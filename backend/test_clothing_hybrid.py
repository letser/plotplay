# backend/test_clothing_hybrid.py
import asyncio
from app.core.clothing_manager import ClothingManager, ClothingValidator
from app.services.ai_service import AIService
import json


async def test_hybrid_detection():
    """Test the hybrid clothing detection approach"""

    # Test validator
    validator = ClothingValidator()

    # Test scenarios
    scenarios = [
        {
            "narrative": "She slowly unbuttons her shirt, letting it fall open as she moves closer.",
            "ai_detected": {
                "removed": ["top"],
                "displaced": [],
                "added": []
            }
        },
        {
            "narrative": "He kicks off his shoes and pulls her closer.",
            "ai_detected": {
                "removed": ["feet"],
                "displaced": [],
                "added": []
            }
        },
        {
            "narrative": "The room grew warmer as they embraced passionately.",
            "ai_detected": {
                "removed": ["outer"],  # AI hallucinated this
                "displaced": [],
                "added": []
            }
        }
    ]

    print("Testing Hybrid Clothing Detection:\n")
    for i, scenario in enumerate(scenarios, 1):
        print(f"Scenario {i}:")
        print(f"Narrative: {scenario['narrative']}")
        print(f"AI Detected: {scenario['ai_detected']}")

        validated = validator.validate_changes(scenario['narrative'], scenario['ai_detected'])
        print(f"After Validation: {validated}")
        print()


async def test_with_ai():
    """Test with actual AI service"""
    ai_service = AIService()

    narrative = "Emma smiles seductively as she slowly removes her black dress, letting it pool at her feet."

    checker_prompt = f"""Analyze this narrative for clothing changes.

NARRATIVE: "{narrative}"

Extract clothing changes and return as JSON:
{{
    "emma": {{
        "removed": ["dress"],
        "displaced": [],
        "added": []
    }}
}}"""

    print("Testing with AI Service:")
    response = await ai_service.generate(
        prompt=checker_prompt,
        temperature=0.1,
        json_mode=True
    )

    print(f"AI Response: {response.content}")

    # Validate the AI response
    validator = ClothingValidator()
    try:
        ai_detected = json.loads(response.content)
        validated = validator.validate_changes(narrative, ai_detected.get('emma', {}))
        print(f"Validated: {validated}")
    except:
        print("Failed to parse AI response")


if __name__ == "__main__":
    asyncio.run(test_hybrid_detection())
    print("\n" + "=" * 50 + "\n")
    asyncio.run(test_with_ai())