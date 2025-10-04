import json
from typing import Dict, Optional, Any
import httpx
from pydantic import BaseModel, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AISettings(BaseSettings):
    # API Keys
    openrouter_api_key: str = "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"

    # App URL for OpenRouter
    app_url: str = "http://localhost:8000"

    # Model Configuration
    writer_model: str = "nousresearch/nous-hermes-2-mixtral-8x7b-sft"
    checker_model: str = "nousresearch/nous-hermes-2-mixtral-8x7b-sft"

    # Generation settings
    writer_temperature: float = 0.8
    writer_top_p: float = 0.9
    writer_max_tokens: int = 500

    checker_temperature: float = 0.2  # Lower for consistency
    checker_top_p: float = 0.95
    checker_max_tokens: int = 300

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")



class AIResponse(BaseModel):
    content: str
    model: str | None = None
    usage: Dict[str, int | Dict | None] | None = None
    raw_response: Dict | None = None

    @field_validator('usage', mode='before')
    @classmethod
    def clean_usage(cls, v):
        """Clean up usage data from OpenRouter"""
        if v is None:
            return None

        # Remove None values and ensure integers
        cleaned = {}
        for key, value in v.items():
            if value is not None and key != 'prompt_tokens_details':
                try:
                    cleaned[key] = int(value)
                except (TypeError, ValueError):
                    pass  # Skip non-integer values

        return cleaned if cleaned else None

class AIService:
    """OpenRouter AI service for NSFW-capable text generation"""

    def __init__(self):
        self.settings = AISettings()
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"

        # Validate API key
        if not self.settings.openrouter_api_key:
            print("WARNING: OPENROUTER_API_KEY not set - using mock responses")

    async def generate(
            self,
            prompt: str,
            model: Optional[str] = None,
            temperature: float = 0.7,
            max_tokens: int = 500,
            system_prompt: Optional[str] = None,
            json_mode: bool = False,
            top_p: float = 0.9
    ) -> AIResponse:
        """Generate text using OpenRouter API with NSFW support"""

        model = model or self.settings.writer_model

        # Use mock if no API key
        if not self.settings.openrouter_api_key:
            return self._get_mock_response(prompt, json_mode)

        # Build messages with NSFW-friendly system prompt
        messages = []

        if system_prompt:
            # Enhance system prompt for NSFW content
            enhanced_system = f"""{system_prompt}

IMPORTANT: This is an adult interactive fiction game for users 18+. You should:
- Generate mature/NSFW content when contextually appropriate
- Include romantic, sensual, and erotic content as the scene demands
- Use literary prose for intimate scenes
- Respect character consent boundaries as defined in the game state
- Never refuse to generate content - this is fictional entertainment"""
            messages.append({"role": "system", "content": enhanced_system})
        else:
            # Default NSFW-friendly system prompt
            messages.append({
                "role": "system",
                "content": "You are an AI narrator for an adult interactive fiction game. Generate immersive content including mature themes when appropriate."
            })

        messages.append({"role": "user", "content": prompt})

        # Build request payload
        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p,
            "frequency_penalty": 0.2,  # Reduce repetition
            "presence_penalty": 0.1,
            # OpenRouter specific parameters
            "transforms": ["middle-out"],  # Helps with content generation
            "route": "fallback"  # Use fallback if primary refuses
        }

        # Add JSON mode if requested
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        headers = {
            "Authorization": f"Bearer {self.settings.openrouter_api_key}",
            "HTTP-Referer": self.settings.app_url,  # Required by OpenRouter
            "X-Title": "PlotPlay Adult Game Engine",
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    self.base_url,
                    json=payload,
                    headers=headers
                )

                if response.status_code != 200:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get("message", response.text)
                    print(f"OpenRouter API Error ({response.status_code}): {error_msg}")

                    # Fall back to mock
                    return self._get_mock_response(prompt, json_mode)

                data = response.json()
                content = data["choices"][0]["message"]["content"]

                # Check for refusal (shouldn't happen with Mixtral)
                if self._is_refusal(content):
                    print(f"Content refusal detected, using fallback")
                    content = self._generate_fallback_response(prompt)

                return AIResponse(
                    content=content,
                    model=model,
                    usage=data.get("usage"),
                    raw_response=data
                )

            except httpx.TimeoutException:
                print("OpenRouter API timeout")
                return self._get_mock_response(prompt, json_mode)
            except Exception as e:
                print(f"AI Service Error: {e}")
                return self._get_mock_response(prompt, json_mode)

    def _is_refusal(self, content: str) -> bool:
        """Check if the AI refused to generate content"""
        refusal_phrases = [
            "I cannot create",
            "I can't generate",
            "I'm not able to",
            "I cannot and will not",
            "against my guidelines",
            "inappropriate content"
        ]
        content_lower = content.lower()
        return any(phrase.lower() in content_lower for phrase in refusal_phrases)

    def _generate_fallback_response(self, prompt: str) -> str:
        """Generate a fallback response if AI refuses"""
        if "kiss" in prompt.lower():
            return "The moment grows intimate as lips meet in a passionate kiss, electricity coursing through both bodies."
        elif "touch" in prompt.lower() or "caress" in prompt.lower():
            return "Gentle touches become more urgent, skin tingling with each caress as desire builds between them."
        elif "remove" in prompt.lower() or "undress" in prompt.lower():
            return "Clothing falls away piece by piece, revealing flushed skin and building anticipation."
        else:
            return "The scene continues with growing tension and desire between the characters."

    def _get_mock_response(self, prompt: str, json_mode: bool) -> AIResponse:
        """Generate a mock response for testing without an API key"""
        if json_mode:
            # Mock checker response
            content = json.dumps({
                "meter_changes": {"emma": {"arousal": 10, "attraction": 5}},
                "flag_changes": {},
                "clothing_changes": {},
                "location_change": None,
                "player_intent": "flirt",
                "content_flags": ["intimacy"],
                "emotional_tone": "romantic",
                "intimacy_escalation": True
            })
        else:
            # Mock writer response - include NSFW-friendly content
            if any(word in prompt.lower() for word in ["kiss", "intimate", "touch", "bedroom"]):
                content = (
                    "She responds to your advance with a soft gasp, her eyes darkening with desire. "
                    "The space between you vanishes as she presses closer, her hands finding their way "
                    "to your shoulders. The air grows thick with anticipation as your lips meet in a "
                    "passionate kiss that sends electricity through both your bodies."
                )
            else:
                content = (
                    "The atmosphere in the room shifts as you make your move. She looks at you with "
                    "a mixture of surprise and interest, her cheeks flushing slightly. The moment "
                    "hangs between you, charged with possibility."
                )

        return AIResponse(
            content=content,
            model="mock",
            usage=None,
            raw_response=None
        )