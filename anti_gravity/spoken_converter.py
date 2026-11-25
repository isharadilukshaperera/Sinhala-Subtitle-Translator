"""
Spoken Sinhala Rule Engine and Converter for Translator.
Converts residual written/literary Sinhala (ලිඛිත සිංහල) forms into natural
everyday spoken Sinhala (කතා කරන සිංහල / කථා ව්‍යවහාරය) and validates dialogue quality.
Uses Unicode-aware regex matching to handle Sinhala conjuncts and vowel modifiers correctly.
"""
import regex as re
from typing import List, Tuple, Dict

# Specific multi-word literary phrases (checked first)
WRITTEN_TO_SPOKEN_PHRASES: List[Tuple[str, str]] = [
    (r"\bසිදු\s*කරනු\s*ලබන\b", "කරන"),
    (r"\bසිදු\s*කරනවා\b", "කරනවා"),
    (r"\bසිදු\s*කරයි\b", "කරනවා"),
    (r"\bසිදු\s*කරන්නෙමු\b", "කරමු"),
    (r"\bසිදු\s*විය\b", "වුණා"),
    (r"\bසිදු\s*වී\s*ඇත\b", "වෙලා තියෙනවා"),
    (r"\bපැමිණෙන\s*ලෙස\b", "එන්න කියලා"),
    (r"\bපැමිණියේ\s*නැත\b", "ආවේ නෑ"),
    (r"\bපැමිණ\s*නැත\b", "ඇවිත් නෑ"),
    (r"\bපැමිණිය\s*හැක\b", "එන්න පුළුවන්"),
    (r"\bපැමිණිය\s*නොහැක\b", "එන්න බෑ"),
    (r"\bනොහැකි\s*ය\b", "බෑ"),
    (r"\bනොහැක\b", "බෑ"),
    (r"\bහැකි\s*ය\b", "පුළුවන්"),
    (r"\bකළ\s*යුතුය\b", "කරන්න ඕනේ"),
    (r"\bකළ\s*යුතු\s*වේ\b", "කරන්න ඕනේ"),
    (r"\bයුතු\s*වේ\b", "ඕනේ"),
    (r"\bයුතුය\b", "ඕනේ"),
    (r"\bදැන\s*සිටියේ\s*නැත\b", "දැනගෙන හිටියේ නෑ"),
    (r"\bදැන\s*නොසිටියේය\b", "දැනගෙන හිටියේ නෑ"),
    (r"\bනික්ම\s*ගියේය\b", "පිටත් වුණා"),
    # Spoken locations and phrasings
    (r"\bදුම්රිය\s*ස්ථානයේදී\b", "ස්ටේෂන් එකේදී"),
    (r"\bදුම්රිය\s*ස්ථානයේ\b", "ස්ටේෂන් එකේ"),
    (r"\bදුම්රිය\s*ස්ථානය\b", "ස්ටේෂන් එක"),
    (r"\bදුම්රිය\s*පොළේදී\b", "ස්ටේෂන් එකේදී"),
    (r"\bදුම්රිය\s*පොළේ\b", "ස්ටේෂන් එකේ"),
    (r"\bදුම්රිය\s*පොළ\b", "ස්ටේෂන් එක"),
    (r"\bබස්\s*නැවතුම්පොළ\b", "බස් හෝල්ට් එක"),
    (r"\bබස්\s*නැවතුම\b", "බස් හෝල්ට් එක"),
    (r"\bසූදානම්\s*කරමින්\s*ඉන්නේ\b", "ලෑස්ති කරනවා"),
    (r"\bසූදානම්\s*කරනවා\b", "ලෑස්ති කරනවා"),
    (r"\bසූදානම්\s*වෙනවා\b", "ලෑස්ති වෙනවා"),
    (r"\bකොහොමද\s*ඉන්නේ\b", "කොහොමද ඔයාට"),
]

