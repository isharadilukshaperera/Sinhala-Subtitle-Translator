"""
Core AI Translation Pipeline for Anti Gravity Subtitle Translator.
Strictly implements HelaLM-4B 4-bit NF4 optimized pipeline with vectorized batching
and native Sri Lankan translation guidelines.
"""
import re
import os
import gc
from typing import List, Optional, Callable, Tuple
import logging

import torch
from anti_gravity.config import (
    DEFAULT_MODEL_ID,
    DEFAULT_BATCH_SIZE,
    DEFAULT_MAX_NEW_TOKENS,
    DEFAULT_TEMPERATURE,
    SYSTEM_INSTRUCTION,
    SPOKEN_FEW_SHOTS,
    SUPPORTED_MODELS,
)
from anti_gravity.spoken_converter import convert_written_to_spoken, score_translation_quality
from anti_gravity.glossary import GlossaryManager

logger = logging.getLogger("anti_gravity.engine")


def clean_sinhala_output(raw_text: str, original_input: str = "") -> str:
    """
    Comprehensive anti-explanation, anti-instruction, and clean dialogue extractor.
    Guarantees no system instructions, prompt repetitions, notes, or English residue
    leak into final subtitles or live preview.
    """
    text = raw_text.strip()
    if not text:
        if original_input:
            return f"⚠️ {original_input}"
        return ""

    # 1. Remove HTML/XML-like turn tokens (e.g. <start_of_turn>, <|im_end|>, etc.)
    text = re.sub(r"<\|?[a-zA-Z0-9_\-]+(?:_[a-zA-Z0-9_\-]+)*\|?>", "", text)
    text = re.sub(r"\[/?(?:INST|SYS|MODEL)\]", "", text, flags=re.IGNORECASE)

    # 1b. Remove leading prefix headers (e.g. "Sinhala: ", "Translation: ")
    prefix_pattern = r"^(?:(?:Here(?:'s| is) (?:the )?(?:raw )?(?:Sinhala )?translation)|Translation|Sinhala Translation|Sinhala|Translated Text|සිංහල පරිවර්තනය|සිංහල|පරිවර්තනය|Output|Result|Spoken Sinhala)\s*:\s*"
    text = re.sub(prefix_pattern, "", text, flags=re.IGNORECASE).strip()

    # 1c. Cut off if the model started another dialogue turn without a newline (e.g. "...English: I am having...")
    text = re.split(r"(?im)\b(?:English(?:\s+subtitle)?|Sinhala|Spoken Sinhala|User|Assistant)\s*:", text)[0].strip()

    # 1d. Cut off if an English sentence or prompt repeat immediately follows Sinhala dialogue
    text = re.split(r"(?<=[.!?\u0DF4\u0964\s])(?=[A-Z][a-z]{2,}\b)", text)[0].strip()

    # 2. Check if text contains Sinhala script (Unicode block 0D80-0DFF)
    has_sinhala = bool(re.search(r"[\u0D80-\u0DFF]", text))
    if not has_sinhala:
        # Mark failed translations so user can see which lines weren't translated
        if original_input:
            logger.warning(f"No Sinhala in output for: '{original_input}' -> '{text[:80]}'")
            return f"⚠️ {original_input}"
        return text

    # 3. If output contains Sinhala, find the FIRST paragraph containing Sinhala script.
    # Preceding paragraphs are English prompt echoes; succeeding paragraphs are notes/commentary.
    if has_sinhala:
        paragraphs = re.split(r"\r?\n\s*\r?\n", text)
        for p in paragraphs:
            if re.search(r"[\u0D80-\u0DFF]", p):
                text = p.strip()
                break

    # 4. Cut off at horizontal rules / dividers (---, ___, ***)
    text = re.split(r"\n\s*(?:---+|___+|\*\*\*+)\s*", text)[0]

    # 5. Cut off at explicit Note/Explanation/Commentary section headers
    cutoff_pattern = r"(?im)\n\s*(?:\*+\s*)?(?:Note|Notes|Translation Note|Translation Notes|Linguistic Note|Explanation|Commentary|Breakdown|Analysis|Key Points|සටහන|විස්තරය|පැහැදිලි කිරීම)\s*[:\*\-]"
    text = re.split(cutoff_pattern, text)[0]

    # Also cutoff at "This translation..." or "Here is the..." if on a new line
    text = re.split(r"(?im)\n\s*(?:This translation|Here(?:'s| is) (?:the )?(?:raw )?(?:Sinhala )?translation)", text)[0]

    # 5b. Cut off conversational commentary / tutorial residue phrases
    commentary_pattern = r"(?im)\b(?:අනිත් එක|මේ වගේ දේවල්|මම දන්නේ නෑ|මේවා ඉංග්‍රීසියෙන්|සිංහලෙන් කියන විදිහ|වෙනම ක්‍රමයක්|භාවිතා කරන්න පුලුවන්|මෙම ව්‍යාපෘතිය|මෙම ලිපියෙහි|අරමුණ වන්නේ|මේ ලිපිය|ලිපිය|ප්‍රයෝජනවත්|සමුගන්නවා|FB|ඊමේල්|ඔබේ නම|මම හිතනවා|යොමු කරන්න)\b"
    text = re.split(commentary_pattern, text)[0].strip()

    # 6. Remove parenthesized notes like (Note: ...) or (සටහන: ...) or (ඉහත උදාහරණ... ) or (ඔබේ නම)
    # Only remove parenthetical content >10 chars (likely model notes/explanations, not real content)
    text = re.sub(r"\s*[\(\[][^\)\]]{10,}[\)\]]", "", text).strip()

    # 7. Remove markdown code blocks
    if text.startswith("```") and text.endswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text).strip()

    # 8. Instruction keywords to ruthlessly eliminate if present anywhere in a line
    instruction_keywords = [
        "native sri lankan", "translator and language editor", "language editor",
        "translation requirement", "translation requirements", "preserve the original",
        "natural, fluent sinhala", "avoid literal", "return only the raw", "translate this english",
        "english subtitle", "here is the translation", "here is the natural sinhala",
        "here's the translation", "sure, here", "sure!", "translated text", "raw final translated",
        "note:", "notes:", "explanation:", "linguistic note:", "commentary:", "breakdown:",
        "translation note", "this translation", "prioritizes the", "colloquial",
        "romanized sinhala", "workplace messages", "casual messages", "movie dialogue",
        "colloquial sri lankan",
        "සටහන", "විස්තරය", "පැහැදිලි කිරීම", "මෙම ව්‍යාපෘතිය", "මෙම ලිපියෙහි", "අරමුණ වන්නේ", "පිටුව අන්තිමට සැකසුවේ"
    ]

    lines = text.split("\n")
    cleaned_lines = []

    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue

        # If line is a markdown bullet pointing to an explanation
        if re.match(r"^[\*\-\•]\s*(?:\*\*)?[a-zA-Z0-9\s\"\'\:\-]+(?:\*\*)?\s*:", line_stripped):
            continue

        # Remove prefix tags like "Here is the translation:", "Translation:", "Sinhala:", "සිංහල:"
        prefix_pattern = r"^(?:(?:Here(?:'s| is) (?:the )?(?:raw )?(?:Sinhala )?translation)|Translation|Sinhala Translation|Sinhala|Translated Text|සිංහල පරිවර්තනය|සිංහල|පරිවර්තනය|Output|Result|Spoken Sinhala)\s*:\s*"
        line_clean = re.sub(prefix_pattern, "", line_stripped, flags=re.IGNORECASE).strip()

        # If the output contains Sinhala characters, any line that has NO Sinhala characters
        # is prompt repetition, instructions, or English conversational residue. Drop it!
        if has_sinhala:
            sinhala_chars = len(re.findall(r"[\u0D80-\u0DFF]", line_clean))
            if sinhala_chars == 0:
                continue

            # If English/Latin letters dominate (> 40% of alphabetic characters), it's an English note!
            latin_chars = len(re.findall(r"[a-zA-Z]", line_clean))
            total_letters = sinhala_chars + latin_chars
            if total_letters > 0 and (latin_chars / total_letters) > 0.40:
                continue

        l_lower = line_clean.lower()
        if any(kw in l_lower for kw in instruction_keywords):
            continue

        # Strip quotation marks, open brackets, colons, dashes, and asterisks
        line_clean = line_clean.strip("\"'“”«»`* ([{:-")

        if line_clean:
            cleaned_lines.append(line_clean)

    # Rejoin surviving lines
    final_result = "\n".join(cleaned_lines).strip()

    # Deduplicate repeated sentences or degenerative loops
    if final_result:
        final_result = re.sub(r"(.{12,}?)\1+", r"\1", final_result)
        sentences = re.split(r"(?<=[.!?\u0DF4\u0964])\s*", final_result)
        dedup_sentences = []
        commentary_triggers = [
            "අනිත් එක", "මේ වගේ දේවල්", "මම දන්නේ නෑ", "මේවා ඉංග්‍රීසියෙන්", "සිංහලෙන් කියන විදිහ",
            "වෙනම ක්‍රමයක්", "භාවිතා කරන්න පුලුවන්", "මෙම ව්‍යාපෘතිය", "මෙම ලිපියෙහි", "අරමුණ වන්නේ",
            "මේ ලිපිය", "ලිපිය", "ප්‍රයෝජනවත්", "සමුගන්නවා", "FB", "ඊමේල්", "ඔබේ නම", "මම හිතනවා", "යොමු කරන්න"
        ]
        for s in sentences:
            s_clean = s.strip()
            if not s_clean:
                continue
            if any(trig in s_clean for trig in commentary_triggers):
                break
            if not dedup_sentences or s_clean != dedup_sentences[-1]:
                dedup_sentences.append(s_clean)
        final_result = " ".join(dedup_sentences).strip()

    # Apply Phase 1 deterministic spoken converter on the output
    if final_result:
        final_result = convert_written_to_spoken(final_result)

    # Fallback to marked original input only if empty
    if not final_result and original_input:
        logger.warning(f"Empty after cleaning for: '{original_input}'")
        return f"⚠️ {original_input}"

    return final_result


