"""
Comprehensive tests for the clean_sinhala_output filter function.
Covers prefix removal, note cutoff, code fences, Wikipedia artifacts,
multi-speaker lines, and failure marking.
"""
import unittest
from anti_gravity.translator_engine import clean_sinhala_output


class TestCleanSinhalaOutput(unittest.TestCase):
    """Tests for clean_sinhala_output(raw_text, original_input)."""

    def test_basic_prefix_removal(self):
        result = clean_sinhala_output("Translation: සුබ උදෑසනක්!", "Good morning")
        self.assertEqual(result, "සුබ උදෑසනක්!")

    def test_verbose_model_preamble(self):
        raw = (
            "You are a native Sri Lankan Sinhala translator and language editor.\n"
            "Translation requirements:\n"
            "1. Preserve original meaning.\n"
            "Translate this English subtitle to natural Sinhala:\n"
            "Good morning!\n\n"
            "Translation: සුබ උදෑසනක්!\n"
            "Note: This is casual greeting."
        )
        result = clean_sinhala_output(raw, "Good morning!")
        self.assertEqual(result, "සුබ උදෑසනක්!")

    def test_model_turn_tags(self):
        raw = "<start_of_turn>model\nසිංහල: මම හෙට එන්නම්.<end_of_turn>"
        result = clean_sinhala_output(raw, "I will come tomorrow")
        self.assertEqual(result, "මම හෙට එන්නම්.")

    def test_inline_translation_prefix(self):
        result = clean_sinhala_output("Here is the translation:\nඅපි යමු.", "Let's go")
        self.assertEqual(result, "අපි යමු.")

    def test_complex_qa_format(self):
        raw = (
            'English subtitle:\n"How are you?"\n\n'
            "Sinhala translation:\nඔයාට කොහොමද?"
        )
        result = clean_sinhala_output(raw, "How are you?")
        self.assertEqual(result, "ඔයාට කොහොමද?")

    def test_parenthetical_note_removal(self):
        raw = "සුබ උදෑසනක්! (සටහන: මෙය සුබපැතුමකි)"
        result = clean_sinhala_output(raw, "Good morning!")
        self.assertEqual(result, "සුබ උදෑසනක්!")

    def test_wikipedia_remark_cutoff(self):
        raw = (
            "ඔයා දැන් කොහෙද යන්නේ?\n\n"
            "විකිපීඩියාවට අදාළ සටහනක් ලෙස, මෙම පරිවර්තනයන් සකස් කර ඇත්තේ ශ"
        )
        result = clean_sinhala_output(raw, "Where are you going right now?")
        self.assertEqual(result, "ඔයා දැන් කොහෙද යන්නේ?")

    def test_english_echo_cutoff(self):
        raw = (
            "ඒක කරන්නේ ඇයි?\n\n"
            "*English subtitle: I'm going to tell you a secret.*\n"
            "Spoken Sinhala:"
        )
        result = clean_sinhala_output(raw, "Why did you do that?")
        self.assertEqual(result, "ඒක කරන්නේ ඇයි?")

    def test_translation_note_cutoff(self):
        raw = (
            "බය වෙන්න එපා, හැමදේම හරි යයි.\n\n"
            "*Translation Note:* This line uses..."
        )
        result = clean_sinhala_output(raw, "Don't worry, everything is going to be fine.")
        self.assertEqual(result, "බය වෙන්න එපා, හැමදේම හරි යයි.")

    def test_multi_speaker_preservation(self):
        raw = "- කොහොමද ඔයාට?\n- මම හොඳින්."
        result = clean_sinhala_output(raw, "- How are you?\n- I am fine.")
        self.assertEqual(result, "- කොහොමද ඔයාට?\n- මම හොඳින්.")

    def test_failure_marker_when_no_sinhala(self):
        """When the output has no Sinhala characters, it should be marked with ⚠️."""
        result = clean_sinhala_output("Hello world", "Hello world")
        self.assertTrue(result.startswith("⚠️"), f"Expected failure marker, got: {result!r}")

    def test_empty_input(self):
        result = clean_sinhala_output("", "Hello")
        self.assertTrue(result.startswith("⚠️") or result == "")


if __name__ == "__main__":
    unittest.main()
