import logging
from typing import Any, Dict, Optional, Type, TypeVar
from pydantic import BaseModel

from backend.config import get_settings
from backend.ai.ollama_provider import OllamaProvider
from backend.ai.gemini_provider import GeminiProvider
from backend.ai.groq_provider import GroqProvider
from backend.ai.openai_provider import OpenAIProvider

logger = logging.getLogger("resq_ai.ai.manager")
T = TypeVar("T", bound=BaseModel)


class AIProviderManager:
    """Manages AI provider fallback chain and structured JSON completion.
    
    Priority Order:
    1. Local Ollama (offline, zero-cost, private)
    2. Free-tier Gemini (if GEMINI_API_KEY configured)
    3. Free-tier Groq (if GROQ_API_KEY configured)
    4. OpenAI (if LLM_API_KEY configured)
    5. Graceful fallback to deterministic rules.
    """

    def __init__(self):
        self.settings = get_settings()
        self.ollama = OllamaProvider(base_url=self.settings.ollama_url, model=self.settings.ollama_model)
        self.gemini = GeminiProvider(api_key=self.settings.gemini_api_key, model=self.settings.gemini_model)
        self.groq = GroqProvider(api_key=self.settings.groq_api_key, model=self.settings.groq_model)
        self.openai = OpenAIProvider(api_key=self.settings.llm_api_key, model=self.settings.llm_model)

    async def execute_structured(
        self,
        prompt: str,
        system_prompt: str,
        schema: Type[T],
        fallback_fn: Any = None,
    ) -> Dict[str, Any]:
        """Attempt completion through providers in priority order, validating against schema."""
        providers = []

        # Configure preferred provider first based on settings
        primary = self.settings.llm_provider.lower()
        if primary == "ollama":
            providers = [("ollama", self.ollama), ("gemini", self.gemini), ("groq", self.groq), ("openai", self.openai)]
        elif primary == "gemini":
            providers = [("gemini", self.gemini), ("groq", self.groq), ("ollama", self.ollama), ("openai", self.openai)]
        elif primary == "groq":
            providers = [("groq", self.groq), ("gemini", self.gemini), ("ollama", self.ollama), ("openai", self.openai)]
        else:
            providers = [("ollama", self.ollama), ("gemini", self.gemini), ("groq", self.groq), ("openai", self.openai)]

        attempts = []
        for name, provider in providers:
            try:
                result = await provider.generate_json(prompt, system_prompt)
                if not result:
                    attempts.append({"provider": name, "outcome": "no_response"})
                    continue

                try:
                    validated = schema.model_validate(result)
                except Exception as validation_exc:
                    attempts.append({"provider": name, "outcome": "schema_validation_failed", "error": str(validation_exc)})
                    logger.warning("Provider %s returned invalid JSON for %s: %s", name, schema.__name__, validation_exc)
                    continue

                return {
                    "status": "success",
                    "provider": name,
                    "data": validated.model_dump(),
                    "fallbacks_tried": attempts,
                    "human_review_required": True,
                }
            except Exception as exc:
                attempts.append({"provider": name, "outcome": "generation_failed", "error": str(exc)})
                logger.debug(f"Provider {name} validation/generation failed: {exc}")

        logger.info("All AI providers unavailable/unconfigured. Falling back to deterministic rule engine.")
        if fallback_fn:
            fallback_data = fallback_fn()
            try:
                validated = schema.model_validate(fallback_data)
                return {
                    "status": "fallback_rule_based",
                    "provider": "deterministic_safety_engine",
                    "data": validated.model_dump(),
                    "fallbacks_tried": attempts,
                    "human_review_required": True,
                }
            except Exception as validation_exc:
                fallback_data.setdefault("requires_human_review", True)
                fallback_data.setdefault("confidence", 0.0)
                logger.warning("Deterministic fallback schema validation failed: %s", validation_exc)
                return {
                    "status": "fallback_rule_based",
                    "provider": "deterministic_safety_engine",
                    "data": fallback_data,
                    "fallbacks_tried": attempts,
                    "human_review_required": True,
                }

        return {
            "status": "unavailable",
            "provider": "none",
            "data": {},
            "fallbacks_tried": attempts,
            "human_review_required": True,
        }

    def get_provider_status(self) -> Dict[str, Any]:
        return {
            "configured_primary": self.settings.llm_provider,
            "ollama_url": self.settings.ollama_url,
            "gemini_enabled": bool(self.settings.gemini_api_key),
            "groq_enabled": bool(self.settings.groq_api_key),
            "openai_enabled": bool(self.settings.llm_api_key),
            "offline_rule_engine": "ready",
        }


# Global singleton
ai_manager = AIProviderManager()
