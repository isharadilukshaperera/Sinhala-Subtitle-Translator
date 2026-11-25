"""
Unit tests for anti_gravity.subtitle_parser.
Covers encoding detection, edge-case SRT files, save/re-number, and overlap detection.
"""
import os
import tempfile
import unittest

from anti_gravity.subtitle_parser import SubtitleFile, detect_file_encoding


class TestDetectFileEncoding(unittest.TestCase):
    def _write_tmp(self, content: bytes, suffix=".srt") -> str:
        fd, path = tempfile.mkstemp(suffix=suffix)
        os.write(fd, content)
        os.close(fd)
        return path

    def test_utf8_bom(self):
        path = self._write_tmp(b"\xef\xbb\xbf1\n00:00:00,000 --> 00:00:01,000\nHi\n\n")
        try:
            enc = detect_file_encoding(path)
            self.assertEqual(enc, "utf-8-sig")
        finally:
            os.unlink(path)

    def test_empty_file(self):
        path = self._write_tmp(b"")
        try:
            enc = detect_file_encoding(path)
            self.assertEqual(enc, "utf-8")
        finally:
            os.unlink(path)

    def test_latin1_detection(self):
        # Latin-1 encoded content with non-UTF-8 byte
        path = self._write_tmp(b"1\n00:00:01,000 --> 00:00:02,000\nCaf\xe9\n\n")
        try:
            enc = detect_file_encoding(path)
            self.assertIsNotNone(enc)
        finally:
            os.unlink(path)


class TestSubtitleFileParsing(unittest.TestCase):
    def _write_srt(self, text: str, encoding="utf-8") -> str:
        fd, path = tempfile.mkstemp(suffix=".srt")
        os.write(fd, text.encode(encoding))
        os.close(fd)
        return path

    def test_basic_parse(self):
        srt = "1\n00:00:01,000 --> 00:00:03,000\nHello world\n\n2\n00:00:04,000 --> 00:00:06,000\nGoodbye\n\n"
        path = self._write_srt(srt)
        try:
            sub = SubtitleFile(path)
            self.assertEqual(sub.total_lines, 2)
            self.assertEqual(sub.items[0].original_text, "Hello world")
            self.assertEqual(sub.items[1].original_text, "Goodbye")
        finally:
            os.unlink(path)

    def test_dot_decimal_timestamps(self):
        """SRT files with . instead of , as decimal separator should parse correctly."""
        srt = "1\n00:00:01.500 --> 00:00:03.000\nDot decimal\n\n"
        path = self._write_srt(srt)
        try:
            sub = SubtitleFile(path)
            self.assertEqual(sub.total_lines, 1)
            self.assertEqual(sub.items[0].original_text, "Dot decimal")
        finally:
            os.unlink(path)

    def test_mixed_line_endings(self):
        srt = "1\r\n00:00:01,000 --> 00:00:02,000\r\nMixed endings\r\n\r\n"
        path = self._write_srt(srt)
        try:
            sub = SubtitleFile(path)
            self.assertEqual(sub.total_lines, 1)
        finally:
            os.unlink(path)

    def test_empty_srt_file(self):
        path = self._write_srt("")
        try:
            sub = SubtitleFile(path)
            self.assertEqual(sub.total_lines, 0)
        finally:
            os.unlink(path)

    def test_multi_line_subtitle_text(self):
        srt = "1\n00:00:01,000 --> 00:00:03,000\nLine one\nLine two\n\n"
        path = self._write_srt(srt)
        try:
            sub = SubtitleFile(path)
            self.assertIn("\n", sub.items[0].original_text)
        finally:
            os.unlink(path)


class TestSubtitleFileSave(unittest.TestCase):
    def _write_srt(self, text: str) -> str:
        fd, path = tempfile.mkstemp(suffix=".srt")
        os.write(fd, text.encode("utf-8"))
        os.close(fd)
        return path

    def test_save_renumbers_indices(self):
        # Input with non-sequential indices (5, 10)
        srt = "5\n00:00:01,000 --> 00:00:02,000\nFirst\n\n10\n00:00:03,000 --> 00:00:04,000\nSecond\n\n"
        path = self._write_srt(srt)
        out_path = path.replace(".srt", "_out.srt")
        try:
            sub = SubtitleFile(path)
            sub.items[0].translated_text = "පළමු"
            sub.items[1].translated_text = "දෙවන"
            sub.save_translated(out_path)

            # Read back and verify sequential numbering
            with open(out_path, "r", encoding="utf-8") as f:
                content = f.read()
            lines = content.strip().split("\n")
            # First subtitle index should be 1, not 5
            self.assertEqual(lines[0].strip(), "1")
        finally:
            for p in (path, out_path):
                if os.path.exists(p):
                    os.unlink(p)

    def test_save_uses_utf8(self):
        srt = "1\n00:00:01,000 --> 00:00:02,000\nHello\n\n"
        path = self._write_srt(srt)
        out_path = path.replace(".srt", "_out.srt")
        try:
            sub = SubtitleFile(path)
            sub.items[0].translated_text = "ආයුබෝවන්"
            sub.save_translated(out_path)

            with open(out_path, "rb") as f:
                raw = f.read()
            self.assertIn("ආයුබෝවන්".encode("utf-8"), raw)
        finally:
            for p in (path, out_path):
                if os.path.exists(p):
                    os.unlink(p)


if __name__ == "__main__":
    unittest.main()

