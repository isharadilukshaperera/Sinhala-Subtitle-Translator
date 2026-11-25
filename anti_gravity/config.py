"""
Configuration settings and constants for Translator Desktop Subtitle Application.
"""
from typing import Dict
import json
import os

APP_NAME = "Translator"
APP_SUBTITLE = "Desktop English-to-Sinhala Subtitle AI"
APP_VERSION = "1.0.0"

# Color Palette & Styling Constants (Obsidian & Neon Amber Aesthetic)
COLOR_BG_DARK = "#0E1015"           # Deep obsidian slate
COLOR_CARD_BG = "#161922"           # Floating rounded card background
COLOR_CARD_BORDER = "#262B36"       # Subtle border stroke
COLOR_CARD_HOVER = "#1E222E"        # Hover background for cards and rows
COLOR_ACCENT = "#FF6B00"            # Vibrant neon amber / orange
COLOR_ACCENT_HOVER = "#FF8533"      # Neon amber hover
COLOR_ACCENT_GLOW = "rgba(255, 107, 0, 0.35)"
COLOR_TEXT_PRIMARY = "#FFFFFF"      # Crisp white for titles and headings
COLOR_TEXT_SECONDARY = "#94A3B8"    # Muted cool grey for secondary labels
COLOR_TEXT_MUTED = "#64748B"        # Dimmer metadata text
COLOR_SUCCESS = "#10B981"           # Emerald green for completed state
COLOR_DANGER = "#EF4444"            # Rose red for failed / abort
COLOR_WARNING = "#F59E0B"           # Warm amber for warnings
COLOR_INFO = "#38BDF8"              # Sky blue for info

# Default AI Model Settings
DEFAULT_MODEL_ID = "SAWithanage/SinLlama-Llama-3-8B-Merged"

SUPPORTED_MODELS: Dict[str, Dict[str, any]] = {
    "SAWithanage/SinLlama-Llama-3-8B-Merged": {
        "name": "SinLlama 8B (Default)",
        "desc": "High capacity Sinhala Llama-3 finetune, 4-bit NF4 (VRAM ~6.0GB)",
        "type": "causal_lm",
        "supports_cpu": False,
        "cpu_reason": "SinLlama 8B uses 4-bit NF4 quantization which requires an NVIDIA CUDA GPU to fit in memory.",
        "default": True
    },
    "Jainamshahhh/helalm-4b": {
        "name": "HelaLM 4B",
        "desc": "Ultra-fast native Sri Lankan Sinhala, 4-bit NF4 quantized (VRAM ~3.5GB)",
        "type": "causal_lm",
        "supports_cpu": False,
        "cpu_reason": "HelaLM 4B is optimized in 4-bit NF4 quantization which strictly requires an NVIDIA CUDA GPU.",
        "default": False
    },
    "facebook/nllb-200-distilled-600M": {
        "name": "NLLB-200 Distilled 600M",
        "desc": "Meta NLLB seq2seq model, fast CPU & GPU capable (RAM ~2.0GB)",
        "type": "seq2seq",
        "supports_cpu": True,
        "cpu_reason": "",
        "default": False
    }
}

DEFAULT_BATCH_SIZE = 8
DEFAULT_MAX_NEW_TOKENS = 196
DEFAULT_TEMPERATURE = 0.2
DEFAULT_OUTPUT_SUFFIX = "_sinhala_clean.srt"

SYSTEM_INSTRUCTION = (
    "You are a native Sri Lankan Sinhala translator, language editor, and expert movie subtitle translator.\n\n"
    "Your task is to translate text and English movie dialogue between English and 100% natural, colloquial Sri Lankan Sinhala (කතා කරන සිංහල / කථා ව්‍යවහාරය) that a native Sri Lankan would genuinely use in everyday life.\n\n"
    "TRANSLATION REQUIREMENTS:\n"
    "1. Preserve the original meaning, intent, tone, emotion, and level of formality accurately.\n"
    "2. Use everyday spoken Sinhala. STRICTLY AVOID formal written or literary Sinhala (ලිඛිත සිංහල).\n"
    "3. Avoid literal, word-for-word translations. Use natural Sri Lankan expressions and adapt slang and idioms to local usage.\n"
    "4. Keep sentences short, punchy, and subtitle-friendly.\n"
    "5. For casual dialogues, use natural conversational Sinhala. For workplace or formal dialogue, use clear, professional but natural Sinhala.\n"
    "6. Keep commonly used technical terms, brand names, and loan words in English when that sounds more natural to Sri Lankan speakers.\n"
    "7. Preserve character names and original subtitle line structure. If the input has multiple lines (separated by \\n), output the same number of lines in Sinhala.\n"
    "8. If the input contains Romanized Sinhala (Singlish), understand its intended meaning before translating it.\n"
    "9. Do not add explanations, notes, pronunciation guides, breakdowns, or ideas absent from the original.\n"
    "10. Output ONLY the final direct spoken Sinhala translation.\n\n"
    "STRICT SPOKEN GRAMMAR RULES:\n"
    "- NEVER use literary verb endings: -න්නේය, -න්නෙමි, -ති, -මු, -ය, -වේ, -නොවේ, -නැත.\n"
    "- ALWAYS use spoken verb forms ending in: -නවා, -න්න, -න්නම්, -නවාද, -වා, -යි, -නෑ, -එපා (e.g. යනවා, කරනවා, එනවා, කරන්නම්, ආවා, බය වෙන්න එපා, තියෙනවා, නෑ).\n"
    "- ALWAYS use conversational pronouns: 'ඔයා' (never 'ඔබ'), 'එයා' (never 'ඔහු' or 'ඇය'), 'ඒගොල්ලෝ' (never 'ඔවුන්').\n"
    "- Use natural spoken time expressions: ALWAYS use 'හවස' for PM / afternoon (never formal 'පස්වරු'), 'උදේ' for AM / morning (never formal 'පෙරවරු').\n"
    "- Use natural everyday spoken phrasings for greetings: e.g. 'කොහොමද ඔයාට?' (never formal 'කොහොමද ඉන්නේ?' or 'කෙසේද?').\n"
    "- Use everyday spoken place names: 'ස්ටේෂන් එක' (never formal 'දුම්රිය ස්ථානය' or 'දුම්රිය පොළ')."
)

# Load few-shot examples from JSON file, with fallback to defaults
_FEW_SHOTS_PATH = os.path.join(os.path.dirname(__file__), "data", "few_shots.json")
try:
    with open(_FEW_SHOTS_PATH, "r", encoding="utf-8") as _f:
        _few_shots_data = json.load(_f)
    SPOKEN_FEW_SHOTS = [(item["en"], item["si"]) for item in _few_shots_data]
except Exception:
    SPOKEN_FEW_SHOTS = [
        ("Catch me.", "මාව අල්ලගන්න."),
        ("All said and done, daughters will always be daughters.", "කොහොම වුනත්, දුවෙක් කියන්නේ දුවෙක්ම තමයි."),
        ("Good morning! How are you doing today?", "සුබ උදෑසනක්! අද කොහොමද ඔයාට?"),
        ("Let's meet at the train station at 5 PM.", "හවස පහට අපි හම්බවෙමු."),
    ]
