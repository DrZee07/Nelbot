##
# Copyright (c) 2024, Chad Juliano, Kinetica DB Inc.
##

import json
import logging
import os
import re
from importlib.metadata import version
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, cast, Dict

if TYPE_CHECKING:
    import gpudb
    import pandas as pd

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
)
from langchain_core.output_parsers.transform import BaseOutputParser
from langchain_core.outputs import ChatGeneration, ChatResult, Generation
from langchain_core.pydantic_v1 import BaseModel, Field, root_validator

LOG = logging.getLogger(__name__)

# Kinetica pydantic API datatypes


class _KdtSuggestContext(BaseModel):
    """pydantic API request type"""

    table: Optional[str] = Field(default=None, title="Name of table")
    description: Optional[str] = Field(default=None, title="Table description")
    columns: List[str] = Field(default=None, title="Table columns list")
    rules: Optional[List[str]] = Field(
        default=None, title="Rules that apply to the table."
    )
    samples: Optional[Dict] = Field(
        default=None, title="Samples that apply to the entire context."
    )

    def to_system_str(self) -> str:
        lines = []
        lines.append(f"CREATE TABLE {self.table} AS")
        lines.append("(")

        if not self.columns or len(self.columns) == 0:
            ValueError(detail="columns list can't be null.")  # type: ignore

        columns = []
        for column in self.columns:
            column = column.replace('"', "").strip()
            columns.append(f"   {column}")
        lines.append(",\n".join(columns))
        lines.append(");")

        if self.description:
            lines.append(f"COMMENT ON TABLE {self.table} IS '{self.description}';")

        if self.rules and len(self.rules) > 0:
            lines.append(
                f"-- When querying table {self.table} the following rules apply:"
            )
            for rule in self.rules:
                lines.append(f"-- * {rule}")

        result = "\n".join(lines)
        return result


class _KdtSuggestPayload(BaseModel):
    """pydantic API request type"""

    question: Optional[str]
    context: List[_KdtSuggestContext]

    def get_system_str(self) -> str:
        lines = []
        for table_context in self.context:
            if table_context.table is None:
                continue
            context_str = table_context.to_system_str()
            lines.append(context_str)
        return "\n\n".join(lines)

    def get_messages(self) -> List[Dict]:
        messages = []
        for context in self.context:
            if context.samples is None:
                continue
            for question, answer in context.samples.items():
                # unescape double quotes
                answer = answer.replace("''", "'")

                messages.append(dict(role="user", content=question or ""))
                messages.append(dict(role="assistant", content=answer))
        return messages

    def to_completion(self) -> Dict:
        messages = []
        messages.append(dict(role="system", content=self.get_system_str()))
        messages.extend(self.get_messages())
        messages.append(dict(role="user", content=self.question or ""))
        response = dict(messages=messages)
        return response


class _KdtoSuggestRequest(BaseModel):
    """pydantic API request type"""

    payload: _KdtSuggestPayload


class _KdtMessage(BaseModel):
    """pydantic API response type"""

    role: str = Field(default=None, title="One of [user|assistant|system]")
    content: str


class _KdtChoice(BaseModel):
    """pydantic API response type"""

    index: int
    message: _KdtMessage = Field(default=None, title="The generated SQL")
    finish_reason: str


class _KdtUsage(BaseModel):
    """pydantic API response type"""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class _KdtSqlResponse(BaseModel):
    """pydantic API response type"""

    id: str
    object: str
    created: int
    model: str
    choices: List[_KdtChoice]
    usage: _KdtUsage
    prompt: str = Field(default=None, title="The input question")


class _KdtCompletionResponse(BaseModel):
    """pydantic API response type"""

    status: str
    data: _KdtSqlResponse


