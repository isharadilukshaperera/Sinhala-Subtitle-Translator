"""
Subtitle parsing and writing module for Anti Gravity.
Provides robust handling of .srt files with automatic encoding detection,
timestamp preservation, and clean Sinhala output.
"""
from dataclasses import dataclass
from typing import List, Optional
import logging
import os
import re
import chardet
import pysrt

logger = logging.getLogger("anti_gravity.subtitle_parser")

# Regex to strip SRT positioning tags like {\\an8} or {\pos(320,50)}
_POSITIONING_TAG_RE = re.compile(r"\{\\[^}]*\}")


@dataclass
class SubtitleItem:
    index: int
    start_time: str
    end_time: str
    original_text: str
    translated_text: str = ""
    start_ms: int = 0
    end_ms: int = 0

def detect_file_encoding(file_path: str) -> str:
    """Detect encoding of an SRT file with multiple fallbacks."""
    try:
        with open(file_path, "rb") as f:
            raw = f.read(65536)
        if not raw:
            return "utf-8"
        # Check BOM
        if raw.startswith(b'\xef\xbb\xbf'):
            return "utf-8-sig"
        detection = chardet.detect(raw)
        encoding = detection.get("encoding")
        if encoding:
            return encoding
    except Exception:
        pass
    return "utf-8"


def _preprocess_srt_file(file_path: str, encoding: str) -> str:
    """Read an SRT file and normalize its content for robust parsing.

    Handles:
    - BOM stripping (utf-8-sig encoding covers this via Python codec)
    - Mixed line endings (\\r\\n, \\r, \\n) → \\n
    - Dot-decimal timestamps (00:01:02.500 → 00:01:02,500)
    - Positioning / styling tags ({\\an8}, {\\pos(x,y)}) removed from text
    Returns the path to a cleaned temp file suitable for pysrt.open().
    """
    try:
        with open(file_path, "r", encoding=encoding, errors="replace") as f:
            content = f.read()
    except Exception:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

    # Normalize line endings
    content = content.replace("\r\n", "\n").replace("\r", "\n")

    # Fix dot-decimal timestamps: 00:01:02.500 --> 00:01:03.000
    # Only replace dots in timestamp lines (HH:MM:SS.mmm --> HH:MM:SS.mmm)
    def _fix_timestamp_dots(match: re.Match) -> str:
        return match.group(0).replace(".", ",")

    content = re.sub(
        r"\d{2}:\d{2}:\d{2}[.,]\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}[.,]\d{3}",
        _fix_timestamp_dots,
        content,
    )

    # Strip positioning tags from text lines
    content = _POSITIONING_TAG_RE.sub("", content)

    # Write to a temp file for pysrt
    import tempfile
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".srt")
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8", newline="\n") as tmp_f:
            tmp_f.write(content)
    except Exception:
        os.close(tmp_fd)
        raise
    return tmp_path


class SubtitleFile:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.file_name = os.path.basename(file_path)
        self.encoding = detect_file_encoding(file_path)
        self.items: List[SubtitleItem] = []
        self._raw_subs: Optional[pysrt.SubRipFile] = None
        self._load()

    def _load(self):
        """Load SRT file into items list."""
        # Preprocess the file for edge-case normalization
        tmp_path: Optional[str] = None
        try:
            tmp_path = _preprocess_srt_file(self.file_path, self.encoding)
            self._raw_subs = pysrt.open(tmp_path, encoding="utf-8")
            logger.debug(
                "Loaded %s via preprocessed temp file (encoding=%s)",
                self.file_name, self.encoding,
            )
        except Exception as first_err:
            logger.warning(
                "Preprocessed load failed for %s: %s — falling back to direct pysrt",
                self.file_name, first_err,
            )
            # Direct fallback chain (original behaviour)
            try:
                self._raw_subs = pysrt.open(self.file_path, encoding=self.encoding)
            except Exception:
                try:
                    self._raw_subs = pysrt.open(self.file_path, encoding="utf-8", error_handling="replace")
                    self.encoding = "utf-8"
                    logger.info("Fallback to utf-8 succeeded for %s", self.file_name)
                except Exception:
                    self._raw_subs = pysrt.open(self.file_path, encoding="latin-1", error_handling="replace")
                    self.encoding = "latin-1"
                    logger.info("Fallback to latin-1 for %s", self.file_name)
        finally:
            # Clean up temp file
            if tmp_path:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

        # Warn on empty file
        if not self._raw_subs or len(self._raw_subs) == 0:
            logger.warning("SRT file is empty or could not be parsed: %s", self.file_name)

        # Build items list with overlap detection
        self.items = []
        prev_end_ms: int = 0
        for i, sub in enumerate(self._raw_subs):
            # Clean text preserving intra-sentence newlines
            text = sub.text.strip()
            item = SubtitleItem(
                index=sub.index if sub.index is not None else (i + 1),
                start_time=str(sub.start),
                end_time=str(sub.end),
                original_text=text,
                start_ms=sub.start.ordinal,
                end_ms=sub.end.ordinal,
            )
            # Detect overlapping timestamps
            if i > 0 and item.start_ms < prev_end_ms:
                overlap_ms = prev_end_ms - item.start_ms
                logger.warning(
                    "Overlapping timestamps in %s: entry %d starts %dms before entry %d ends",
                    self.file_name, i + 1, overlap_ms, i,
                )
            prev_end_ms = item.end_ms
            self.items.append(item)

    @property
    def total_lines(self) -> int:
        return len(self.items)

    def save_translated(self, output_path: str) -> str:
        """Save translated subtitles to the target path with UTF-8 encoding.

        Always re-numbers subtitle indices sequentially (1, 2, 3, …) to
        produce a clean, standards-compliant SRT file.
        """
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        # Build clean SubRipFile — always re-number indices
        if self._raw_subs is not None and len(self._raw_subs) == len(self.items):
            for seq, (raw_sub, item) in enumerate(zip(self._raw_subs, self.items), 1):
                final_text = item.translated_text.strip() if item.translated_text else item.original_text
                raw_sub.text = final_text
                raw_sub.index = seq  # Re-number sequentially
            self._raw_subs.save(output_path, encoding="utf-8")
        else:
            # Manual fallback writer (already re-numbers via enumerate)
            with open(output_path, "w", encoding="utf-8", newline="\n") as f:
                for idx, item in enumerate(self.items, 1):
                    final_text = item.translated_text.strip() if item.translated_text else item.original_text
                    f.write(f"{idx}\n")
                    f.write(f"{item.start_time.replace('.', ',')} --> {item.end_time.replace('.', ',')}\n")
                    f.write(f"{final_text}\n\n")

        logger.info("Saved translated SRT: %s (%d entries)", output_path, len(self.items))
        return output_path

