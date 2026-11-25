"""
Background translation thread worker for Anti Gravity.
Executes non-blocking batch translation of queued subtitle files with real-time signals.
"""
from dataclasses import dataclass
from typing import List, Optional, Dict
import os
import time
import logging

from PyQt6.QtCore import QThread, pyqtSignal

from anti_gravity.subtitle_parser import SubtitleFile, SubtitleItem
from anti_gravity.translator_engine import TranslationEngine
from anti_gravity.subtitle_validator import validate_subtitle_file

logger = logging.getLogger("anti_gravity.worker")

# Scene boundary detection thresholds (milliseconds)
SCENE_GAP_THRESHOLD_MS = 2000   # Gap > 2s = likely scene change → prefer batch break
RAPID_FIRE_THRESHOLD_MS = 500   # Gap < 0.5s = rapid dialogue → keep in same batch


def build_scene_aware_batches(
    items: List[SubtitleItem],
    batch_size: int,
) -> List[List[SubtitleItem]]:
    """Split subtitle items into batches, preferring to break at scene boundaries.

    Instead of blindly slicing every `batch_size` items, this looks for timestamp
    gaps > SCENE_GAP_THRESHOLD_MS near the batch-size boundary and breaks there.
    Rapid-fire dialogue (gaps < RAPID_FIRE_THRESHOLD_MS) is kept together when possible.

    Args:
        items: Ordered list of SubtitleItem.
        batch_size: Target number of items per batch.

    Returns:
        List of batches, each a list of SubtitleItem.
    """
    if not items:
        return []
    if batch_size <= 0:
        batch_size = 8

    batches: List[List[SubtitleItem]] = []
    current_batch: List[SubtitleItem] = []

    for i, item in enumerate(items):
        current_batch.append(item)

        # Check if we're in the "break zone" (within ±30% of batch_size)
        at_target = len(current_batch) >= batch_size
        in_break_zone = len(current_batch) >= max(1, int(batch_size * 0.7))

        if at_target or (in_break_zone and i + 1 < len(items)):
            # Look at the gap to the NEXT subtitle
            if i + 1 < len(items):
                gap_ms = items[i + 1].start_ms - item.end_ms
                is_scene_break = gap_ms >= SCENE_GAP_THRESHOLD_MS
                is_rapid_fire = gap_ms < RAPID_FIRE_THRESHOLD_MS

                if at_target:
                    # At target size: break unless in rapid-fire dialogue
                    # (allow up to 30% overshoot to keep rapid-fire together)
                    if is_rapid_fire and len(current_batch) < int(batch_size * 1.3):
                        continue  # Keep going to avoid splitting mid-dialogue
                    batches.append(current_batch)
                    current_batch = []
                elif in_break_zone and is_scene_break:
                    # In break zone with a scene gap: break early
                    batches.append(current_batch)
                    current_batch = []
            else:
                # Last item — flush
                batches.append(current_batch)
                current_batch = []

    # Flush remaining
    if current_batch:
        batches.append(current_batch)

    return batches


@dataclass
class QueueItem:
    file_path: str
    output_path: str
    file_name: str
    total_lines: int
    status: str = "Queued"  # Queued, Processing, Completed, Failed, Aborted
    completed_lines: int = 0
    error_message: str = ""


