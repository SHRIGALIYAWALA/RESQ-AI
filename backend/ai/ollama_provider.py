import json
import logging
from typing import Any, Dict, Optional
import httpx

logger = logging.getLogger("resq_ai.ai.ollama")


class OllamaProvider:
    """Local Ollama LLM provider adapter with ultra-fast connect failover."""

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3.2:1b"):
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def generate_json(self, prompt: str, system_prompt: str = "") -> Optional[Dict[str, Any]]:
        """Generate structured JSON response using local Ollama instance."""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system_prompt + "\nRespond strictly in valid JSON format matching the requested schema.",
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0.1,
            },
        }
        try:
            # Fast connect timeout so unavailable local servers don't block pipeline
            async with httpx.AsyncClient(timeout=httpx.Timeout(5.0, connect=0.4)) as client:
                response = await client.post(f"{self.base_url}/api/generate", json=payload)
                if response.status_code == 200:
                    data = response.json()
                    response_text = data.get("response", "{}")
                    return json.loads(response_text)
                logger.warning(f"Ollama returned HTTP {response.status_code}: {response.text}")
        except Exception as exc:
            logger.debug(f"Ollama provider unavailable: {exc}")
        return None

    def is_available_sync(self) -> bool:
        """Check if Ollama server is responsive."""
        try:
            with httpx.Client(timeout=0.3) as client:
                resp = client.get(f"{self.base_url}/api/tags")
                return resp.status_code == 200
        except Exception:
            return False
