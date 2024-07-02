"""Test NexaAI Chat API wrapper."""
from langchain_nexa_ai import NexaAILLM

def test_initialization() -> None:
    """Test integration initialization."""
    NexaAILLM()

def test_prepare_categories() -> None:
    """Test _prepare_categories method of NexaAILLM."""
    llm = NexaAILLM()

    # Test case 1: No categories or category provided
    prompts = ["Prompt 1", "Prompt 2"]
    categories = llm._prepare_categories(prompts)
    assert categories == ["shopping", "shopping"], "Expected default category 'shopping' for all prompts"

    # Test case 2: Single category provided
    prompt = ["Prompt 1"]
    categories = llm._prepare_categories(prompt, category="shopping")
    assert categories == ["shopping"], "Expected category 'shopping' for the prompt" # type: ignore

    # Test case 3: List of categories provided
    categories = llm._prepare_categories(prompts, categories=["shopping", "travel"])
    assert categories == ["shopping", "travel"], "Expected categories 'tech' and 'fashion' for prompts"

    # Test case 4: Both category and categories provided (categories should be used)
    categories = llm._prepare_categories(prompts, category="electronics", categories=["shopping", "travel"])
    assert categories == ["shopping", "travel"], "Expected categories 'shopping' and 'travel' when both category and categories are provided"
