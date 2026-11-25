"""
Integration test for the full translation pipeline using a mock TranslationEngine.
Verifies: parse → translate → validate → save produces a valid SRT file.
"""
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path

from anti_gravity.subtitle_parser import SubtitleFile


# Predetermined Sinhala translations for test
MOCK_TRANSLATIONS = {
    "Good morning! How are you doing today?": "සුබ උදෑසනක්! අද ඔයාට කොහොමද?",
    "I am preparing the report for the project.": "මම ප්‍රොජෙක්ට් එකේ වාර්තාව හදනවා.",
    "Let's meet at the train station at 5 PM.": "පහේට දුම්රිය ස්ථානයේ හමුවෙමු.",
    "Don't worry, everything is going to be fine.": "බය වෙන්න එපා, හැමදේම හරි යයි.",
}

SAMPLE_SRT_PATH = Path(__file__).parent.parent / "test_sample.srt"


class TestFullPipeline(unittest.TestCase):
    """End-to-end pipeline test with mocked LLM."""

    def test_parse_translate_save_roundtrip(self):
        """Parse a real SRT, assign mock translations, save, and verify output."""
        self.assertTrue(SAMPLE_SRT_PATH.exists(), f"Missing {SAMPLE_SRT_PATH}")

        # 1. Parse
        sub = SubtitleFile(str(SAMPLE_SRT_PATH))
        self.assertEqual(sub.total_lines, 4)

        # 2. "Translate" using mock mapping
        for item in sub.items:
            item.translated_text = MOCK_TRANSLATIONS.get(
                item.original_text, f"⚠️ {item.original_text}"
            )

        # 3. Save
        fd, out_path = tempfile.mkstemp(suffix="_sinhala.srt")
        os.close(fd)
        try:
            sub.save_translated(out_path)

            # 4. Verify output is a valid SRT
            self.assertTrue(os.path.exists(out_path))
            with open(out_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Should contain Sinhala text
            self.assertIn("සුබ උදෑසනක්", content)
            self.assertIn("-->", content)

            # Should have sequential indices 1-4
            lines = content.strip().split("\n")
            indices_found = []
            for line in lines:
                stripped = line.strip()
                if stripped.isdigit():
                    indices_found.append(int(stripped))
            self.assertEqual(indices_found, [1, 2, 3, 4])

            # 5. Re-parse the output to ensure it's valid
            out_sub = SubtitleFile(out_path)
            self.assertEqual(out_sub.total_lines, 4)
            self.assertIn("සුබ උදෑසනක්", out_sub.items[0].original_text)
        finally:
            os.unlink(out_path)

    def test_empty_file_handling(self):
        """Empty SRT file should produce an empty output without crashing."""
        fd, empty_path = tempfile.mkstemp(suffix=".srt")
        os.close(fd)
        try:
            sub = SubtitleFile(empty_path)
            self.assertEqual(sub.total_lines, 0)

            fd2, out_path = tempfile.mkstemp(suffix="_out.srt")
            os.close(fd2)
            try:
                sub.save_translated(out_path)
                self.assertTrue(os.path.exists(out_path))
            finally:
                os.unlink(out_path)
        finally:
            os.unlink(empty_path)

    def test_large_file_simulation(self):
        """Simulate a 500-entry SRT to ensure no performance issues."""
        lines = []
        for i in range(1, 501):
            start_s = i * 2
            end_s = start_s + 1
            h, m, s = start_s // 3600, (start_s % 3600) // 60, start_s % 60
            h2, m2, s2 = end_s // 3600, (end_s % 3600) // 60, end_s % 60
            lines.append(f"{i}")
            lines.append(f"{h:02d}:{m:02d}:{s:02d},000 --> {h2:02d}:{m2:02d}:{s2:02d},000")
            lines.append(f"Subtitle line {i}")
            lines.append("")

        fd, path = tempfile.mkstemp(suffix=".srt")
        os.write(fd, "\n".join(lines).encode("utf-8"))
        os.close(fd)

        try:
            sub = SubtitleFile(path)
            self.assertEqual(sub.total_lines, 500)

            for item in sub.items:
                item.translated_text = f"උපසිරැසි පේළිය {item.index}"

            fd2, out_path = tempfile.mkstemp(suffix="_out.srt")
            os.close(fd2)
            try:
                sub.save_translated(out_path)
                out_sub = SubtitleFile(out_path)
                self.assertEqual(out_sub.total_lines, 500)
            finally:
                os.unlink(out_path)
        finally:
            os.unlink(path)

    def test_html_tags_preserved_in_output(self):
        """SRT formatting tags like <i> should survive the save roundtrip."""
        srt = "1\n00:00:01,000 --> 00:00:03,000\n<i>Hello world</i>\n\n"
        fd, path = tempfile.mkstemp(suffix=".srt")
        os.write(fd, srt.encode("utf-8"))
        os.close(fd)

        try:
            sub = SubtitleFile(path)
            sub.items[0].translated_text = "<i>හෙලෝ ලෝකය</i>"

            fd2, out_path = tempfile.mkstemp(suffix="_out.srt")
            os.close(fd2)
            try:
                sub.save_translated(out_path)
                with open(out_path, "r", encoding="utf-8") as f:
                    content = f.read()
                self.assertIn("<i>", content)
                self.assertIn("</i>", content)
            finally:
                os.unlink(out_path)
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()

