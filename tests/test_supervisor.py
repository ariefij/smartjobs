import pytest

from smartjobs.agent import SmartJobsAgent
from smartjobs.config import get_settings
from smartjobs.errors import LLMRequiredError
from smartjobs.schemas import SearchRequest


def test_supervisor_requires_llm_for_runtime_search():
    agent = SmartJobsAgent(get_settings())
    with pytest.raises(LLMRequiredError):
        agent.search(SearchRequest(pertanyaan='berapa jumlah lowongan data analyst di jakarta', batas=5))
