import json
import logging
from typing import Any, Dict, Optional
import httpx

logger = logging.getLogger("resq_ai.ai.groq")


class GroqProvider:
    """Groq ultra-low-latency provider adapter."""

    def __init__(self, api_key: str = "", model: str = "llama-3.1-8b-instant"):
        self.api_key = api_key
        self.model = model

    async def generate_json(self, prompt: str, system_prompt: str = "") -> Optional[Dict[str, Any]]:
        if not self.api_key:
            return None

        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt + "\nOutput strictly valid raw JSON."},
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, headers=headers, json=payload)
                if response.status_code == 200:
                    data = response.json()
                    choices = data.get("choices", [])
                    if choices:
                        content = choices[0].get("message", {}).get("content", "{}")
                        return json.loads(content)
                logger.warning(f"Groq API returned HTTP {response.status_code}: {response.text}")
        except Exception as exc:
            logger.debug(f"Groq provider exception: {exc}")
        return None
