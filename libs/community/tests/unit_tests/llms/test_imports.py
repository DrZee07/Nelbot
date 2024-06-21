from langchain_core.language_models.llms import BaseLLM

from langchain_community import llms

EXPECT_ALL = [
    "AI21",
    "AlephAlpha",
    "AmazonAPIGateway",
    "Anthropic",
    "Anyscale",
    "Aphrodite",
    "Arcee",
    "Aviary",
    "AzureMLOnlineEndpoint",
    "AzureOpenAI",
    "BaichuanLLM",
    "Banana",
    "Baseten",
    "Beam",
    "Bedrock",
    "CTransformers",
    "CTranslate2",
    "CerebriumAI",
    "ChatGLM",
    "Clarifai",
    "Cohere",
    "Databricks",
    "DeepInfra",
    "DeepSparse",
    "EdenAI",
    "FakeListLLM",
    "Fireworks",
    "ForefrontAI",
    "Friendli",
    "GigaChat",
    "GPT4All",
    "GooglePalm",
    "GooseAI",
    "GradientLLM",
    "HuggingFaceEndpoint",
    "HuggingFaceHub",
    "HuggingFacePipeline",
    "HuggingFaceTextGenInference",
    "HumanInputLLM",
    "IpexLLM",
    "KoboldApiLLM",
    "Konko",
    "LlamaCpp",
    "Llamafile",
    "TextGen",
    "ManifestWrapper",
    "Minimax",
    "Mlflow",
    "MlflowAIGateway",
    "MLXPipeline",
    "Modal",
    "MosaicML",
    "Nebula",
    "OCIModelDeploymentTGI",
    "OCIModelDeploymentVLLM",
    "OCIGenAI",
    "NIBittensorLLM",
    "NLPCloud",
    "Ollama",
    "OpenAI",
    "OpenAIChat",
    "OpenLLM",
    "OpenLM",
    "PaiEasEndpoint",
    "Petals",
    "PipelineAI",
    "Predibase",
    "PredictionGuard",
    "PromptLayerOpenAI",
    "PromptLayerOpenAIChat",
    "OpaquePrompts",
    "RWKV",
    "Replicate",
    "SagemakerEndpoint",
    "Sambaverse",
    "SambaStudio",
    "SelfHostedHuggingFaceLLM",
    "SelfHostedPipeline",
    "StochasticAI",
    "TitanTakeoff",
    "TitanTakeoffPro",
    "Together",
    "Tongyi",
    "VertexAI",
    "VertexAIModelGarden",
    "VLLM",
    "VLLMOpenAI",
    "WeightOnlyQuantPipeline",
    "Writer",
    "OctoAIEndpoint",
    "Xinference",
    "JavelinAIGateway",
    "QianfanLLMEndpoint",
    "YandexGPT",
    "Yuan2",
    "VolcEngineMaasLLM",
    "VolcEngineMaasLLMV3",
    "WatsonxLLM",
    "SparkLLM",
]


def test_all_imports() -> None:
    """Simple test to make sure all things can be imported."""
    for cls in llms.__all__:
        assert issubclass(getattr(llms, cls), BaseLLM)
    assert set(llms.__all__) == set(EXPECT_ALL)
