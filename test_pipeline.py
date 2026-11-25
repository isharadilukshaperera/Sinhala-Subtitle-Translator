"""
Integration test for the core translation pipeline.
Validates clean_sinhala_output filter and SubtitleFile parsing.
"""
import unittest
from pathlib import Path

from anti_gravity.translator_engine import clean_sinhala_output
from anti_gravity.subtitle_parser import SubtitleFile

SAMPLE_SRT = Path(__file__).parent / "test_sample.srt"


class TestTranslationPipeline(unittest.TestCase):
    def test_clean_basic_prefix_removal(self):
        self.assertEqual(
            clean_sinhala_output("Translation: සුබ උදෑසනක්!", "Good morning!"),
            "සුබ උදෑසනක්!",
        )

    def test_clean_quoted_text(self):
        self.assertEqual(
            clean_sinhala_output('"සුබ පැතුම්"', "Blessings"),
            "සුබ පැතුම්",
        )

    def test_clean_note_cutoff(self):
        self.assertEqual(
            clean_sinhala_output(
                "සිංහල පරිවර්තනය: ආයුබෝවන්\nNote: This is formal.",
                "Welcome",
            ),
            "ආයුබෝවන්",
        )

    def test_clean_inline_prefix(self):
        self.assertEqual(
            clean_sinhala_output("Here is the translation: මම එන්නම්", "I will come"),
            "මම එන්නම්",
        )

    def test_clean_code_fences(self):
        self.assertEqual(
            clean_sinhala_output("```\nස්තූතියි\n```", "Thank you"),
            "ස්තූතියි",
        )

    def test_subtitle_parsing(self):
        self.assertTrue(SAMPLE_SRT.exists(), f"Sample SRT not found: {SAMPLE_SRT}")
        sub = SubtitleFile(str(SAMPLE_SRT))
        self.assertEqual(sub.total_lines, 4)
        self.assertEqual(sub.items[0].index, 1)
        self.assertIn("Good morning", sub.items[0].original_text)

    def test_subtitle_timestamps_are_strings(self):
        sub = SubtitleFile(str(SAMPLE_SRT))
        for item in sub.items:
            self.assertIsInstance(item.start_time, str)
            self.assertIsInstance(item.end_time, str)
            self.assertGreater(item.end_ms, item.start_ms)


if __name__ == "__main__":
    unittest.main()
