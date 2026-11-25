# Anti Gravity — Sinhala Subtitle Translator 🎬
### Standalone Desktop English-to-Sinhala Subtitle AI

**Anti Gravity** is a lightweight, professional standalone Windows desktop application designed to translate English `.srt` subtitle files into natural, professional-grade Sri Lankan **Spoken Sinhala** using local AI models running on an NVIDIA GPU or CPU.

---

## 📋 Table of Contents
1. [Core Architecture & Tech Stack](#1-core-architecture--tech-stack)
2. [UI & UX Aesthetic Specifications](#2-ui--ux-aesthetic-specifications)
3. [Strict AI Translation Guidelines & System Prompt](#3-strict-ai-translation-guidelines--system-prompt)
4. [Functional Features](#4-functional-features)
5. [Compute Device Selection & CPU Incompatibility Handling](#5-compute-device-selection--cpu-incompatibility-handling)
6. [Project Structure](#6-project-structure)
7. [Execution & Usage Instructions](#7-execution--usage-instructions)
8. [Packaging into Standalone Windows Executable (.exe)](#8-packaging-into-standalone-windows-executable-exe)
9. [Troubleshooting & Dependency Management](#9-troubleshooting--dependency-management)
10. [Quality Assurance & Roadmap](#10-quality-assurance--roadmap)

---

## 1. Core Architecture & Tech Stack
- **Language & GUI Framework:** Python 3.10+ using **PyQt6** with a modern frameless window layout and multi-threaded architecture (`QThread`) to ensure the user interface stays 100% fluid and responsive during GPU and CPU inference.
- **AI Engine:**
  - **PyTorch** with native CUDA acceleration.
  - Hugging Face **`transformers`**.
  - **`bitsandbytes`** for 4-bit NF4 quantization (`BitsAndBytesConfig`).
  - **`accelerate`** for automated device placement and offloading.
  - SDPA (`Scaled Dot-Product Attention`) attention optimization for RTX-series GPUs.
- **Hardware Telemetry:**
  - Real-time polling via `pynvml` (NVIDIA Management Library) and `torch.cuda` for GPU VRAM allocation, GPU core utilization, and GPU temperature.
  - `psutil` for CPU load and system RAM metrics.
  - **Dynamic GPU detection** — automatically detects your GPU model (no hardcoded GPU name).
- **Subtitle Parsing Engine:**
  - Multi-encoding detection (UTF-8, UTF-8-BOM, CP1252, Latin-1) via `chardet` and `pysrt`.
  - Precise timestamp preservation and subtitle sequence formatting.
  - Edge-case handling: BOM stripping, dot-decimal timestamps, mixed line endings, positioning tags, overlapping timestamp warnings.
- **Translation Quality Pipeline:**
  - Context-aware sliding window (maintains dialogue coherence across subtitles).
  - Glossary-injected prompts (200+ English-to-Spoken-Sinhala terms).
  - 14 categorized few-shot examples loaded from `data/few_shots.json`.
  - Post-translation subtitle validation (CPS, line length, repetition, length ratio, tag preservation).
  - Written-to-spoken Sinhala converter with protected word lists.
  - Quality scoring with automatic failure marking.

---

## 2. UI & UX Aesthetic Specifications
Inspired by a modern, high-contrast dark dashboard aesthetic:
- **Frameless Window:**
  - Sleek borderless window frame with custom **Minimize (—)**, **Maximize/Restore (□ / ❐)**, and **Close (✕)** window controls in the top-right corner.
  - Fully draggable header bar (drag to move, double-click to maximize/restore).
- **Color Palette:**
  - **Background:** Deep obsidian slate (`#0E1015`).
  - **Cards & Containers:** Floating rounded cards (`#161922` background, 1px `#262B36` border stroke, `16px` border-radius).
  - **Accents:** Vibrant neon amber/orange (`#FF6B00` / `#FF8533`) for primary CTA buttons, active queue states, progress fills, and glowing badges.
  - **Typography:** Crisp white (`#FFFFFF`) for primary titles and headers, muted cool grey (`#94A3B8`) for secondary labels and metadata.
- **Live Preview Console:**
  - Real-time streaming of EN → SI translation pairs with quality badges (🟢 Spoken / 🟡 Check / 🔴 Review).
  - Auto-scroll with export functionality.
  - Memory-limited to 500 blocks for smooth performance on large files.

---

## 3. Strict AI Translation Guidelines & Spoken Sinhala Mandate
The translation engine strictly enforces everyday **Spoken Sinhala (කතා කරන සිංහල / කථා ව්‍යවහාරය)** dialogue, strictly forbidding formal literary or written book Sinhala (ලිඛිත සිංහල).

### Key Rules:
1. **NEVER** use formal written or literary Sinhala (ලිඛිත සිංහල).
2. **NEVER** use written grammar or literary verb endings such as: -න්නේය, -න්නෙමි, -ති, -මු, -ය, -වේ, -නොවේ, -නැත.
3. **ALWAYS** use spoken verb forms ending in: -නවා, -න්න, -න්නම්, -නවාද, -වා, -යි, -නෑ, -එපා.
4. **ALWAYS** use spoken conversational pronouns: 'ඔයා' (never 'ඔබ'), 'එයා' (never 'ඔහු' or 'ඇය'), 'ඒගොල්ලෝ' (never 'ඔවුන්').
5. Keep commonly used English technical terms or loan words when they sound more natural.
6. Multi-line subtitle dialogues preserve their dialogue format.
7. Return ONLY the direct final raw spoken Sinhala subtitle line — no notes, explanations, or commentary.

### Conversational Few-Shot Grounding
Causal LLMs default to written/formal Sinhala unless anchored by conversational dialogue turns. The pipeline automatically feeds multi-turn spoken dialogue examples into the chat template, grounding the model's generation in natural spoken Sinhala. 14 examples covering questions, negations, commands, emotions, past/future tense, conditionals, loan words, and multi-speaker lines are loaded dynamically from `anti_gravity/data/few_shots.json`.

### Anti-Explanation & Anti-Instruction Post-Processing Filter
A multi-stage cleaning pipeline ensures that zero system instructions, Wikipedia notes, or meta commentary ever leak into the final `.srt` output:
- **Blank-line Paragraph Isolation:** Truncates trailing paragraphs (notes, Wikipedia remarks).
- **Section Cutoffs:** Cuts before `Note:`, `Explanation:`, `Commentary:`, `Breakdown:`, `සටහන:`, etc.
- **Language Ratio Enforcement:** Drops lines where Latin/English characters dominate (>40%).
- **Prefix Removal:** Strips `Translation:`, `Sinhala:`, `Spoken Sinhala:`, etc.
- **Failure Marking:** Lines that fail to produce Sinhala output are marked with `⚠️` prefix for easy identification.

---

## 4. Functional Features

### 1. File Handling & Drag-and-Drop
- Drag and drop single or multiple `.srt` files directly into the UI.
- Drop an entire folder to recursively search and queue all `.srt` subtitle files.
- Manual file and folder browsing buttons.
- Duplicate file detection (by absolute path).

### 2. Queue Management
- Interactive table displaying: Row number, file name, total subtitle count, progress, and status badges (`Queued`, `Processing`, `Completed`, `Failed`, `Aborted`).
- Per-row actions: **Move Up (▲)**, **Move Down (▼)**, and **Remove (✕)**.

### 3. Execution & Dynamic Button States
- **Start Queue Button:** Changes dynamically from `"⚡ Start Queue"` → `"⏳ Loading Model..."` → `"⏳ Translating Queue..."` and resets on completion.
- **Abort Controls:** Abort current file or entire queue safely.

### 4. Smart Scene-Aware Batching
- Batches are split at scene boundaries (timestamp gaps > 2 seconds) rather than arbitrary fixed positions.
- Rapid-fire dialogue (gaps < 0.5s) is kept together for better context coherence.

### 5. Translation Quality Monitoring
- Real-time quality scoring per line (🟢 🟡 🔴 badges).
- Glossary-injected prompts with 200+ terms.
- Post-translation subtitle validation: line length, CPS (characters per second), repetition detection.
- Failed translations marked with `⚠️` and counted in summary.

### 6. Settings Persistence
- All settings saved to `%APPDATA%/SinhalaSubtitleTranslator/settings.json`.
- Persists across sessions: model selection, batch size, temperature, max tokens, system prompt, HF token.

### 7. Logging & Error Handling
- Console logging (INFO) + rotating file log (DEBUG, 5MB × 3 files).
- Global exception handler with user-friendly error dialogs.
- Batch-level error recovery: failed batches are marked, not fatal.

---

## 5. Compute Device Selection & CPU Incompatibility Handling
Users can switch between **GPU** and **CPU** directly from the bottom control bar:
- **GPU (Default):** Utilizes NVIDIA CUDA and 4-bit NF4 quantization for maximum throughput. GPU name is auto-detected.
- **CPU:** Supported by models like `facebook/nllb-200-distilled-600M`.
- **Incompatibility Warning:** If a user selects CPU while a 4-bit quantized model is chosen, the application displays an explanatory alert.

---

## 6. Project Structure

```
anti_gravity/
├── __init__.py               # Package marker
├── config.py                 # Configuration, themes, model definitions, system prompt
├── glossary.py               # English→Sinhala glossary engine (word-boundary matching)
├── main.py                   # Top-level entry point with logging configuration
├── spoken_converter.py       # Written-to-spoken Sinhala converter & quality scorer
├── styles.py                 # QSS styling (Obsidian slate, Neon amber, Frameless controls)
├── subtitle_parser.py        # Robust .srt parsing, encoding detection, edge-case handling
├── subtitle_validator.py     # SRT compliance validation (CPS, line length, repetition, etc.)
├── system_monitor.py         # Hardware telemetry poller (GPU VRAM, compute, CPU, RAM)
├── translator_engine.py      # 4-bit NF4 inference pipeline & anti-explanation cleanup
├── worker.py                 # QThread background worker with scene-aware batching
├── data/
│   ├── glossary.json         # 200+ English→Spoken Sinhala glossary terms
│   └── few_shots.json        # 14 categorized few-shot translation examples
└── ui/
    ├── __init__.py           # UI package marker
    ├── header_bar.py         # Draggable frameless header, window controls
    ├── file_queue_widget.py  # Queue table with drag-and-drop zone
    ├── resource_monitor_widget.py # Real-time CPU, RAM, GPU VRAM meters
    ├── live_preview_widget.py# Live preview console with quality badges & export
    ├── bottom_bar.py         # Device selector, model dropdown, start button
    ├── settings_dialog.py    # Hyperparameters, batch size, temperature, system prompt
    └── installer_wizard.py   # Dependency & model checker with auto-download

tests/
├── __init__.py
├── test_subtitle_parser.py   # Parser edge cases, encoding, save/re-number
├── test_glossary.py          # Word boundary matching, term ordering
├── test_spoken_converter.py  # Conversion rules, protected words, scoring
├── test_subtitle_validator.py# Validation checks (CPS, repetition, length ratio)
└── test_integration.py       # Full pipeline integration test with mock model

test_pipeline.py              # Legacy integration tests
test_clean_filter.py          # clean_sinhala_output filter tests
test_sample.srt               # Sample test subtitle
build_exe.py                  # PyInstaller build script (with CUDA, data, hidden imports)
run.bat                       # One-click Windows launcher
README.md                     # This file
```

---

## 7. Execution & Usage Instructions

### Method 1: One-Click Windows Batch Launcher
Double-click `run.bat` in the project root folder.

### Method 2: Command Line (PowerShell / CMD)
```powershell
cd "g:\Ai\Sinhala Subtitle Translator"
python main.py
```

### Usage Steps in the Application:
1. **Add Files:** Drag and drop your `.srt` files into the queue area or click **"+ Add Files"** / **"📁 Add Folder"**.
2. **Select Output Location:** Choose a custom output folder or leave blank to save in the source folder with `_sinhala_clean.srt`.
3. **Choose Compute Device:** Select **GPU** (default, auto-detected) or **CPU**.
4. **Choose AI Model:** Select **HelaLM 4B (Recommended)** or your preferred model from the dropdown.
5. **Configure Settings:** Click the settings icon to adjust batch size, temperature, max tokens, and system prompt.
6. **Start Translation:** Click **"⚡ Start Queue"**. Monitor live translation previews and hardware gauges.
7. **Review Output:** Check the quality badges in the preview console. Export the full log if needed.

---

## 8. Packaging into Standalone Windows Executable (.exe)
To package the entire project into a self-contained `.exe`:

```powershell
python build_exe.py
```

- PyInstaller will package the application in `dist/AntiGravity/`.
- Launch the application directly via `dist/AntiGravity/AntiGravity.exe`.
- The build script includes: CUDA DLLs (`--collect-all=torch`), data files (glossary, few-shots), and all hidden imports.

---

## 9. Troubleshooting & Dependency Management
If any dependencies or model weights are missing:
1. Click **"🛠 Setup & Health"** in the application header.
2. The wizard checks all library packages and local model caching status.
3. Select any missing model(s) and click **"⚡ Auto-Install & Download"**.

### Common Issues:
| Issue | Solution |
|---|---|
| CUDA out of memory | Reduce batch size in Settings or use a smaller model (NLLB-200) |
| Model download fails | Set your Hugging Face token in Settings for gated models |
| Translations are truncated | Increase "Max Generation Tokens" in Settings (default: 196) |
| CPU + 4-bit model selected | Switch to GPU or select the NLLB-200 model for CPU inference |
| Application log location | `%APPDATA%\SinhalaSubtitleTranslator\app.log` |

---

## 10. Quality Assurance & Roadmap
A detailed 6-phase improvement plan has been executed:

| Phase | Status | Description |
|---|---|---|
| **Phase 1** — Critical Bug Fixes | ✅ Complete | Context window, MAX_NEW_TOKENS, quality scoring, installer fix, regex fix, failure marking, settings persistence |
| **Phase 2** — Translation Quality | ✅ Complete | Glossary injection, multi-line preservation, spoken converter fix, 14 few-shots, subtitle validation |
| **Phase 3** — Error Handling | ✅ Complete | Batch error recovery, logging, exception handler, engine init protection, SRT parser edge cases |
| **Phase 4** — UI/UX Improvements | ✅ Complete | Dynamic GPU detection, HTML escaping, preview memory limit, settings validation, double-check fix |
| **Phase 5** — Testing | ✅ Complete | Fixed broken tests, comprehensive unit tests, integration test with mock model |
| **Phase 6** — Performance & Advanced | ✅ Complete | Scene-aware batching, expanded glossary (200+), build_exe.py fix, documentation update |

See [`IMPROVEMENT_PLAN_V2.md`](IMPROVEMENT_PLAN_V2.md) for the full detailed plan.
