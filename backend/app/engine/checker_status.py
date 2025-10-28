"""Generates contextual status messages while streaming Checker response."""

import random


class CheckerStatusGenerator:
    """Generates fun, contextual status messages based on Checker streaming content."""

    # Message patterns for different contexts
    MESSAGES = {
        "meter": [
            "Hmm, something's changing...",
            "Let me check how you're feeling...",
            "Energy levels look different...",
            "Checking your stats...",
            "Something shifted inside you...",
        ],
        "character": [
            "Oh, {name}...",
            "Interesting reaction from {name}...",
            "{name} seems affected by this...",
            "Let's see what {name} thinks...",
            "Checking on {name}...",
            "What's {name} up to?",
            "Hmm, {name}'s involved here...",
            "{name}, {name}, {name}...",
            "Can't forget about {name}...",
            "{name} caught my attention...",
        ],
        "location": [
            "Wait, are we moving?",
            "New place, new possibilities...",
            "Location update incoming...",
            "Checking the surroundings...",
            "Where are we headed?",
        ],
        "clothing": [
            "Wardrobe check...",
            "Let me see what you're wearing...",
            "Outfit analysis...",
            "Fashion update...",
            "Checking your attire...",
        ],
        "memory": [
            "This seems memorable...",
            "Better write this down...",
            "Recording this moment...",
            "Worth remembering...",
            "Making a mental note...",
        ],
        "inventory": [
            "What's in your pockets?",
            "Inventory shuffle...",
            "Checking your belongings...",
            "Item management...",
            "Looking through your stuff...",
        ],
        "flag": [
            "Story progress noted...",
            "Marking this milestone...",
            "Updating story flags...",
            "Something important happened...",
        ],
        "start": [
            "OK, let's see what changed...",
            "Alright, analyzing the scene...",
            "Let me think about this...",
            "Time to make sense of everything...",
            "Processing what just happened...",
            "Let's break this down...",
        ],
        "generic": [
            "Making sense of all this...",
            "Just a moment...",
            "Processing the details...",
            "Almost there...",
            "Putting it all together...",
            "Hmm, interesting...",
            "Let me double-check something...",
            "Analyzing the nuances...",
            "Connecting the dots...",
            "One sec, thinking...",
            "Verifying the details...",
            "Checking my notes...",
            "This is getting complex...",
            "Bear with me...",
            "Parsing the scene...",
            "Reading between the lines...",
            "Crunching the numbers...",
            "Fact-checking...",
            "Cross-referencing...",
            "Dot the i's, cross the t's...",
            "Quality control...",
            "Sanity check...",
            "Second opinion...",
            "Devil's in the details...",
        ],
    }

    def __init__(self, character_names: list[str] | None = None):
        self.character_names = character_names or []
        self.used_contexts = set()
        self.message_count = 0

    def detect_context(self, partial_text: str) -> str | tuple | None:
        """Detect what context we're in based on partial streaming text."""
        text_lower = partial_text.lower()

        # Check for specific JSON keys/patterns
        if any(key in text_lower for key in ["meter_changes", "arousal", "attraction", "energy", "confidence"]):
            if "meter" not in self.used_contexts:
                self.used_contexts.add("meter")
                return "meter"

        # Check for character names
        for name in self.character_names:
            if name.lower() in text_lower and "character" not in self.used_contexts:
                self.used_contexts.add("character")
                return "character", name

        if any(key in text_lower for key in ["location_change", "move", "travel", "destination"]):
            if "location" not in self.used_contexts:
                self.used_contexts.add("location")
                return "location"

        if any(key in text_lower for key in ["clothing_changes", "wearing", "outfit", "dress", "attire"]):
            if "clothing" not in self.used_contexts:
                self.used_contexts.add("clothing")
                return "clothing"

        if any(key in text_lower for key in ["memory", "remember", "note"]):
            if "memory" not in self.used_contexts:
                self.used_contexts.add("memory")
                return "memory"

        if any(key in text_lower for key in ["inventory", "item", "possession"]):
            if "inventory" not in self.used_contexts:
                self.used_contexts.add("inventory")
                return "inventory"

        if any(key in text_lower for key in ["flag_changes", "milestone", "progress"]):
            if "flag" not in self.used_contexts:
                self.used_contexts.add("flag")
                return "flag"

        return None

    def generate_message(self, context: str | tuple | None = None) -> str:
        """Generate a status message based on context."""
        self.message_count += 1

        # The first message is always a "start" message
        if self.message_count == 1:
            return random.choice(self.MESSAGES["start"])

        # Context-specific message
        if context:
            if isinstance(context, tuple) and context[0] == "character":
                _, name = context
                template = random.choice(self.MESSAGES["character"])
                return template.format(name=name)
            elif isinstance(context, str) and context in self.MESSAGES:
                return random.choice(self.MESSAGES[context])

        # Generic fallback
        return random.choice(self.MESSAGES["generic"])

    @staticmethod
    def get_completion_message() -> str:
        """Get the final completion message."""
        return random.choice([
            "All set!",
            "Got it!",
            "Done analyzing!",
            "Everything's updated!",
            "Ready to continue!",
            "And... done!",
            "Phew, got it all!",
            "Crystal clear now!",
            "Locked in!",
            "Nailed it!",
            "Good to go!",
            "Check!",
            "Sorted!",
        ])
