from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .observability import NoOpLangfuseObserver
from .prompts import (
    CV_ANALYSIS_SYSTEM_PROMPT,
    INTENT_ROUTER_SYSTEM_PROMPT,
    JOB_ENRICHMENT_SYSTEM_PROMPT,
    RESPONSE_SYSTEM_PROMPT,
    SKILL_GAP_SYSTEM_PROMPT,
)

LOCAL_PROMPTS = {
    "job_enrichment": JOB_ENRICHMENT_SYSTEM_PROMPT,
    "cv_analysis": CV_ANALYSIS_SYSTEM_PROMPT,
    "response_generation": RESPONSE_SYSTEM_PROMPT,
    "skill_gap": SKILL_GAP_SYSTEM_PROMPT,
    "intent_router": INTENT_ROUTER_SYSTEM_PROMPT,
}


class PromptRegistry:
    def __init__(
        self,
        prompt_file: str | Path | None = None,
        *,
        observer: NoOpLangfuseObserver | None = None,
        langfuse_client: Any | None = None,
    ):
        self.prompt_file = Path(prompt_file) if prompt_file else None
        self.observer = observer or NoOpLangfuseObserver()
        self.langfuse_client = langfuse_client
        self.meta: dict[str, Any] = {}
        if self.prompt_file and self.prompt_file.exists():
            try:
                self.meta = json.loads(self.prompt_file.read_text(encoding="utf-8"))
            except Exception:
                self.meta = {}

    def get_prompt(self, key: str) -> str:
        meta = self.get_prompt_meta(key)
        prompt_name = meta.get("name") or key
        if self.langfuse_client is not None:
            with self.observer.trace("prompt_registry.get_prompt", {"key": key, "prompt_name": prompt_name, "source": "langfuse"}):
                prompt = self._get_langfuse_prompt(prompt_name)
                if prompt:
                    return prompt
        with self.observer.trace("prompt_registry.get_prompt", {"key": key, "prompt_name": prompt_name, "source": "local"}):
            return LOCAL_PROMPTS[key]

    def get_prompt_meta(self, key: str) -> dict[str, Any]:
        payload = self.meta.get(key) or {}
        if isinstance(payload, dict):
            return payload
        return {}

    def _get_langfuse_prompt(self, prompt_name: str) -> str | None:
        try:
            prompt_obj = self.langfuse_client.get_prompt(prompt_name)
        except Exception:
            return None
        if isinstance(prompt_obj, str) and prompt_obj.strip():
            return prompt_obj.strip()
        if isinstance(prompt_obj, dict):
            for candidate in ("prompt", "text", "content"):
                value = prompt_obj.get(candidate)
                if isinstance(value, str) and value.strip():
                    return value.strip()
        for attr in ("prompt", "text", "content"):
            value = getattr(prompt_obj, attr, None)
            if isinstance(value, str) and value.strip():
                return value.strip()
        compile_fn = getattr(prompt_obj, "compile", None)
        if callable(compile_fn):
            try:
                compiled = compile_fn()
            except Exception:
                return None
            if isinstance(compiled, str) and compiled.strip():
                return compiled.strip()
        return None
