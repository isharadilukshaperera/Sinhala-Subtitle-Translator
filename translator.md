# Project Specification: "Anti Gravity" - Standalone Desktop English-to-Sinhala Subtitle Translator

Build a professional, lightweight, standalone Windows desktop application (`.exe`) named **Anti Gravity** that translates English `.srt` subtitle files into natural, professional-grade Sri Lankan Sinhala using local AI models running on an NVIDIA GPU (optimized for RTX 3060).

## 1. Core Architecture & Tech Stack
- **Language & Framework:** Python 3.10+ using **PyQt6** (or PySide6) for a high-performance, responsive desktop UI with multi-threading (`QThread`) to keep the interface completely smooth during GPU inference.
- **AI Engine:** PyTorch (CUDA enabled), Hugging Face `transformers`, `bitsandbytes` (4-bit NF4 quantization), and `accelerate`.
- **Packaging:** Bundled into a standalone Windows executable (`.exe`) using **PyInstaller**.
- **System Monitoring:** `psutil` for CPU/RAM metrics and `torch.cuda` / `pynvml` for real-time GPU VRAM and utilization tracking.

---

## 2. UI & UX Design (Inspired by the Reference Dashboard Aesthetic)
*Note: Adapt the aesthetic look and feel (colors, cards, glowing accents, typography) into a clean desktop software layout—do NOT copy a car dashboard layout.*

- **Color Palette & Styling:** 
  - **Background:** Deep obsidian slate (`#0E1015`).
  - **Containers/Cards:** Floating rounded rectangular cards (`#161922` background with subtle 1px border stroke and `16px` border-radius) to organize features cleanly.
  - **Accents:** Vibrant neon amber/orange (`#FF6B00`) for primary action buttons, active queue states, progress fills, and glowing status indicators.
- **Typography:** Modern clean sans-serif (Segoe UI / Inter); crisp white (`#FFFFFF`) for primary titles/headers, and muted cool grey (`#94A3B8`) for secondary labels and metadata.
- **Layout Structure:**
  - **Header Bar:** Sleek application title ("Anti Gravity 🎬"), active GPU hardware badge, and advanced settings drawer toggle.
  - **Main Dashboard Grid:** Split-pane modular layout using the styled rounded cards:
    - *Left Card:* Drag-and-drop file zone & File Queue table (with status, progress, move up/down, and remove actions).
    - *Right Top Card:* CPU & GPU VRAM real-time utilization monitor with sleek progress gauges.
    - *Right Bottom Card:* Live Translation Preview Console streaming incoming English lines alongside their live Sinhala translations dialog-by-dialog.
  - **Bottom Control Bar:** Output folder path selector, AI model selector dropdown, and master "Start Queue" / "Abort" controls.

---

## 3. Mandatory Functional Features

### Feature 1 & 3 & 4: File Handling & Drag-and-Drop
- Support browsing or drag-and-drop for `.srt` files directly into the UI queue container.
- Support uploading multiple `.srt` files simultaneously.

### Feature 5 & 6: Queue Management
- Display all queued files in a clean styled table showing: File Name, Total Lines, Current Progress (`Completed / Total`), and Status (`Queued`, `Processing`, `Completed`, `Failed`, `Aborted`).
- Provide action buttons for each row: **Move Up**, **Move Down**, and **Remove from Queue**.

### Feature 7 & 8: Progress & Abort Controls
- Live progress updates per file and overall queue progress bar highlighted in neon amber.
- Dedicated buttons: **"Abort Current File"** and **"Abort Entire Queue"** (instantly halts background threads and resets states safely).

### Feature 9: Output Folder Configuration
- A clean file path selector widget to choose a custom output directory (defaults to input path with a `_sinhala_clean.srt` suffix).

### Feature 10: CPU & GPU Resource Widget
- Real-time polled meters displaying CPU Usage (%) and GPU VRAM Allocation / Utilization (%) customized for NVIDIA RTX 3060.

### Feature 11: Real-Time Translation Preview Widget
- A dedicated live-scrolling dark console showing the live translation stream dialog-by-dialog as the GPU processes batches.

### Feature 12: Advanced Settings Widget
- An expandable panel or modal allowing users to switch AI models:
  - **Default:** `Jainamshahhh/helalm-4b` (4-bit quantized)
  - **Alternative 1:** `SinLlama 8B`
  - **Alternative 2:** `facebook/nllb-200-distilled-600M`

### Feature 13: Automated Dependency Checker & Non-Technical Installer Wizard
- When clicking **"Start Translation"**, pre-flight checks validate Python packages (`torch`, `transformers`, `bitsandbytes`, `accelerate`, `psutil`) and CUDA availability.
- If dependencies or model weights are missing, show a friendly setup wizard with an **"Auto-Install & Download"** button that runs background pip installs and model caching with a visual progress bar.

### Feature 14 & 16: Core AI Translation Pipeline (Strict Compliance)
Implement the exact production-ready pipeline developed for HelaLM-4B:
- **Optimization:** Loaded in 4-bit NF4 with `attn_implementation="sdpa"` and compiled via `torch.compile(model, mode="reduce-overhead")` for maximum RTX 3060 throughput.
- **Batch Processing:** Vectorized batching (`BATCH_SIZE = 8`) with left-padding enabled (`tokenizer.padding_side = "left"`) to process multiple subtitle lines concurrently.
- **Strict System Prompt & Anti-Explanation Filter:** 
  Embed the exact 10-point native Sri Lankan translation guidelines as the system prompt:
  ```python
  system_instruction = (
      "You are a native Sri Lankan Sinhala translator and language editor.\n"
      "Your task is to translate text between English and Sinhala.\n\n"
      "Translation requirements:\n"
      "1. Preserve the original meaning and intent accurately.\n"
      "2. Use natural, fluent Sinhala that a native Sri Lankan would genuinely use in everyday life.\n"
      "3. Avoid literal, word-for-word translations.\n"
      "4. Preserve the original tone, emotion, and level of formality.\n"
      "5. For casual messages, use natural conversational Sinhala.\n"
      "6. For workplace messages, use clear, professional but natural Sinhala.\n"
      "7. Keep commonly used technical terms in English when that sounds more natural to Sri Lankan speakers.\n"
      "8. Do not add explanations, information, linguistic notes, breakdowns, or commentary.\n"
      "9. If the input is Romanized Sinhala, understand its intended meaning before translating it.\n"
      "10. Return ONLY the raw final translated Sinhala subtitle text. Multi-sentence dialogues are allowed if the original has multiple sentences."
  )