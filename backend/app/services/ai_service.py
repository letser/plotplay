import json
from typing import Dict, Optional, Any

import httpx
from pydantic import BaseModel
from pydantic_settings import BaseSettings


class AISettings(BaseSettings):
    fireworks_api_key: str = ""
    openai_api_key: Optional[str] = None

    writer_model: str = "accounts/fireworks/models/llama-v3p1-70b-instruct"
    checker_model: str = "accounts/fireworks/models/llama-v3p1-8b-instruct"

    writer_temperature: float = 0.8
    writer_top_p: float = 0.9
    writer_max_tokens: int = 500

    checker_temperature: float = 0.1
    checker_top_p: float = 0.95
    checker_max_tokens: int = 300

    class Config:
        env_file = ".env"
        extra = "ignore"  # This will ignore extra fields in .env


class AIResponse(BaseModel):
    content: str
    model: str
    usage: Optional[Dict[str, int]] = None
    raw_response: Optional[Dict] = None


class AIService:
    """Base service for AI model interactions"""

    def __init__(self):
        self.settings = AISettings()
        self.base_url = "https://api.fireworks.ai/inference/v1"

        # For testing without an API key
        if not self.settings.fireworks_api_key:
            print("WARNING: FIREWORKS_API_KEY not set - using mock responses")

    async def generate(
            self,
            prompt: str,
            model: Optional[str] = None,
            temperature: float = 0.7,
            max_tokens: int = 500,
            system_prompt: Optional[str] = None,
            json_mode: bool = False
    ) -> AIResponse:
        """Generate text from AI model"""

        model = model or self.settings.writer_model

        # Mock response if no API key
        if not self.settings.fireworks_api_key:
            return self._get_mock_response(prompt, json_mode)

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": 0.9,
        }

        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        headers = {
            "Authorization": f"Bearer {self.settings.fireworks_api_key}",
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()

                data = response.json()

                return AIResponse(
                    content=data['choices'][0]['message']['content'],
                    model=model,
                    usage=data.get('usage'),
                    raw_response=data
                )

            except httpx.HTTPError as e:
                print(f"AI API Error: {e}")
                return self._get_mock_response(prompt, json_mode)

    def _get_mock_response(self, prompt: str, json_mode: bool) -> AIResponse:
        """Generate a mock response for testing without an API key"""
        if json_mode:
            # Mock checker response
            content = json.dumps({
                "meter_changes": {"bartender": {"trust": 5}},
                "flag_changes": {},
                "clothing_changes": {},
                "location_change": None,
                "player_intent": "investigate",
                "content_flags": [],
                "emotional_tone": "neutral"
            })
        else:
            # Mock writer response
            content = (
                "The dim tavern light flickers across weathered wooden tables as you enter. "
                "The bartender, a gruff woman with sharp eyes, glances up from polishing a glass. "
                "The air is thick with smoke and whispered conversations. A few patrons nurse their "
                "drinks in shadowy corners, avoiding eye contact."
            )

        return AIResponse(
            content=content,
            model="mock",
            usage=None,
            raw_response=None
        )