# Vocabulary and pronoun substitutions
WRITTEN_TO_SPOKEN_WORDS: List[Tuple[str, str]] = [
    # Common model hallucinations & literary vocabulary
    (r"\bබිසවිට\b", "බිරිඳට"),
    (r"\bබිසවගේ\b", "බිරිඳගේ"),
    (r"\bබිසව\b", "බිරිඳ"),
    (r"\bමිය\s*ගිය\b", "නැතිවුණු"),
    (r"\bමිය\s*ගියා\b", "මැරුණා"),
    (r"\bදුවොල\b", "දුවලා"),
    (r"\bදුවොත්\b", "දුවලා"),
    (r"\bදුවොයි\b", "දුවෙක්"),
    (r"\bකිසිදා\b", "කවදාවත්"),
    (r"\bසැමදාම\b", "හැමදාම"),
    (r"\bසැමදා\b", "හැමදාම"),
    (r"\bසැමවිටම\b", "හැමතිස්සෙම"),
    (r"\bනිවෙස්වලින්\b", "ගෙවල්වලින්"),
    (r"\bනිවසින්\b", "ගෙදරින්"),
    (r"\bනිවසට\b", "ගෙදරට"),
    (r"\bනිවස\b", "ගෙදර"),
    (r"\bවිවාහය\b", "කසාදේ"),
    (r"\bවිවාහ\s*වෙන්න\b", "කසාද බඳින්න"),
    (r"\bවිවා\s*වෙන්න\b", "කසාද බඳින්න"),
    (r"\bවසර\s*ගණනාවි\b", "අවුරුදු ගාණක්"),
    (r"\bවසර\s*ගණනාවක්\b", "අවුරුදු ගාණක්"),
    (r"\bපෙනුමෙන්\s*ගත්\s*කළ\b", "පෙනුමෙන්"),
    (r"\bසිනාසෙව්වා\b", "හිනැස්සුවා"),

    # Pronouns
    (r"\bඔබට\b", "ඔයාට"),
    (r"\bඔබගේ\b", "ඔයාගේ"),
    (r"\bඔබෙන්\b", "ඔයාගෙන්"),
    (r"\bඔබව\b", "ඔයාව"),
    (r"\bඔබ\b", "ඔයා"),

    (r"\bඔහුට\b", "එයාට"),
    (r"\bඔහුගේ\b", "එයාගේ"),
    (r"\bඔහුගෙන්\b", "එයාගෙන්"),
    (r"\bඔහුව\b", "එයාව"),
    (r"\bඔහු\b", "එයා"),

    (r"\bඇයට\b", "එයාට"),
    (r"\bඇයගේ\b", "එයාගේ"),
    (r"\bඇයගෙන්\b", "එයාගෙන්"),
    (r"\bඇයව\b", "එයාව"),
    (r"\bඇය\b", "එයා"),

    (r"\bඔවුන්ට\b", "ඒගොල්ලන්ට"),
    (r"\bඔවුන්ගේ\b", "ඒගොල්ලන්ගේ"),
    (r"\bඔවුන්ගෙන්\b", "ඒගොල්ලන්ගෙන්"),
    (r"\bඔවුන්ව\b", "ඒගොල්ලන්ව"),
    (r"\bඔවුන්\b", "ඒගොල්ලෝ"),

    # Negation
    (r"\bනොවේද\b", "නෙවෙයිද"),
    (r"\bනොවේ\b", "නෙවෙයි"),
    (r"\bනැත\b", "නෑ"),
    (r"\bනැත්තේය\b", "නැත්තේ"),

    # Verbs (exact word forms)
    (r"\bපැමිණියා\b", "ආවා"),
    (r"\bපැමිණියේය\b", "ආවා"),
    (r"\bපැමිණේ\b", "එනවා"),
    (r"\bපැමිණෙයි\b", "එනවා"),
    (r"\bපැමිණෙනවා\b", "එනවා"),
    (r"\bපැමිණෙන්න\b", "එන්න"),
    (r"\bපැමිණ\b", "ඇවිත්"),
    (r"\bපවසයි\b", "කියනවා"),
    (r"\bපැවසුවේය\b", "කිව්වා"),
    (r"\bපැවසීය\b", "කිව්වා"),
    (r"\bපවසන්න\b", "කියන්න"),
    (r"\bලැබේ\b", "ලැබෙනවා"),
    (r"\bලැබුණි\b", "ලැබුණා"),
    (r"\bලැබුණේය\b", "ලැබුණා"),
    (r"\bපවතී\b", "තියෙනවා"),
    (r"\bපැවතුණි\b", "තිබුණා"),
    (r"\bදනී\b", "දන්නවා"),
    (r"\bදනිමි\b", "දන්නවා"),
    (r"\bසිටියි\b", "ඉන්නවා"),
    (r"\bසිටියේය\b", "හිටියා"),
    (r"\bසිටියහ\b", "හිටියා"),
    (r"\bවෙයි\b", "වෙනවා"),
    (r"\bවිය\b", "වුණා"),
    (r"\bවූයේය\b", "වුණා"),
    (r"\bදෙයි\b", "දෙනවා"),
    (r"\bදුන්නේය\b", "දුන්නා"),
    (r"\bගනියි\b", "ගන්නවා"),
    (r"\bගත්තේය\b", "ගත්තා"),
    (r"\bබලයි\b", "බලනවා"),
    (r"\bබැලුවේය\b", "බැලුවා"),
    (r"\bකරයි\b", "කරනවා"),
    (r"\bකළේය\b", "කළා"),
    (r"\bකළහ\b", "කළා"),
    (r"\bගියේය\b", "ගියා"),
    (r"\bගියහ\b", "ගියා"),
    (r"\bහමුවෙමු\b", "හම්බවෙමු"),
    (r"\bහමුවිය\b", "හම්බවුණා"),
    (r"\bහමුවෙයි\b", "හම්බවෙනවා"),

    # Spoken time expressions & common vocabulary
    (r"\bපස්වරු\b", "හවස"),
    (r"\bපෙරවරු\b", "උදේ"),
    (r"\bසූදානම්\b", "ලෑස්ති"),
]

