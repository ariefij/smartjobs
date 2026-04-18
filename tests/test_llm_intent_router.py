import pytest

from smartjobs.config import get_settings
from smartjobs.errors import LLMRequiredError
from smartjobs.llm import OpenAIJobLLM


def test_classify_intent_requires_llm_for_runtime():
    llm = OpenAIJobLLM(get_settings())
    with pytest.raises(LLMRequiredError):
        llm.classify_intent('tolong carikan lowongan data analyst di jakarta', has_cv=False)


def test_analyze_cv_requires_llm_for_runtime():
    llm = OpenAIJobLLM(get_settings())
    with pytest.raises(LLMRequiredError):
        llm.analyze_cv_text('CV: Python SQL Tableau')
