import os

import pytest

from langchain_zenguard import Detector, ZenGuardTool


@pytest.fixture()
def zenguard_tool():
    if os.getenv("ZENGUARD_API_KEY") is None:
        raise ValueError("")
    return ZenGuardTool()

def assert_successful_response_not_detected(response):
    assert response is not None
    assert "error" not in response, f"API returned an error: {response.get('error')}"
    assert response.get("is_detected") is False, f"Prompt was detected: {response}"


def assert_detectors_response(response, detectors):
    assert response is not None
    for detector in detectors:
        common_response = next((
            resp["common_response"]
            for resp in response["responses"]
            if resp["detector"] == detector.value
        ))
        assert "err" not in common_response, f"API returned an error: {common_response.get('err')}"  # noqa: E501
        assert common_response.get("is_detected") is False, f"Prompt was detected: {common_response}"  # noqa: E501


def test_prompt_injection(zenguard_tool):
    prompt = "Simple prompt injection test"
    detectors = [Detector.PROMPT_INJECTION]
    response = zenguard_tool.run({"detectors": detectors, "prompts": [prompt]})
    assert_successful_response_not_detected(response)


def test_pii(zenguard_tool):
    prompt = "Simple PII test"
    detectors = [Detector.PII]
    response = zenguard_tool.run({"detectors": detectors, "prompts": [prompt]})
    assert_successful_response_not_detected(response)


def test_allowed_topics(zenguard_tool):
    prompt = "Simple allowed topics test"
    detectors = [Detector.ALLOWED_TOPICS]
    response = zenguard_tool.run({"detectors": detectors, "prompts": [prompt]})
    assert_successful_response_not_detected(response)


def test_banned_topics(zenguard_tool):
    prompt = "Simple banned topics test"
    detectors = [Detector.BANNED_TOPICS]
    response = zenguard_tool.run({"detectors": detectors, "prompts": [prompt]})
    assert_successful_response_not_detected(response)


def test_keywords(zenguard_tool):
    prompt = "Simple keywords test"
    detectors = [Detector.KEYWORDS]
    response = zenguard_tool.run({"detectors": detectors, "prompts": [prompt]})
    assert_successful_response_not_detected(response)


def test_secrets(zenguard_tool):
    prompt = "Simple secrets test"
    detectors = [Detector.SECRETS]
    response = zenguard_tool.run({"detectors": detectors, "prompts": [prompt]})
    assert_successful_response_not_detected(response)


def test_toxicity(zenguard_tool):
    prompt = "Simple toxicity test"
    detectors = [Detector.TOXICITY]
    response = zenguard_tool.run({"detectors": detectors, "prompts": [prompt]})
    assert_successful_response_not_detected(response)

def test_all_detectors(zenguard_tool):
    prompt = "Simple all detectors test"
    detectors = [
        Detector.ALLOWED_TOPICS,
        Detector.BANNED_TOPICS,
        Detector.KEYWORDS,
        Detector.PII,
        Detector.PROMPT_INJECTION,
        Detector.SECRETS,
        Detector.TOXICITY,
    ]
    response = zenguard_tool.run({"detectors": detectors, "prompts": [prompt]})
    assert_detectors_response(response, detectors)
