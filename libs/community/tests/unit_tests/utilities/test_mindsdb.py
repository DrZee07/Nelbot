from unittest.mock import Mock, patch
import pytest

from langchain_core.pydantic_v1 import SecretStr

from langchain_community.utilities.mindsdb.ai_data_mind.ai_data_mind_wrapper import AIDataMindWrapper
from langchain_community.utilities.mindsdb.base_mind_wrapper import DEFAULT_API_BASE, DEFAULT_MODEL


@pytest.fixture
def data_source_configs():
    return {
        "postgres": {
            "type": "postgres",
            "description": "dummy description",
            "connection_args": {
                "host": "dummy_host",
                "port": 5432,
                "user": "dummy_user",
                "password": "dummy_password",
                "database": "dummy_database",
                "schema": "dummy_schema",
            },
            "tables": ["dummy_table_1", "dummy_table_2"],
        },
        "mysql": {
            "type": "mysql",
            "description": "dummy description",
            "connection_args": {
                "host": "dummy_host",
                "port": 3306,
                "user": "dummy_user",
                "password": "dummy_password",
                "database": "dummy_database",
            },
            "tables": ["dummy_table_1", "dummy_table_2"],
        },
        "mariadb": {
            "type": "mariadb",
            "description": "dummy description",
            "connection_args": {
                "host": "dummy_host",
                "port": 3306,
                "user": "dummy_user",
                "password": "dummy_password",
                "database": "dummy_database",
            },
            "tables": ["dummy_table_1", "dummy_table_2"],
        },
        "clickhouse": {
            "type": "clickhouse",
            "description": "dummy description",
            "connection_args": {
                "host": "dummy_host",
                "port": 8123,
                "user": "dummy_user",
                "password": "dummy_password",
                "database": "dummy_database",
            },
            "tables": ["dummy_table_1", "dummy_table_2"],
        },
        "snowflake": {
            "type": "snowflake",
            "description": "dummy description",
            "connection_args": {
                "account": "dummy_account",
                "user": "dummy_user",
                "password": "dummy_password",
                "warehouse": "dummy_warehouse",
                "database": "dummy_database",
                "schema": "dummy_schema",
            },
            "tables": ["dummy_table_1", "dummy_table_2"],
        },
        "bigquery": {
            "type": "bigquery",
            "description": "dummy description",
            "connection_args": {
                "project_id": "dummy_project_id",
                "dataset": "dummy_dataset",
                "service_account_json": {
                    "type": "service_account",
                    "project_id": "dummy_project_id",
                    "private_key_id": "dummy_private_key_id",
                    "private_key": "dummy_private_key",
                }
            },
            "tables": ["dummy_table_1", "dummy_table_2"],
        }
    }


@pytest.mark.requires("mindsdb_sdk")
@pytest.mark.parametrize("data_source_key", ["postgres", "mysql", "mariadb", "clickhouse", "snowflake", "bigquery"])
@patch("mindsdb_sdk.utils.mind.create_mind")
@patch("mindsdb_sdk.utils.mind.DatabaseConfig")
def test_init_with_data_source(mock_database_config, mock_create_mind, data_source_key, data_source_configs):
    data_source_config = data_source_configs[data_source_key]
    ai_data_mind_config = {
        "name": "dummy_mind",
        "mindsdb_api_key": "dummy_key",
        "data_source_configs": [data_source_config],
    }

    mock_create_mind.return_value = Mock(name="dummy_mind")
    mock_database_config.return_value = Mock(
        type=data_source_config["type"],
        description=data_source_config["description"],
        connection_args=data_source_config["connection_args"],
        tables=data_source_config["tables"],
    )

    ai_data_mind_wrapper = AIDataMindWrapper(**ai_data_mind_config)

    assert ai_data_mind_wrapper.mind is not None
    assert ai_data_mind_wrapper.data_source_configs == [data_source_config]
    assert ai_data_mind_wrapper.name == "dummy_mind"
    assert ai_data_mind_wrapper.mindsdb_api_base == DEFAULT_API_BASE
    assert ai_data_mind_wrapper.model == DEFAULT_MODEL
    assert isinstance(ai_data_mind_wrapper.mindsdb_api_key, SecretStr)


@pytest.mark.requires("mindsdb_sdk")
@patch("mindsdb_sdk.utils.mind.create_mind")
@patch("mindsdb_sdk.utils.mind.DatabaseConfig")
def test_init_with_multiple_data_sources(mock_database_config, mock_create_mind, data_source_configs):
    ai_data_mind_config = {
        "name": "dummy_mind",
        "mindsdb_api_key": "dummy_key",
        "data_source_configs": list(data_source_configs.values()),
    }

    mock_create_mind.return_value = Mock(name="dummy_mind")

    mock_return_values = [
        Mock(
            type=config["type"],
            description=config["description"],
            connection_args=config["connection_args"],
            tables=config["tables"],
        )
        for config in data_source_configs.values()
    ]

    mock_database_config.side_effect = mock_return_values

    ai_data_mind_wrapper = AIDataMindWrapper(**ai_data_mind_config)

    assert ai_data_mind_wrapper.mind is not None
    assert ai_data_mind_wrapper.data_source_configs == list(data_source_configs.values())
    assert ai_data_mind_wrapper.name == "dummy_mind"
    assert ai_data_mind_wrapper.mindsdb_api_base == DEFAULT_API_BASE
    assert ai_data_mind_wrapper.model == DEFAULT_MODEL
    assert isinstance(ai_data_mind_wrapper.mindsdb_api_key, SecretStr)


if __name__ == "__main__":
    pytest.main()