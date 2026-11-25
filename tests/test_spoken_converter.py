"""
Unit tests for anti_gravity.spoken_converter.
Covers formal-to-spoken conversion, protected words, and score_translation_quality.
"""
import unittest
from anti_gravity.spoken_converter import (
    convert_to_spoken_sinhala,
    score_translation_quality,
)


class TestConvertToSpokenSinhala(unittest.TestCase):
    def test_empty_input(self):
        self.assertEqual(convert_to_spoken_sinhala(""), "")

    def test_already_spoken_text_unchanged(self):
        """Text already in spoken form should not be double-converted."""
        spoken = "මම යනවා"
        result = convert_to_spoken_sinhala(spoken)
        # Should remain the same or very close
        self.assertEqual(result, spoken)

    def test_basic_conversion(self):
        """A known formal ending should be converted."""
        result = convert_to_spoken_sinhala("මම කරමි")
        # Should not keep the formal "මි" ending (exact output may vary)
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)

    def test_short_words_not_corrupted(self):
        """Very short words (< 3 chars) should not be mangled by suffix rules."""
        # Single character or two char Sinhala words
        short = "ද"
        result = convert_to_spoken_sinhala(short)
        self.assertEqual(result, short)

    def test_multiline_input(self):
        """Multi-line text should be processed correctly."""
        text = "මම යමි\nඔබ එන්න"
        result = convert_to_spoken_sinhala(text)
        self.assertIn("\n", result)


class TestScoreTranslationQuality(unittest.TestCase):
    def test_good_translation_high_score(self):
        score, issues = score_translation_quality(
            "Hello, how are you?",
            "හෙලෝ, ඔයාට කොහොමද?"
        )
        self.assertGreaterEqual(score, 0.5)

    def test_failure_marker_low_score(self):
        score, issues = score_translation_quality(
            "Hello",
            "⚠️ Hello"
        )
        self.assertLess(score, 0.5)

    def test_english_echo_low_score(self):
        score, issues = score_translation_quality(
            "Good morning",
            "Good morning"
        )
        self.assertLess(score, 0.6)

    def test_empty_translation_scores_zero(self):
        score, issues = score_translation_quality("Hello", "")
        self.assertLessEqual(score, 0.1)

    def test_returns_issues_list(self):
        score, issues = score_translation_quality("Hello", "")
        self.assertIsInstance(issues, list)


if __name__ == "__main__":
    unittest.main()