class TranslationWorker(QThread):
    # Signals for thread-safe UI updates
    model_loading_progress = pyqtSignal(str, int)  # status_message, percent
    file_status_changed = pyqtSignal(int, str)     # file_index, status_text
    file_progress = pyqtSignal(int, int, int)       # file_index, completed_lines, total_lines
    queue_progress = pyqtSignal(int, int, float)    # completed_total, total_lines, percent
    line_translated = pyqtSignal(str, int, str, str)# file_name, line_index, original, translated
    file_finished = pyqtSignal(int, str, str)       # file_index, status, output_path
    queue_finished = pyqtSignal(bool, str)          # success, summary_message
    log_message = pyqtSignal(str)                  # console log

    def __init__(
        self,
        queue_items: List[QueueItem],
        engine: TranslationEngine,
        batch_size: int = 8,
        parent=None
    ):
        super().__init__(parent)
        self.queue_items = queue_items
        self.engine = engine
        self.batch_size = batch_size

        self._abort_current_file = False
        self._abort_queue = False
        self._is_running = True

    def abort_current(self):
        """Request immediate abort of the file currently being processed."""
        self._abort_current_file = True
        self.log_message.emit("⚠ Abort requested for current file.")

    def abort_all(self):
        """Request immediate abort of the entire translation queue."""
        self._abort_queue = True
        self._abort_current_file = True
        self.log_message.emit("🛑 Abort requested for entire queue.")

    def run(self):
        self.log_message.emit("🚀 Starting translation worker...")

        # Step 1: Ensure AI engine is loaded
        if not self.engine.is_loaded:
            self.log_message.emit(f"Loading AI Model: {self.engine.model_id}...")
            try:
                def on_load_progress(msg, pct):
                    self.model_loading_progress.emit(msg, pct)
                    self.log_message.emit(f"[{pct}%] {msg}")

                self.engine.load_model(progress_callback=on_load_progress)
                self.log_message.emit("✓ AI Model loaded successfully into GPU VRAM.")
            except Exception as e:
                err_str = f"Failed to load AI model: {str(e)}"
                logger.exception(err_str)
                self.log_message.emit(f"❌ {err_str}")
                self.queue_finished.emit(False, err_str)
                return

        # Calculate total lines across entire queue
        total_queue_lines = sum(item.total_lines for item in self.queue_items)
        cumulative_completed_lines = 0

        for file_idx, item in enumerate(self.queue_items):
            if self._abort_queue:
                item.status = "Aborted"
                self.file_status_changed.emit(file_idx, "Aborted")
                continue

            if item.status == "Completed":
                cumulative_completed_lines += item.total_lines
                continue

            self._abort_current_file = False
            item.status = "Processing"
            self.file_status_changed.emit(file_idx, "Processing")
            self.log_message.emit(f"▶ Translating [{file_idx+1}/{len(self.queue_items)}]: {item.file_name}")

            try:
                sub_file = SubtitleFile(item.file_path)
                total_file_lines = sub_file.total_lines
                item.total_lines = total_file_lines

                if total_file_lines == 0:
                    item.status = "Completed"
                    self.file_status_changed.emit(file_idx, "Completed")
                    self.file_finished.emit(file_idx, "Completed", item.output_path)
                    continue

                # Rolling context window for inter-subtitle coherence
                rolling_context = []
                translation_failures = 0

                # Scene-aware batch processing
                batches = build_scene_aware_batches(sub_file.items, self.batch_size)
                processed_lines = 0

                for batch_items in batches:
                    if self._abort_queue or self._abort_current_file:
                        break

                    batch_texts = [b.original_text for b in batch_items]

                    # Vectorized GPU inference with context
                    try:
                        translated_batch, rolling_context = self.engine.translate_batch(
                            batch_texts,
                            context_lines=rolling_context,
                        )
                    except Exception as batch_err:
                        batch_num = processed_lines // self.batch_size
                        logger.warning(f"Batch {batch_num} failed: {batch_err}, marking lines as failed")
                        translated_batch = [f"⚠️ {t}" for t in batch_texts]
                        translation_failures += len(batch_texts)

                    # Update items and emit preview for each
                    for b_sub, trans_text in zip(batch_items, translated_batch):
                        b_sub.translated_text = trans_text
                        if trans_text.startswith("⚠️"):
                            translation_failures += 1
                        self.line_translated.emit(
                            item.file_name,
                            b_sub.index,
                            b_sub.original_text,
                            trans_text
                        )

                    processed_lines += len(batch_items)
                    done_in_file = min(processed_lines, total_file_lines)
                    item.completed_lines = done_in_file
                    self.file_progress.emit(file_idx, done_in_file, total_file_lines)

                    overall_done = cumulative_completed_lines + done_in_file
                    overall_pct = (overall_done / total_queue_lines * 100.0) if total_queue_lines > 0 else 0.0
                    self.queue_progress.emit(overall_done, total_queue_lines, overall_pct)

                if self._abort_queue or self._abort_current_file:
                    item.status = "Aborted"
                    self.file_status_changed.emit(file_idx, "Aborted")
                    self.file_finished.emit(file_idx, "Aborted", "")
                    self.log_message.emit(f"⏹ File aborted: {item.file_name}")
                else:
                    # Run subtitle validation and auto-fix before saving
                    warnings_count, fixes_count, val_summary = validate_subtitle_file(sub_file.items)
                    for msg in val_summary:
                        self.log_message.emit(f"  {msg}")

                    # Save clean translated output
                    sub_file.save_translated(item.output_path)
                    item.status = "Completed"
                    cumulative_completed_lines += total_file_lines
                    self.file_status_changed.emit(file_idx, "Completed")
                    self.file_finished.emit(file_idx, "Completed", item.output_path)
                    if translation_failures > 0:
                        self.log_message.emit(
                            f"⚠ Completed: {item.file_name} -> Saved to {item.output_path} "
                            f"({translation_failures} of {total_file_lines} lines failed to translate)"
                        )
                    else:
                        self.log_message.emit(f"✓ Completed: {item.file_name} -> Saved to {item.output_path}")

            except Exception as e:
                err_msg = str(e)
                logger.exception(f"Error processing {item.file_name}: {err_msg}")
                item.status = "Failed"
                item.error_message = err_msg
                self.file_status_changed.emit(file_idx, "Failed")
                self.file_finished.emit(file_idx, "Failed", "")
                self.log_message.emit(f"❌ Error on {item.file_name}: {err_msg}")

        all_completed = all(i.status == "Completed" for i in self.queue_items)
        summary = "All files translated successfully!" if all_completed else "Queue processing finished."
        self.queue_finished.emit(all_completed, summary)
        self.log_message.emit(f"🏁 {summary}")

