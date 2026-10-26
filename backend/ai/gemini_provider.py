import json
import logging
from typing import Any, Dict, Optional
import httpx

logger = logging.getLogger("resq_ai.ai.gemini")


class GeminiProvider:
    """Google Gemini AI provider adapter using standard REST API."""

    def __init__(self, api_key: str = "", model: str = "gemini-2.0-flash"):
        self.api_key = api_key
        self.model = model

    async def generate_json(self, prompt: str, system_prompt: str = "") -> Optional[Dict[str, Any]]:
        if not self.api_key:
            return None

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        payload = {
            "system_instruction": {
                "parts": [{"text": system_prompt + "\nOutput strictly valid raw JSON without markdown code fences."}]
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}],
                }
            ],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.1,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                response = await client.post(url, json=payload)
                if response.status_code == 200:
                    data = response.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        content_parts = candidates[0].get("content", {}).get("parts", [])
                        if content_parts:
                            text_out = content_parts[0].get("text", "{}")
                            return json.loads(text_out)
                logger.warning(f"Gemini API returned HTTP {response.status_code}: {response.text}")
        except Exception as exc:
            logger.debug(f"Gemini provider exception: {exc}")
        return None