# Verb endings conversion regex rules
VERB_ENDING_RULES: List[Tuple[str, str]] = [
    # 3rd person past: -න්නේය / -න්නීය / -න්නෝය -> -න්නේ
    (r"(\w+)න්නේය\b", r"\1න්නේ"),
    (r"(\w+)න්නීය\b", r"\1න්නේ"),
    
    # 1st person declarative: -න්නෙමි -> -න්නම්
    (r"(\w+)න්නෙමි\b", r"\1න්නම්"),
    
    # Literary past plural: -හ / -වෝය -> -වා / -වුණා
    # Require at least 3 characters before suffix to avoid corrupting short root words
    (r"(\w{3,})ූහ\b", r"\1ුවා"),
    (r"(\w{3,})ාහ\b", r"\1ා"),
    
    # Specific literary 3rd-person plural verbs (ending in -ති)
    (r"\bකරතිද\b", "කරනවාද"),
    (r"\bකරති\b", "කරනවා"),
    (r"\bයතිද\b", "යනවාද"),
    (r"\bයති\b", "යනවා"),
    (r"\bඑතිද\b", "එනවාද"),
    (r"\bඑති\b", "එනවා"),
    (r"\bබලතිද\b", "බලනවාද"),
    (r"\bබලති\b", "බලනවා"),
    (r"\bදනිති\b", "දන්නවා"),
    (r"\bපවසති\b", "කියනවා"),
    
    # Literary suffix -ය at sentence ends
    # Require at least 3 characters before suffix to avoid corrupting short root words
    (r"(\w{3,})වේය\b", r"\1වෙනවා"),
    (r"(\w{3,})දෝය\b", r"\1ද"),
]


