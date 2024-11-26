from langchain_community.embeddings import __all__, _module_lookup

EXPECTED_ALL = [
    "ClovaEmbeddings",
    "OpenAIEmbeddings",
    "AnyscaleEmbeddings",
    "AzureOpenAIEmbeddings",
    "BaichuanTextEmbeddings",
    "ClarifaiEmbeddings",
    "ClovaXEmbeddings",
    "CohereEmbeddings",
    "DatabricksEmbeddings",
    "ElasticsearchEmbeddings",
    "FastEmbedEmbeddings",
    "HuggingFaceEmbeddings",
    "HuggingFaceInferenceAPIEmbeddings",
    "InfinityEmbeddings",
    "InfinityEmbeddingsLocal",
    "GradientEmbeddings",
    "JinaEmbeddings",
    "LaserEmbeddings",
    "LlamaCppEmbeddings",
    "LlamafileEmbeddings",
    "LLMRailsEmbeddings",
    "HuggingFaceHubEmbeddings",
    "MlflowAIGatewayEmbeddings",
    "MlflowEmbeddings",
    "MlflowCohereEmbeddings",
    "ModelScopeEmbeddings",
    "TensorflowHubEmbeddings",
    "SagemakerEndpointEmbeddings",
    "HuggingFaceInstructEmbeddings",
    "MosaicMLInstructorEmbeddings",
    "SelfHostedEmbeddings",
    "SelfHostedHuggingFaceEmbeddings",
    "SelfHostedHuggingFaceInstructEmbeddings",
    "FakeEmbeddings",
    "DeterministicFakeEmbedding",
    "AlephAlphaAsymmetricSemanticEmbedding",
    "AlephAlphaSymmetricSemanticEmbedding",
    "SentenceTransformerEmbeddings",
    "GooglePalmEmbeddings",
    "MiniMaxEmbeddings",
    "VertexAIEmbeddings",
    "BedrockEmbeddings",
    "DeepInfraEmbeddings",
    "EdenAiEmbeddings",
    "DashScopeEmbeddings",
    "EmbaasEmbeddings",
    "OctoAIEmbeddings",
    "SpacyEmbeddings",
    "NLPCloudEmbeddings",
    "GPT4AllEmbeddings",
    "GigaChatEmbeddings",
    "XinferenceEmbeddings",
    "LocalAIEmbeddings",
    "AwaEmbeddings",
    "HuggingFaceBgeEmbeddings",
    "IpexLLMBgeEmbeddings",
    "ErnieEmbeddings",
    "JavelinAIGatewayEmbeddings",
    "OllamaEmbeddings",
    "OracleEmbeddings",
    "OVHCloudEmbeddings",
    "QianfanEmbeddingsEndpoint",
    "JohnSnowLabsEmbeddings",
    "VoyageEmbeddings",
    "BookendEmbeddings",
    "VolcanoEmbeddings",
    "OCIGenAIEmbeddings",
    "QuantizedBiEncoderEmbeddings",
    "NeMoEmbeddings",
    "SparkLLMTextEmbeddings",
    "SambaStudioEmbeddings",
    "TitanTakeoffEmbed",
    "QuantizedBgeEmbeddings",
    "PremAIEmbeddings",
    "YandexGPTEmbeddings",
    "OpenVINOEmbeddings",
    "OpenVINOBgeEmbeddings",
    "SolarEmbeddings",
    "AscendEmbeddings",
    "ZhipuAIEmbeddings",
    "TextEmbedEmbeddings",
    "PredictionGuardEmbeddings",
]


def test_all_imports() -> None:
    assert set(__all__) == set(EXPECTED_ALL)
    assert set(__all__) == set(_module_lookup.keys())