class _KineticaLlmFileContextParser:
    """Parse a Kinetica LLM context datafile."""

    # parse line into a dict containing role and content
    PARSER = re.compile(r"^<\|(?P<role>\w+)\|>\W*(?P<content>.*)$", re.DOTALL)

    @classmethod
    def parse_dialogue_file(cls, input_file: os.PathLike) -> Dict:
        path = Path(input_file)
        schema = path.name.removesuffix(".txt")
        lines = open(input_file).read()
        return cls.parse_dialogue(lines, schema)

    @classmethod
    def parse_dialogue(cls, text: str, schema: str) -> Dict:
        messages = []
        system = None

        lines = text.split("<|end|>")
        user_message = None

        for idx, line in enumerate(lines):
            line = line.strip()

            if len(line) == 0:
                continue

            match = cls.PARSER.match(line)
            if match is None:
                raise ValueError(f"Could not find starting token in: {line}")

            groupdict = match.groupdict()
            role = groupdict["role"]

            if role == "system":
                if system is not None:
                    raise ValueError(f"Only one system token allowed in: {line}")
                system = groupdict["content"]
            elif role == "user":
                if user_message is not None:
                    raise ValueError(
                        f"Found user token without assistant token: {line}"
                    )
                user_message = groupdict
            elif role == "assistant":
                if user_message is None:
                    raise Exception(f"Found assistant token without user token: {line}")
                messages.append(user_message)
                messages.append(groupdict)
                user_message = None
            else:
                raise ValueError(f"Unknown token: {role}")

        return {"schema": schema, "system": system, "messages": messages}


