"""
Unit tests for anti_gravity.glossary.
Covers word boundary matching, term ordering, and edge cases.
"""
import unittest
from anti_gravity.glossary import Glossary


class TestGlossary(unittest.TestCase):
    def setUp(self):
        self.glossary = Glossary()

    def test_glossary_loads(self):
        """Glossary should load at least some terms from glossary.json."""
        self.assertGreater(len(self.glossary.terms), 0)

    def test_find_relevant_terms_word_boundary(self):
        """'he' should NOT match inside 'the' or 'there'."""
        # Only run if 'he' is in the glossary; otherwise skip
        he_terms = [t for t in self.glossary.terms if t["en"].lower() == "he"]
        if not he_terms:
            self.skipTest("'he' not in glossary")
        matches = self.glossary.find_relevant_terms("the weather is nice")
        matched_en = [m["en"].lower() for m in matches]
        self.assertNotIn("he", matched_en)

    def test_find_relevant_terms_match(self):
        """A known glossary term should be found when present."""
        # Use a term we know exists (email is in the default glossary)
        matches = self.glossary.find_relevant_terms("Send me an email right now")
        matched_en = [m["en"].lower() for m in matches]
        self.assertIn("email", matched_en)

    def test_apply_glossary_basic(self):
        """apply_glossary should replace known terms in translated text."""
        # This is a smoke test; exact result depends on glossary content
        result = self.glossary.apply_glossary("I got an email today", "email")
        self.assertIsInstance(result, str)

    def test_find_relevant_terms_empty_text(self):
        matches = self.glossary.find_relevant_terms("")
        self.assertEqual(matches, [])

    def test_find_relevant_terms_no_matches(self):
        matches = self.glossary.find_relevant_terms("xyzzy flurbo zazzle")
        self.assertEqual(matches, [])


if __name__ == "__main__":
    unittest.main()

