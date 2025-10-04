"""
Test for Character model dialogue_style and author_notes fields
Add this to backend/tests/test_character_fields.py
"""
import pytest
from app.models.character import Character
from app.models.flag import Flag
from app.models.meters import Meter


def test_character_dialogue_style():
    """Test that dialogue_style field works correctly."""

    # Create a character with dialogue_style
    character = Character(
        id="emma",
        name="Emma",
        age=22,
        gender="female",
        dialogue_style="warm, teasing, uses coffee metaphors",  # New field
        author_notes="Emma starts shy but becomes flirty when trust > 50."  # Existing field
    )

    assert character.dialogue_style == "warm, teasing, uses coffee metaphors"
    assert character.author_notes == "Emma starts shy but becomes flirty when trust > 50."

    # Test that it's optional
    character_minimal = Character(
        id="player",
        name="You",
        gender="unspecified"
    )

    assert character_minimal.dialogue_style is None
    assert character_minimal.author_notes is None


def test_character_with_all_fields():
    """Test that all character fields work together."""

    character = Character(
        id="alex",
        name="Alex",
        age=25,
        gender="nonbinary",
        pronouns=["they", "them"],
        role="philosopher",
        description="A thoughtful regular at the coffee shop",
        tags=["friend", "intellectual"],
        dialogue_style="verbose, philosophical, uses big words",
        author_notes="Alex provides the intellectual subplot. Keep conversations cerebral.",
        meters={
            "friendship": {"min": 0, "max": 100, "default": 30}
        },
        flags={
            "first_debate": Flag(type="bool", default=False)
        },
        inventory={"notebook": 1, "pen": 2}
    )

    # Verify all fields
    assert character.id == "alex"
    assert character.dialogue_style == "verbose, philosophical, uses big words"
    assert character.author_notes == "Alex provides the intellectual subplot. Keep conversations cerebral."
    assert "friend" in character.tags
    assert character.pronouns == ["they", "them"]
    assert character.inventory["notebook"] == 1


def test_character_serialization():
    """Test that character can be serialized to dict/JSON."""

    character = Character(
        id="test",
        name="Test Character",
        age=20,
        gender="female",
        dialogue_style="test style",
        author_notes="test notes"
    )

    # Convert to dict
    char_dict = character.model_dump()

    assert char_dict["dialogue_style"] == "test style"
    assert char_dict["author_notes"] == "test notes"

    # Ensure it can be recreated from dict
    character_copy = Character(**char_dict)
    assert character_copy.dialogue_style == character.dialogue_style
    assert character_copy.author_notes == character.author_notes


if __name__ == "__main__":
    test_character_dialogue_style()
    test_character_with_all_fields()
    test_character_serialization()
    print("✅ All character field tests passed!")