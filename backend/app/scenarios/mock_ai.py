"""
Mock AI service for deterministic scenario testing.

This service provides pre-scripted Writer and Checker responses,
allowing scenarios to execute without real LLM calls.
"""

import json
from typing import Dict, List, AsyncIterator, Optional
from app.scenarios.models import MockResponses


class MockAIService:
    """
    Deterministic mock AI service for scenario testing.

    Replaces the real AIService with pre-scripted responses,
    enabling reproducible integration tests without LLM costs.
    """

    def __init__(self):
        self.writer_responses: Dict[str, str] = {}
        self.checker_responses: Dict[str, dict] = {}
        self.call_log: List[dict] = []  # Track all calls for debugging
        self.current_mock_key: Optional[str] = None  # Set by runner before each step

    def load_mocks(self, mocks: MockResponses):
        """Load mock responses from scenario definition."""
        self.writer_responses = mocks.writer
        self.checker_responses = mocks.checker

    def set_mock_key(self, key: str):
        """Set the current mock key for next AI call."""
        self.current_mock_key = key

    def set_inline_mocks(self, writer: Optional[str] = None, checker: Optional[dict] = None):
        """
        Set inline mocks for the current step (temporary, overrides referenced mocks).

        Args:
            writer: Inline narrative text (optional)
            checker: Inline checker delta (optional)
        """
        # Use a special key for inline mocks
        inline_key = "__inline__"
        self.current_mock_key = inline_key

        # Set inline responses
        if writer is not None:
            self.writer_responses[inline_key] = writer
        elif inline_key in self.writer_responses:
            # Use default if no inline writer provided
            del self.writer_responses[inline_key]

        if checker is not None:
            self.checker_responses[inline_key] = checker
        elif inline_key not in self.checker_responses:
            # Use sensible default if no inline checker provided
            self.checker_responses[inline_key] = {
                "meters": {},
                "flags": {},
                "character_memories": {},
                "safety": {"ok": True}
            }

    async def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 500,
        response_format: Optional[dict] = None,
        **kwargs
    ) -> "AIResponse":
        """
        Return mocked Checker response.

        The response should be JSON-formatted state deltas.
        """
        key = self.current_mock_key or "default"

        # Get mock response or use sensible default
        response_data = self.checker_responses.get(key, {
            "meters": {},
            "flags": {},
            "character_memories": {},
            "safety": {"ok": True}
        })

        # Log the call for debugging
        self.call_log.append({
            "type": "checker",
            "key": key,
            "prompt_length": len(prompt),
            "response": response_data
        })

        # Return AIResponse-like object
        from app.services.ai_service import AIResponse
        return AIResponse(
            content=json.dumps(response_data),
            done=True,
            model="mock-checker",
            usage={"prompt_tokens": 0, "completion_tokens": 0}
        )

    async def generate_stream(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 500,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        Return mocked Writer response as a stream.

        Streams the narrative character by character for realism.
        """
        key = self.current_mock_key or "default"

        # Get mock narrative or use default
        narrative = self.writer_responses.get(key, "A scene unfolds...")

        # Log the call
        self.call_log.append({
            "type": "writer",
            "key": key,
            "prompt_length": len(prompt),
            "narrative": narrative
        })

        # Stream character by character (simulates real streaming)
        for char in narrative:
            yield char

    def clear_log(self):
        """Clear the call log (useful between scenarios)."""
        self.call_log = []

    def get_call_count(self) -> dict:
        """Get count of Writer and Checker calls."""
        writer_calls = sum(1 for call in self.call_log if call["type"] == "writer")
        checker_calls = sum(1 for call in self.call_log if call["type"] == "checker")
        return {
            "writer": writer_calls,
            "checker": checker_calls,
            "total": len(self.call_log)
        }
