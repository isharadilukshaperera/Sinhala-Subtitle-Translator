"""
Subtitle output validator for Anti Gravity Translator.
Validates translated subtitle entries for SRT compliance, readability,
and common translation quality issues.
"""
import re
import logging
from typing import List, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger("anti_gravity.validator")

# SRT subtitle best-practice limits
MAX_LINE_LENGTH = 42        # Characters per line
MAX_LINES_PER_ENTRY = 2     # Lines per subtitle entry
MIN_CPS = 10                # Minimum characters per second (too slow = wasted screen time)
MAX_CPS = 25                # Maximum characters per second (too fast = unreadable)


@dataclass
class ValidationResult:
    """Result of validating a single subtitle entry."""
    is_valid: bool = True
    warnings: List[str] = field(default_factory=list)
    auto_fixed: bool = False
    fixed_text: str = ""


def validate_subtitle_entry(
    text: str,
    original_en: str = "",
    duration_ms: int = 0,
) -> ValidationResult:
    """
    Validate a single translated subtitle entry for SRT compliance and quality.
    
    Args:
        text: The translated Sinhala subtitle text.
        original_en: The original English text (for ratio checks).
        duration_ms: Duration of this subtitle in milliseconds (for CPS check).
        
    Returns:
        ValidationResult with warnings and optional auto-fixed text.
    """
    result = ValidationResult()
    if not text or not text.strip():
        result.is_valid = False
        result.warnings.append("Empty translation")
        return result

    working_text = text.strip()

    # 1. Check for translation failure markers
    if working_text.startswith("⚠️"):
        result.is_valid = False
        result.warnings.append("Translation failed — line contains error marker")
        return result

    # 2. Repetition detection: same word/phrase repeated 3+ times
    words = working_text.split()
    if len(words) >= 4:
        for i in range(len(words) - 2):
            if words[i] == words[i + 1] == words[i + 2]:
                # Strip the repetitions
                deduped = []
                prev = None
                repeat_count = 0
                for w in words:
                    if w == prev:
                        repeat_count += 1
                        if repeat_count < 2:
                            deduped.append(w)
                    else:
                        deduped.append(w)
                        repeat_count = 0
                    prev = w
                working_text = " ".join(deduped)
                result.warnings.append("Repetitive word loop detected and cleaned")
                result.auto_fixed = True
                break

    # 3. Length ratio check (Sinhala vs English)
    if original_en:
        en_len = max(1, len(original_en.strip()))
        si_len = len(working_text)
        ratio = si_len / en_len
        if ratio > 3.5:
            result.warnings.append(f"Translation unusually long ({ratio:.1f}x original)")
        elif ratio < 0.2 and en_len > 10:
            result.warnings.append(f"Translation unusually short ({ratio:.1f}x original)")

    # 4. Characters per second (reading speed) check
    if duration_ms > 0:
        duration_sec = duration_ms / 1000.0
        char_count = len(working_text.replace(" ", "").replace("\n", ""))
        if duration_sec > 0:
            cps = char_count / duration_sec
            if cps > MAX_CPS:
                result.warnings.append(
                    f"Reading speed too fast ({cps:.1f} CPS, max {MAX_CPS})"
                )
            elif cps < MIN_CPS and char_count > 5:
                result.warnings.append(
                    f"Reading speed very slow ({cps:.1f} CPS, min {MIN_CPS})"
                )

    # 5. Line length enforcement and auto-wrap
    lines = working_text.split("\n")
    needs_rewrap = False
    
    # Check if any line exceeds max length
    for line in lines:
        if len(line) > MAX_LINE_LENGTH:
            needs_rewrap = True
            break
    
    # Also check if there are too many lines
    if len(lines) > MAX_LINES_PER_ENTRY:
        needs_rewrap = True

    if needs_rewrap:
        # Join all lines and re-wrap
        flat = " ".join(line.strip() for line in lines)
        if len(flat) <= MAX_LINE_LENGTH:
            working_text = flat
        elif len(flat) <= MAX_LINE_LENGTH * 2:
            # Split into 2 roughly equal lines at a word boundary
            mid = len(flat) // 2
            # Find the nearest space to the midpoint
            best_split = mid
            for offset in range(0, min(mid, 15)):
                if mid + offset < len(flat) and flat[mid + offset] == " ":
                    best_split = mid + offset
                    break
                if mid - offset >= 0 and flat[mid - offset] == " ":
                    best_split = mid - offset
                    break
            working_text = flat[:best_split].strip() + "\n" + flat[best_split:].strip()
        else:
            # Text is very long — truncate to 2 lines of max length
            result.warnings.append(
                f"Text too long ({len(flat)} chars) — wrapped to 2 lines"
            )
            # Find a word boundary near MAX_LINE_LENGTH
            if len(flat) > MAX_LINE_LENGTH:
                split_pos = flat.rfind(" ", 0, MAX_LINE_LENGTH)
                if split_pos == -1:
                    split_pos = MAX_LINE_LENGTH
                line1 = flat[:split_pos].strip()
                remaining = flat[split_pos:].strip()
                if len(remaining) > MAX_LINE_LENGTH:
                    remaining = remaining[:MAX_LINE_LENGTH - 1] + "…"
                working_text = line1 + "\n" + remaining
            
        result.auto_fixed = True

    # 6. Preserve SRT formatting tags from original
    if original_en:
        # Check if original had <i>, <b>, <u> tags
        tag_match = re.match(r'^(<[ibu]>)', original_en)
        tag_end = re.search(r'(</[ibu]>)$', original_en)
        if tag_match and tag_end:
            open_tag = tag_match.group(1)
            close_tag = tag_end.group(1)
            if open_tag not in working_text:
                working_text = open_tag + working_text + close_tag
                result.auto_fixed = True

    if result.auto_fixed:
        result.fixed_text = working_text

    return result


def validate_subtitle_file(items: list) -> Tuple[int, int, List[str]]:
    """
    Validate all subtitle items in a file.
    
    Args:
        items: List of SubtitleItem objects.
        
    Returns:
        Tuple of (total_warnings, auto_fixes_applied, summary_messages).
    """
    total_warnings = 0
    total_fixes = 0
    summary = []

    for item in items:
        if not item.translated_text:
            continue
            
        duration_ms = item.end_ms - item.start_ms if hasattr(item, 'end_ms') and hasattr(item, 'start_ms') else 0
        
        result = validate_subtitle_entry(
            text=item.translated_text,
            original_en=item.original_text,
            duration_ms=duration_ms,
        )

        if result.warnings:
            total_warnings += len(result.warnings)
            for w in result.warnings:
                logger.debug(f"Line {item.index}: {w}")

        if result.auto_fixed and result.fixed_text:
            item.translated_text = result.fixed_text
            total_fixes += 1

    if total_warnings > 0:
        summary.append(f"⚠ {total_warnings} quality warnings across {len(items)} lines")
    if total_fixes > 0:
        summary.append(f"🔧 Auto-fixed {total_fixes} lines (line wrapping, repetition removal)")
    if total_warnings == 0 and total_fixes == 0:
        summary.append(f"✓ All {len(items)} lines pass validation")

    return total_warnings, total_fixes, summary
