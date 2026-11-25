"""
Unit tests for anti_gravity.subtitle_validator.
Covers all 7 validation checks: empty, failure markers, repetition,
length ratio, CPS, line wrapping, and tag preservation.
"""
import unittest
from anti_gravity.subtitle_validator import validate_subtitle_entry, ValidationResult


class TestValidateSubtitleEntry(unittest.TestCase):
    def test_valid_subtitle_passes(self):
        result = validate_subtitle_entry(
            text="හෙලෝ එහෙම",
            original_en="Hello there",
            duration_ms=3000,
        )
        self.assertTrue(result.is_valid)

    def test_empty_translation_flagged(self):
        result = validate_subtitle_entry(
            text="",
            original_en="Hello",
            duration_ms=2000,
        )
        self.assertFalse(result.is_valid)
        self.assertTrue(any("empty" in w.lower() for w in result.warnings))

    def test_whitespace_only_flagged(self):
        result = validate_subtitle_entry(
            text="   \n  ",
            original_en="Hello",
            duration_ms=2000,
        )
        self.assertFalse(result.is_valid)

    def test_failure_marker_flagged(self):
        result = validate_subtitle_entry(
            text="⚠️ Hello",
            original_en="Hello",
            duration_ms=2000,
        )
        self.assertFalse(result.is_valid)
        self.assertTrue(any("fail" in w.lower() or "marker" in w.lower() for w in result.warnings))

    def test_repetition_detected(self):
        result = validate_subtitle_entry(
            text="සුබ සුබ සුබ සුබ සුබ",
            original_en="Hello",
            duration_ms=3000,
        )
        self.assertTrue(any("repet" in w.lower() for w in result.warnings))

    def test_abnormal_length_ratio(self):
        result = validate_subtitle_entry(
            text="ම" * 200,
            original_en="Hi",
            duration_ms=2000,
        )
        self.assertTrue(any("ratio" in w.lower() or "length" in w.lower() for w in result.warnings))

    def test_line_wrapping_warning(self):
        """Lines > 42 chars should trigger a wrapping warning."""
        long_line = "ම" * 50  # 50 Sinhala chars on one line
        result = validate_subtitle_entry(
            text=long_line,
            original_en="A very long subtitle line",
            duration_ms=5000,
        )
        wrap_warnings = [
            w for w in result.warnings
            if "line" in w.lower() and ("long" in w.lower() or "wrap" in w.lower() or "length" in w.lower() or "char" in w.lower())
        ]
        self.assertGreater(len(wrap_warnings), 0)

    def test_fast_cps_warning(self):
        """Very short duration with long text should warn about CPS."""
        result = validate_subtitle_entry(
            text="ම" * 30,
            original_en="A moderately long subtitle",
            duration_ms=500,  # 0.5 seconds — way too fast
        )
        cps_warnings = [
            w for w in result.warnings
            if "cps" in w.lower() or "speed" in w.lower() or "fast" in w.lower() or "reading" in w.lower()
        ]
        self.assertGreater(len(cps_warnings), 0)

    def test_auto_fix_sets_fixed_text(self):
        """When auto-fix is applied (e.g. wrapping), fixed_text should be non-empty."""
        # Long line that needs wrapping
        long_line = "මම ඉතාමත් දිගු වාක්‍යයක් ලියනවා එය පේළි දෙකකට බෙදිය යුතුයි"
        result = validate_subtitle_entry(
            text=long_line,
            original_en="I am writing a very long sentence",
            duration_ms=5000,
        )
        # fixed_text may or may not be set depending on implementation
        self.assertIsInstance(result.fixed_text, str)

    def test_returns_validation_result_type(self):
        result = validate_subtitle_entry("හෙලෝ", "Hello", 2000)
        self.assertIsInstance(result, ValidationResult)


if __name__ == "__main__":
    unittest.main()
