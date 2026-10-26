from typing import Any, Callable, Dict, Iterable


class ProviderChain:
    """Try configured providers in order and return an auditable result."""

    def __init__(self, providers: Iterable[tuple[str, Callable[[], Dict[str, Any]]]]) -> None:
        self.providers = list(providers)

    def run(self) -> Dict[str, Any]:
        failures = []
        for name, provider in self.providers:
            try:
                result = provider()
                result.setdefault("provider", name)
                result.setdefault("fallbacks_tried", failures)
                return result
            except Exception as exc:
                failures.append({"provider": name, "error": str(exc)})
        return {
            "provider": "none",
            "status": "all_providers_unavailable",
            "fallbacks_tried": failures,
            "human_review_required": True,
        }