class KineticaChatLLM(BaseChatModel):
    """Kinetica LLM Chat Model"""

    kdbc: Any = None
    """ Kinetica DB connection. """

    @classmethod
    def _create_kdbc(
        cls,
        url: Optional[str] = None,
        user: Optional[str] = None,
        passwd: Optional[str] = None,
    ) -> "gpudb.GPUdb":
        """Create a Kinetica DB connection."""

        try:
            import gpudb
        except ImportError:
            raise ImportError(
                "Could not import Kinetica python package. "
                "Please install it with `pip install gpudb`."
            )

        url = cls._get_env("KINETICA_URL", url)
        user = cls._get_env("KINETICA_USER", user)
        passwd = cls._get_env("KINETICA_PASSWD", passwd)

        options = gpudb.GPUdb.Options()
        options.username = user
        options.password = passwd
        options.skip_ssl_cert_verification = True
        options.disable_failover = True
        options.logging_level = "INFO"
        kdbc = gpudb.GPUdb(host=url, options=options)

        LOG.info(
            "Connected to Kinetica: {}. (api={}, server={})".format(
                kdbc.get_url(), version("gpudb"), kdbc.server_version
            )
        )

        return kdbc

    @classmethod
    def _get_env(cls, name: str, default: Optional[str]) -> str:
        """Get an environment variable or use a default."""
        if default is not None:
            return default

        result = os.getenv(name)
        if result is not None:
            return result

        raise ValueError(
            f"Parameter was not passed and not found in the environment: {name}"
        )

    @root_validator()
    def validate_environment(cls, values: Dict) -> Dict:
        """Pydantic object validator."""

        kdbc = values.get("kdbc", None)
        if kdbc is None:
            kdbc = cls._create_kdbc()
            values["kdbc"] = kdbc
        return values

    @property
    def _llm_type(self) -> str:
        return "kinetica-sqlassist"

    @property
    def _identifying_params(self) -> Dict[str, Any]:
        return dict(
            kinetica_version=str(self.kdbc.server_version), api_version=version("gpudb")
        )

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        if stop is not None:
            raise ValueError("stop kwargs are not permitted.")

        dict_messages = [self._convert_message_to_dict(m) for m in messages]
        sql_response = self._submit_completion(dict_messages)

        response_message = sql_response.choices[0].message
        # generated_dict = response_message.model_dump() # pydantic v2
        generated_dict = response_message.dict()

        generated_message = self._convert_message_from_dict(generated_dict)

        llm_output = dict(
            input_tokens=sql_response.usage.prompt_tokens,
            output_tokens=sql_response.usage.completion_tokens,
            model_name=sql_response.model,
        )
        return ChatResult(
            generations=[ChatGeneration(message=generated_message)],
            llm_output=llm_output,
        )

    def load_messages_from_context(self, context_name: str) -> List:
        """Load a lanchain prompt from a Kinetica context."""

        # query kinetica for the prompt
        sql = f"GENERATE PROMPT WITH OPTIONS (CONTEXT_NAMES = '{context_name}')"
        result = self._execute_sql(sql)
        prompt = result["Prompt"]
        prompt_json = json.loads(prompt)

        # convert the prompt to messages
        # request = SuggestRequest.model_validate(prompt_json) # pydantic v2
        request = _KdtoSuggestRequest.parse_obj(prompt_json)
        payload = request.payload

        dict_messages = []
        dict_messages.append(dict(role="system", content=payload.get_system_str()))
        dict_messages.extend(payload.get_messages())
        messages = [self._convert_message_from_dict(m) for m in dict_messages]
        return messages

    def _submit_completion(self, messages: List[Dict]) -> _KdtSqlResponse:
        """Submit a /chat/completions request to Kinetica."""

        request = dict(messages=messages)
        request_json = json.dumps(request)
        response_raw = self.kdbc._GPUdb__submit_request_json(
            "/chat/completions", request_json
        )
        response_json = json.loads(response_raw)

        status = response_json["status"]
        if status != "OK":
            message = response_json["message"]
            match_resp = re.compile(r"response:({.*})")
            result = match_resp.search(message)
            if result is not None:
                response = result.group(1)
                response_json = json.loads(response)
                message = response_json["message"]
            raise ValueError(message)

        data = response_json["data"]
        # response = CompletionResponse.model_validate(data) # pydantic v2
        response = _KdtCompletionResponse.parse_obj(data)
        if response.status != "OK":
            raise ValueError("SQL Generation failed")
        return response.data

    def _execute_sql(self, sql: str) -> Dict:
        """Execute an SQL query and return the result."""

        response = self.kdbc.execute_sql_and_decode(
            sql, limit=1, get_column_major=False
        )

        status_info = response["status_info"]
        if status_info["status"] != "OK":
            message = status_info["message"]
            raise ValueError(message)

        records = response["records"]
        if len(records) != 1:
            raise ValueError("No records returned.")

        record = records[0]
        response_dict = {}
        for col, val in record.items():
            response_dict[col] = val
        return response_dict

    @classmethod
    def load_messages_from_datafile(cls, sa_datafile: Path) -> List[BaseMessage]:
        """Load a lanchain prompt from a Kinetica context datafile."""
        datafile_dict = _KineticaLlmFileContextParser.parse_dialogue_file(sa_datafile)
        messages = cls._convert_dict_to_messages(datafile_dict)
        return messages

    @classmethod
    def _convert_message_to_dict(cls, message: BaseMessage) -> Dict:
        """Convert a single message to a BaseMessage."""

        content = cast(str, message.content)
        if isinstance(message, HumanMessage):
            role = "user"
        elif isinstance(message, AIMessage):
            role = "assistant"
        elif isinstance(message, SystemMessage):
            role = "system"
        else:
            raise ValueError(f"Got unsupported message type: {message}")

        result_message = dict(role=role, content=content)
        return result_message

    @classmethod
    def _convert_message_from_dict(cls, message: Dict) -> BaseMessage:
        """Convert a single message from a BaseMessage."""

        role = message["role"]
        content = message["content"]
        if role == "user":
            return HumanMessage(content=content)
        elif role == "assistant":
            return AIMessage(content=content)
        elif role == "system":
            return SystemMessage(content=content)
        else:
            raise ValueError(f"Got unsupported role: {role}")

    @classmethod
    def _convert_dict_to_messages(cls, sa_data: Dict) -> List[BaseMessage]:
        """Convert a dict to a list of BaseMessages."""

        schema = sa_data["schema"]
        system = sa_data["system"]
        messages = sa_data["messages"]
        LOG.info(f"Importing prompt for schema: {schema}")

        result_list: List[BaseMessage] = []
        result_list.append(SystemMessage(content=system))
        result_list.extend([cls._convert_message_from_dict(m) for m in messages])
        return result_list


class KineticaSqlResponse(BaseModel):
    """Response containing SQL and the fetched data."""

    sql: str = Field(description="Result SQL")
    dataframe: "pd.DataFrame" = Field(description="Result Data")

    class Config:
        """Configuration for this pydantic object."""

        arbitrary_types_allowed = True


class KineticaSqlOutputParser(BaseOutputParser[KineticaSqlResponse]):
    """Fetch and return data from the Kinetica LLM."""

    kdbc: Any = Field(exclude=True)
    """ Kinetica DB connection. """

    class Config:
        """Configuration for this pydantic object."""

        arbitrary_types_allowed = True

    def parse(self, text: str) -> KineticaSqlResponse:
        df = self.kdbc.to_df(text)
        return KineticaSqlResponse(sql=text, dataframe=df)

    def parse_result(
        self, result: List[Generation], *, partial: bool = False
    ) -> KineticaSqlResponse:
        return self.parse(result[0].text)

    @property
    def _type(self) -> str:
        return "kinetica_sql_output_parser"
