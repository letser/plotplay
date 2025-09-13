import asyncio
import httpx
from app.services.ai_service import AIService


async def test_ai_connection():
    """Test AI service connection"""
    service = AIService()

    # Test Writer model
    print("Testing Writer model...")
    writer_response = await service.generate(
        prompt="Describe a mysterious tavern in 2 sentences.",
        temperature=0.8,
        max_tokens=100
    )
    print(f"Writer: {writer_response.content}\n")

    # Test Checker model
    print("Testing Checker model...")
    checker_prompt = """Extract the emotion from this text and return JSON:
    "She smiled warmly and touched his hand."

    Return: {"emotion": "affectionate"}"""

    checker_response = await service.generate(
        prompt=checker_prompt,
        model=service.settings.checker_model,
        temperature=0.1,
        json_mode=True
    )
    print(f"Checker: {checker_response.content}\n")


if __name__ == "__main__":
    asyncio.run(test_ai_connection())