def convert_written_to_spoken(text: str) -> str:
    """
    Deterministically transforms literary/written Sinhala grammar and vocabulary
    into natural spoken Sinhala dialogue using Unicode-aware regex matching.
    """
    if not text or not text.strip():
        return text

    result = text

    # Step 1: Specific multi-word phrases
    for pat, repl in WRITTEN_TO_SPOKEN_PHRASES:
        result = re.sub(pat, repl, result)

    # Step 2: Individual vocabulary & pronouns
    for pat, repl in WRITTEN_TO_SPOKEN_WORDS:
        result = re.sub(pat, repl, result)

    # Step 3: Verb endings
    for pat, repl in VERB_ENDING_RULES:
        result = re.sub(pat, repl, result)

    # Clean up double spaces if any occurred
    result = re.sub(r" +", " ", result).strip()
    return result


def detect_written_forms(text: str) -> List[str]:
    """
    Inspects text for remaining literary or written Sinhala forms.
    Returns a list of issue descriptions.
    """
    issues = []
    if not text:
        return issues

    checks = [
        (r"\bඔබ\b", "Written pronoun 'ඔබ' (use 'ඔයා')"),
        (r"\bඔහු\b", "Written pronoun 'ඔහු' (use 'එයා')"),
        (r"\bඇය\b", "Written pronoun 'ඇය' (use 'එයා')"),
        (r"\bඔවුන්\b", "Written pronoun 'ඔවුන්' (use 'ඒගොල්ලෝ')"),
        (r"\bනොවේ\b", "Written negation 'නොවේ' (use 'නෙවෙයි')"),
        (r"\bනැත\b", "Written negation 'නැත' (use 'නෑ')"),
        (r"න්නේය\b", "Written verb ending '-න්නේය' (use '-නවා' or '-න්නේ')"),
        (r"න්නෙමි\b", "Written verb ending '-න්නෙමි' (use '-න්නම්')"),
        (r"\b(?:කරති|යති|එති|බලති|දනිති|පවසති)\b", "Written verb ending '-ති' (use '-නවා')"),
    ]

    for pat, desc in checks:
        if re.search(pat, text):
            issues.append(desc)

    return issues


def score_translation_quality(original_en: str, translated_si: str) -> Tuple[float, List[str]]:
    """
    Evaluates subtitle line quality across:
    1. Written Sinhala artifacts
    2. Length expansion ratio (too short/long)
    3. English/Latin leakage
    4. Repetition or empty output

    Returns:
        (score between 0.0 and 1.0, list_of_diagnostics)
    """
    diagnostics = []
    score = 1.0

    if not translated_si or not translated_si.strip():
        return 0.0, ["Empty translation output"]

    en_stripped = original_en.strip()
    si_stripped = translated_si.strip()

    # 1. Check for written Sinhala forms
    written_issues = detect_written_forms(si_stripped)
    if written_issues:
        score -= min(0.3, 0.1 * len(written_issues))
        diagnostics.extend(written_issues)

    # 2. Length Ratio Check
    en_words = max(1, len(en_stripped.split()))
    si_words = max(1, len(si_stripped.split()))
    ratio = si_words / en_words

    if ratio > 3.0:
        score -= 0.25
        diagnostics.append(f"Output too verbose ({si_words} words for {en_words} English words)")
    elif ratio < 0.25 and en_words > 2:
        score -= 0.25
        diagnostics.append(f"Output truncated ({si_words} words for {en_words} English words)")

    # 3. English/Latin residue in Sinhala output
    sinhala_chars = len(re.findall(r"[\u0D80-\u0DFF]", si_stripped))
    latin_chars = len(re.findall(r"[a-zA-Z]", si_stripped))
    total_letters = sinhala_chars + latin_chars

    if total_letters > 0:
        latin_ratio = latin_chars / total_letters
        if latin_ratio > 0.40:
            score -= 0.4
            diagnostics.append(f"Excessive untranslated English residue ({latin_ratio*100:.1f}%)")

    # 4. Repetition loop check
    words = si_stripped.split()
    if len(words) >= 4:
        repeated_count = 0
        for i in range(len(words) - 1):
            if words[i] == words[i+1]:
                repeated_count += 1
        if repeated_count >= 2:
            score -= 0.3
            diagnostics.append("Repetitive word loop detected")

    score = max(0.0, min(1.0, score))
    return score, diagnostics
