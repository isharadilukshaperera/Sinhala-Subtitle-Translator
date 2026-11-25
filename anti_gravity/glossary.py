"""
Glossary lookup and terminology management module.
Loads user and built-in terms to guide the translation engine with natural spoken transliterations.
"""
import os
import json
import logging
from typing import Dict, List, Tuple
import regex as re

logger = logging.getLogger("anti_gravity.glossary")

DEFAULT_GLOSSARY_PATH = os.path.join(os.path.dirname(__file__), "data", "glossary.json")

class GlossaryManager:
    def __init__(self, glossary_path: str = DEFAULT_GLOSSARY_PATH):
        self.glossary_path = glossary_path
        self.terms: Dict[str, str] = {}
        self.load()

    def load(self):
        """Loads dictionary terms from json file."""
        if os.path.exists(self.glossary_path):
            try:
                with open(self.glossary_path, "r", encoding="utf-8") as f:
                    self.terms = json.load(f)
            except Exception as e:
                logger.warning(f"Could not load glossary from {self.glossary_path}: {e}")
                self.terms = {}
        else:
            self.terms = {}

    def save(self):
        """Saves current dictionary terms to json file."""
        os.makedirs(os.path.dirname(self.glossary_path), exist_ok=True)
        try:
            with open(self.glossary_path, "w", encoding="utf-8") as f:
                json.dump(self.terms, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save glossary: {e}")

    def add_term(self, en_term: str, si_term: str):
        self.terms[en_term.strip().lower()] = si_term.strip()
        self.save()

    def remove_term(self, en_term: str):
        key = en_term.strip().lower()
        if key in self.terms:
            del self.terms[key]
            self.save()

    def find_relevant_terms(self, text: str) -> List[Tuple[str, str]]:
        """Finds any glossary terms that appear in the English input line."""
        if not text or not self.terms:
            return []

        found = []
        lower_text = text.lower()
        # Sort terms by length descending to match multi-word phrases first
        sorted_keys = sorted(self.terms.keys(), key=len, reverse=True)

        for key in sorted_keys:
            pattern = rf"\b{re.escape(key)}\b"
            if re.search(pattern, lower_text):
                found.append((key, self.terms[key]))

        return found

    def apply_glossary(self, original_en: str, translated_si: str) -> str:
        """
        Aligns translation using glossary terms:
        If an English loan word in the glossary appears directly in Latin script in translated_si,
        replaces it with the glossary's spoken transliteration.
        """
        if not translated_si or not self.terms:
            return translated_si

        result = translated_si
        # Sort by key length descending to handle multi-word terms first (e.g. 'train station' before 'train')
        sorted_keys = sorted(self.terms.keys(), key=len, reverse=True)
        for en_term in sorted_keys:
            si_term = self.terms[en_term]
            pattern = rf"(?i)\b{re.escape(en_term)}\b"
            if re.search(pattern, result):
                result = re.sub(pattern, si_term, result)

        return result

