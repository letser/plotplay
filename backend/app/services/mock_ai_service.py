"""
Mock AI service for fast testing without API calls.
"""

import json
from typing import AsyncGenerator

from app.services.ai_service import AIResponse


class MockAIService:
    """Mock AI service that returns instant responses without API calls."""

    def __init__(self):
        """Initialize mock service."""
        pass

    async def generate(
        self,
        prompt: str,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 500,
        system_prompt: str | None = None,
        json_mode: bool = False,
        top_p: float = 0.9,
    ) -> AIResponse:
        """Generate instant mock response."""

        if json_mode:
            # Mock Checker response
            content = json.dumps({
                "meter_changes": {},
                "flag_changes": {},
                "clothing_changes": {},
                "location_change": None,
                "player_intent": "test",
                "content_flags": [],
                "emotional_tone": "neutral",
                "intimacy_escalation": False,
                "memory": []
            })
        else:
            # Mock Writer response
            content = (
                "The scene unfolds as expected. Your action has an effect on the "
                "environment around you. The atmosphere shifts subtly in response."
            )

        return AIResponse(
            content=content,
            model=model or "mock",
            usage={"total_tokens": 100, "prompt_tokens": 50, "completion_tokens": 50},
            raw_response=None,
        )

    async def generate_stream(
        self,
        prompt: str,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 500,
        system_prompt: str | None = None,
        top_p: float = 0.9,
    ) -> AsyncGenerator[str, None]:
        """Generate instant mock streaming response."""

        # Mock streaming by yielding the response in chunks
        response = (
            "The scene unfolds as expected. Your action has an effect on the "
            "environment around you. The atmosphere shifts subtly in response."
        )

        # Yield each word
        for word in response.split():
            yield word + " "