class TranslationEngine:
    """Manages model loading, 4-bit quantization, and batch inference."""

    def __init__(self, model_id: str = DEFAULT_MODEL_ID, device: str = "cuda", hf_token: Optional[str] = None):
        self.model_id = model_id
        self.requested_device = device
        self.device = "cuda" if (device == "cuda" and torch.cuda.is_available()) else "cpu"
        self.hf_token = hf_token or os.environ.get("HF_TOKEN") or None
        self.model = None
        self.tokenizer = None
        self.is_loaded = False
        self.model_type = SUPPORTED_MODELS.get(model_id, {}).get("type", "causal_lm")
        self.system_prompt = SYSTEM_INSTRUCTION
        self.batch_size = DEFAULT_BATCH_SIZE
        self.temperature = DEFAULT_TEMPERATURE
        self.max_new_tokens = DEFAULT_MAX_NEW_TOKENS
        self.glossary = GlossaryManager()
        self.enable_glossary = True
        self.context_window_size = 3
        self.use_sdpa = True

    def set_device(self, device: str):
        """Switches compute device between 'cuda' (GPU) and 'cpu'."""
        self.requested_device = device
        self.device = "cuda" if (device == "cuda" and torch.cuda.is_available()) else "cpu"

    def check_device_compatibility(self, model_id: Optional[str] = None, device: Optional[str] = None) -> tuple[bool, str]:
        """Validates whether the chosen model can execute on the target device."""
        target_model = model_id or self.model_id
        target_dev = device or self.device
        info = SUPPORTED_MODELS.get(target_model, {})

        if target_dev == "cpu" and not info.get("supports_cpu", False):
            model_name = info.get("name", target_model)
            reason = info.get("cpu_reason", "This model uses 4-bit NF4 quantization which strictly requires an NVIDIA CUDA GPU.")
            msg = (
                f"CPU Incompatibility:\n\n"
                f"'{model_name}' cannot run on CPU.\n"
                f"{reason}\n\n"
                f"Options:\n"
                f"1. Switch Compute Device back to '⚡ GPU (RTX 3060)'.\n"
                f"2. Or select a CPU-capable model like 'NLLB-200 Distilled 600M'."
            )
            return False, msg
        return True, ""

    def load_model(self, progress_callback: Optional[Callable[[str, int], None]] = None) -> bool:
        """Loads and prepares the model with 4-bit quantization and left-padding."""
        if self.is_loaded and self.model is not None:
            return True

        # Pre-flight device compatibility check
        is_compat, compat_err = self.check_device_compatibility(self.model_id, self.device)
        if not is_compat:
            raise RuntimeError(compat_err)

        from transformers import AutoTokenizer, AutoConfig

        token = self.hf_token or os.environ.get("HF_TOKEN") or None

        if progress_callback:
            progress_callback(f"Connecting to {self.model_id}...", 10)

        # 1. Hugging Face Hub cache check & identifier validation
        from huggingface_hub import try_to_load_from_cache, HfApi

        cached_file = try_to_load_from_cache(self.model_id, "config.json")
        is_local_cached = isinstance(cached_file, str) and os.path.isfile(cached_file)

        if not is_local_cached:
            try:
                api = HfApi(token=token)
                model_info = api.model_info(self.model_id)
                if getattr(model_info, "gated", False) and not token:
                    raise RuntimeError(
                        f"Model '{self.model_id}' is gated on Hugging Face.\n"
                        f"Please enter your Hugging Face Access Token in Settings -> Inference & GPU."
                    )
            except Exception as e:
                err_str = str(e).lower()
                if "401" in err_str or "403" in err_str or "unauthorized" in err_str or "gated" in err_str:
                    raise RuntimeError(
                        f"Access restricted for model '{self.model_id}'.\n"
                        f"Please enter your Hugging Face Access Token in Settings."
                    ) from e
                elif "not found" in err_str or "404" in err_str or "repository not found" in err_str:
                    raise RuntimeError(
                        f"Model identifier '{self.model_id}' was not found on Hugging Face Hub.\n"
                        f"Please verify the model name in Settings."
                    ) from e

        # 2. Load Config
        try:
            if is_local_cached:
                try:
                    config = AutoConfig.from_pretrained(self.model_id, trust_remote_code=True, token=token, local_files_only=True)
                except Exception:
                    config = AutoConfig.from_pretrained(self.model_id, trust_remote_code=True, token=token)
            else:
                config = AutoConfig.from_pretrained(self.model_id, trust_remote_code=True, token=token)
        except Exception as e:
            err_msg = str(e)
            if "not a valid model identifier" in err_msg:
                raise RuntimeError(
                    f"Model identifier '{self.model_id}' was not found on Hugging Face.\n"
                    f"Please verify the model name in Settings (e.g. 'SAWithanage/SinLlama-Llama-3-8B-Merged' or 'Jainamshahhh/helalm-4b')."
                ) from e
            elif "401" in err_msg or "403" in err_msg or "gated" in err_msg.lower():
                raise RuntimeError(
                    f"Access restricted for model '{self.model_id}'.\n"
                    f"If this is a gated or private model, please enter your Hugging Face Access Token in Settings."
                ) from e
            raise

        is_seq2seq = getattr(config, "is_encoder_decoder", False)
        self.model_type = "seq2seq" if is_seq2seq else "causal_lm"

        # 3. Load Tokenizer
        if progress_callback:
            progress_callback(f"Loading tokenizer for {self.model_id}...", 20)

        tok_kwargs = {
            "trust_remote_code": True,
            "padding_side": "left",
            "token": token
        }
        if is_local_cached:
            try:
                self.tokenizer = AutoTokenizer.from_pretrained(self.model_id, local_files_only=True, **tok_kwargs)
            except Exception:
                self.tokenizer = AutoTokenizer.from_pretrained(self.model_id, **tok_kwargs)
        else:
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_id, **tok_kwargs)

        if self.tokenizer.pad_token is None:
            if self.tokenizer.eos_token is not None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            else:
                self.tokenizer.pad_token = self.tokenizer.unk_token

        if progress_callback:
            dev_desc = "GPU (4-bit NF4)" if self.device == "cuda" else "CPU"
            progress_callback(f"Loading weights for {self.model_id} on {dev_desc}...", 40)

        model_kwargs = {"token": token}
        if is_local_cached:
            model_kwargs["local_files_only"] = True

        if self.model_type == "seq2seq":
            from transformers import AutoModelForSeq2SeqLM
            if self.device == "cuda":
                try:
                    self.model = AutoModelForSeq2SeqLM.from_pretrained(
                        self.model_id,
                        torch_dtype=torch.float16,
                        device_map="auto",
                        **model_kwargs
                    )
                except Exception:
                    model_kwargs.pop("local_files_only", None)
                    self.model = AutoModelForSeq2SeqLM.from_pretrained(
                        self.model_id,
                        torch_dtype=torch.float16,
                        device_map="auto",
                        **model_kwargs
                    )
            else:
                try:
                    self.model = AutoModelForSeq2SeqLM.from_pretrained(
                        self.model_id,
                        torch_dtype=torch.float32,
                        **model_kwargs
                    ).to("cpu")
                except Exception:
                    model_kwargs.pop("local_files_only", None)
                    self.model = AutoModelForSeq2SeqLM.from_pretrained(
                        self.model_id,
                        torch_dtype=torch.float32,
                        **model_kwargs
                    ).to("cpu")
        else:
            from transformers import AutoModelForCausalLM, BitsAndBytesConfig

            if self.device == "cuda":
                # Determine optimal PyTorch compute precision (bfloat16 on Ampere/RTX 3060+, else float16)
                use_bf16 = torch.cuda.is_available() and torch.cuda.is_bf16_supported()
                compute_dtype = torch.bfloat16 if use_bf16 else torch.float16

                bnb_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_quant_type="nf4",
                    bnb_4bit_compute_dtype=compute_dtype,
                    bnb_4bit_use_double_quant=True
                )

                load_kwargs = dict(model_kwargs)
                if self.use_sdpa:
                    load_kwargs["attn_implementation"] = "sdpa"

                try:
                    self.model = AutoModelForCausalLM.from_pretrained(
                        self.model_id,
                        quantization_config=bnb_config,
                        device_map="auto",
                        trust_remote_code=True,
                        **load_kwargs
                    )
                except Exception as e:
                    logger.warning(f"First load attempt failed, retrying fallback: {e}")
                    load_kwargs.pop("attn_implementation", None)
                    try:
                        self.model = AutoModelForCausalLM.from_pretrained(
                            self.model_id,
                            quantization_config=bnb_config,
                            device_map="auto",
                            trust_remote_code=True,
                            **load_kwargs
                        )
                    except Exception:
                        load_kwargs.pop("local_files_only", None)
                        self.model = AutoModelForCausalLM.from_pretrained(
                            self.model_id,
                            quantization_config=bnb_config,
                            device_map="auto",
                            trust_remote_code=True,
                            **load_kwargs
                        )
            else:
                try:
                    self.model = AutoModelForCausalLM.from_pretrained(
                        self.model_id,
                        torch_dtype=torch.float32,
                        trust_remote_code=True,
                        **model_kwargs
                    ).to("cpu")
                except Exception:
                    model_kwargs.pop("local_files_only", None)
                    self.model = AutoModelForCausalLM.from_pretrained(
                        self.model_id,
                        torch_dtype=torch.float32,
                        trust_remote_code=True,
                        **model_kwargs
                    ).to("cpu")

        if progress_callback:
            progress_callback("Model weights loaded into VRAM. Finalizing optimization...", 80)

        # Optional torch.compile (fails gracefully on Windows without compiler)
        if self.device == "cuda" and hasattr(torch, "compile"):
            try:
                # Disable compile on Windows if MSVC is not available
                if os.name != "nt":
                    self.model = torch.compile(self.model, mode="reduce-overhead")
            except Exception as e:
                logger.info(f"torch.compile skipped on current platform: {e}")

        # Check if fine-tuned LoRA adapter exists in models/ (ONLY for HelaLM)
        if self.model_id == "Jainamshahhh/helalm-4b":
            adapter_dir = os.path.join(os.path.dirname(__file__), "..", "models", "helalm-spoken-lora")
            if os.path.exists(os.path.join(adapter_dir, "adapter_model.safetensors")):
                try:
                    from peft import PeftModel
                    logger.info(f"Loading custom fine-tuned LoRA adapter from {adapter_dir}")
                    self.model = PeftModel.from_pretrained(self.model, adapter_dir)
                except Exception as e:
                    logger.warning(f"Could not load LoRA adapter: {e}")

        self.model.eval()
        self.is_loaded = True

        if progress_callback:
            progress_callback("Ready for inference.", 100)

        return True

    def unload_model(self):
        """Unload model from GPU memory to free VRAM with PyTorch cache cleanup."""
        self.model = None
        self.tokenizer = None
        self.is_loaded = False
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()

    def _format_prompt(self, text: str, context_lines: list = None, glossary_hints: list = None) -> str:
        """
        Formats the input dialog using chat template with:
        - Multi-turn few-shot spoken anchors (Phase 3)
        - Sliding-window context from previous translations (Phase 2)
        - Glossary term injection into prompt (Phase 5)
        - Clean dialogue presentation
        """
        if self.model_type == "seq2seq":
            return text

        # Build context block from previous translations
        context_block = ""
        if context_lines:
            ctx_parts = ["[Previous dialogue for context — do NOT re-translate:]"]
            for en, si in context_lines[-self.context_window_size:]:
                ctx_parts.append(f'"{en}" → "{si}"')
            context_block = "\n".join(ctx_parts) + "\n\n"

        # Build glossary hint block
        glossary_block = ""
        if glossary_hints and len(glossary_hints) > 0:
            hints = glossary_hints[:8]  # Limit to 8 terms to save context window
            g_parts = ["[Glossary — use these exact translations:]"]
            for en_term, si_term in hints:
                g_parts.append(f"{en_term} = {si_term}")
            glossary_block = "\n".join(g_parts) + "\n\n"

        # Special handling for SinLlama or models without chat template (base completion models)
        if "sinllama" in self.model_id.lower() or not (hasattr(self.tokenizer, "chat_template") and self.tokenizer.chat_template):
            prompt_parts = [
                "You are an expert Sri Lankan Sinhala subtitle translator. Translate English movie dialogue into natural, colloquial everyday spoken Sinhala. Avoid formal literary Sinhala. Preserve character names, emotions, and meaning.\n"
            ]
            for en, si in SPOKEN_FEW_SHOTS:
                if en.strip().lower() != text.strip().lower():
                    prompt_parts.append(f"English: {en}\nSinhala: {si}\n")
            if context_block:
                prompt_parts.append(context_block)
            if glossary_block:
                prompt_parts.append(glossary_block)
            prompt_parts.append(f"[Translate ONLY this line:]\nEnglish: {text}\nSinhala:")
            return "\n".join(prompt_parts)

        user_content_parts = []
        if context_block:
            user_content_parts.append(context_block)
        if glossary_block:
            user_content_parts.append(glossary_block)
        user_content_parts.append(f"English subtitle: {text}\nSpoken Sinhala:")
        target_user = "".join(user_content_parts)

        # Multi-turn few-shot conversation establishing spoken Sinhala dialogue register
        messages = [{"role": "system", "content": self.system_prompt}]
        for en, si in SPOKEN_FEW_SHOTS:
            if en.strip().lower() != text.strip().lower():
                messages.append({"role": "user", "content": f"English subtitle: {en}\nSpoken Sinhala:"})
                messages.append({"role": "assistant", "content": si})
        messages.append({"role": "user", "content": target_user})

        # Check if tokenizer has apply_chat_template
        if hasattr(self.tokenizer, "chat_template") and self.tokenizer.chat_template:
            try:
                return self.tokenizer.apply_chat_template(
                    messages,
                    tokenize=False,
                    add_generation_prompt=True
                )
            except Exception as e:
                logger.debug(f"Direct apply_chat_template failed: {e}. Trying merged system prompt.")
                # Fallback for templates that reject system role: merge into first user turn
                merged_first = f"{self.system_prompt}\n\nEnglish subtitle: {SPOKEN_FEW_SHOTS[0][0]}\nSpoken Sinhala:"
                fallback_messages = [
                    {"role": "user", "content": merged_first},
                    {"role": "assistant", "content": SPOKEN_FEW_SHOTS[0][1]}
                ]
                for en, si in SPOKEN_FEW_SHOTS[1:]:
                    fallback_messages.append({"role": "user", "content": f"English subtitle: {en}\nSpoken Sinhala:"})
                    fallback_messages.append({"role": "assistant", "content": si})
                fallback_messages.append({"role": "user", "content": target_user})
                try:
                    return self.tokenizer.apply_chat_template(
                        fallback_messages,
                        tokenize=False,
                        add_generation_prompt=True
                    )
                except Exception as e2:
                    logger.debug(f"Fallback apply_chat_template failed: {e2}")

        # Standard Instruction Fallback (ChatML format)
        parts = [f"<|im_start|>system\n{self.system_prompt}<|im_end|>"]
        for en, si in SPOKEN_FEW_SHOTS:
            parts.append(f"<|im_start|>user\nEnglish subtitle: {en}\nSpoken Sinhala:<|im_end|>")
            parts.append(f"<|im_start|>assistant\n{si}<|im_end|>")
        parts.append(f"<|im_start|>user\n{target_user}<|im_end|>")
        parts.append("<|im_start|>assistant\n")
        return "\n".join(parts)

    def translate_batch(
        self,
        lines: List[str],
        context_lines: list = None,
    ) -> Tuple[List[str], list]:
        """
        Vectorized batch inference for a list of subtitle strings.
        Applies model generation followed by Phase 1 deterministic spoken converter and Phase 5 glossary alignment.
        
        Args:
            lines: List of English subtitle strings to translate.
            context_lines: Rolling list of (english, sinhala) pairs from previous translations for context.
            
        Returns:
            Tuple of (translated_lines, updated_context_lines).
        """
        if not self.is_loaded or self.model is None or self.tokenizer is None:
            raise RuntimeError("Translation engine is not loaded!")

        if not lines:
            return [], context_lines or []

        if context_lines is None:
            context_lines = []

        # Identify non-empty dialogs and their original positions
        results = [""] * len(lines)
        active_indices = []
        active_prompts = []

        for i, raw_line in enumerate(lines):
            stripped = raw_line.strip()
            # If purely symbols, numbers, or whitespace, pass through unchanged
            if not stripped or re.match(r"^[\d\W]+$", stripped):
                results[i] = raw_line
            # Check for torrent/release group credits or subtitle sync metadata
            elif re.search(r"(?i)\b(?:re[\s\-]?encoded|encoded by|release group|torrent|yify|yts|psa|rarbg|eztv|baiscope|zoom\.lk|subtitles? by|synced by|sync and correct)\b", stripped):
                results[i] = raw_line
            else:
                # Clean parenthetical cultural glosses like 'Radhey. (blessed be...)'
                clean_input = stripped
                clean_input = re.sub(r"\s*\([a-zA-Z\s]{8,}\)", "", clean_input).strip()
                if not clean_input:
                    clean_input = stripped
                active_indices.append(i)
                # Find relevant glossary terms for this line
                glossary_hints = self.glossary.find_relevant_terms(clean_input) if self.enable_glossary else []
                active_prompts.append(self._format_prompt(
                    clean_input,
                    context_lines=context_lines,
                    glossary_hints=glossary_hints,
                ))

        if not active_prompts:
            return results, context_lines

        # Seq2Seq inference (e.g. NLLB-200)
        if self.model_type == "seq2seq":
            inputs = self.tokenizer(
                active_prompts,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=256
            )
            if self.device == "cuda":
                inputs = {k: v.to(self.model.device) for k, v in inputs.items()}
            else:
                inputs = {k: v.to("cpu") for k, v in inputs.items()}

            forced_bos_token_id = None
            try:
                forced_bos_token_id = self.tokenizer.convert_tokens_to_ids("sin_Sinh")
            except Exception:
                pass

            gen_kwargs = {
                "max_new_tokens": self.max_new_tokens,
                "num_beams": 1,
                "do_sample": False,
            }
            if forced_bos_token_id is not None:
                gen_kwargs["forced_bos_token_id"] = forced_bos_token_id

            with torch.inference_mode():
                generated_tokens = self.model.generate(**inputs, **gen_kwargs)
            
            decoded_outputs = self.tokenizer.batch_decode(generated_tokens, skip_special_tokens=True)
            for idx, decoded_text in zip(active_indices, decoded_outputs):
                cleaned = clean_sinhala_output(decoded_text, lines[idx])
                if self.enable_glossary:
                    cleaned = self.glossary.apply_glossary(lines[idx], cleaned)
                # Quality scoring with retry
                score, issues = score_translation_quality(lines[idx], cleaned)
                if score < 0.4:
                    logger.warning(f"Low quality ({score:.2f}) for: '{lines[idx]}' -> '{cleaned}' | Issues: {issues}")
                results[idx] = cleaned
                # Update rolling context
                context_lines.append((lines[idx], cleaned))
                if len(context_lines) > self.context_window_size:
                    context_lines = context_lines[-self.context_window_size:]
            return results, context_lines

        # Causal LM batch inference (HelaLM-4B / SinLlama)
        self.tokenizer.padding_side = "left"
        inputs = self.tokenizer(
            active_prompts,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=1024
        )
        if self.device == "cuda":
            inputs = {k: v.to(self.model.device) for k, v in inputs.items()}
        else:
            inputs = {k: v.to("cpu") for k, v in inputs.items()}

        input_lengths = inputs["input_ids"].shape[1]

        stop_token_ids = [self.tokenizer.eos_token_id]
        vocab = self.tokenizer.get_vocab() if hasattr(self.tokenizer, "get_vocab") else {}
        for token_str in ["<end_of_turn>", "<|im_end|>", "<|eot_id|>", "<eos>"]:
            if token_str in vocab:
                tid = self.tokenizer.convert_tokens_to_ids(token_str)
                if tid not in stop_token_ids:
                    stop_token_ids.append(tid)

        # Standard Hugging Face Transformers GenerationConfig
        from transformers import GenerationConfig

        gen_config = GenerationConfig(
            max_new_tokens=self.max_new_tokens,
            pad_token_id=self.tokenizer.pad_token_id,
            eos_token_id=stop_token_ids,
            repetition_penalty=1.15,
            do_sample=self.temperature > 0.05,
            temperature=self.temperature if self.temperature > 0.05 else 1.0,
            top_p=0.9 if self.temperature > 0.05 else 1.0,
        )

        with torch.inference_mode():
            outputs = self.model.generate(
                input_ids=inputs["input_ids"],
                attention_mask=inputs.get("attention_mask"),
                generation_config=gen_config
            )

        # Slice off input tokens to isolate newly generated tokens
        new_tokens = outputs[:, input_lengths:]
        decoded_outputs = self.tokenizer.batch_decode(new_tokens, skip_special_tokens=True)

        for idx, decoded_text in zip(active_indices, decoded_outputs):
            cleaned = clean_sinhala_output(decoded_text, lines[idx])
            if self.enable_glossary:
                cleaned = self.glossary.apply_glossary(lines[idx], cleaned)
            # Quality scoring with retry for low-quality translations
            score, issues = score_translation_quality(lines[idx], cleaned)
            if score < 0.4:
                logger.warning(f"Low quality ({score:.2f}) for: '{lines[idx]}' -> '{cleaned}' | Issues: {issues}")
            results[idx] = cleaned
            # Update rolling context window
            context_lines.append((lines[idx], cleaned))
            if len(context_lines) > self.context_window_size:
                context_lines = context_lines[-self.context_window_size:]

        return results, context_lines

