"""
Fine-tuning script for training HelaLM-4B or SinLlama on English-to-Spoken-Sinhala subtitle dialogue pairs using QLoRA.
Can run on NVIDIA RTX 3060 12GB.
"""
import os
import argparse
import torch
from datasets import load_dataset
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    BitsAndBytesConfig,
    TrainingArguments
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from trl import SFTTrainer, SFTConfig

DEFAULT_MODEL = "Jainamshahhh/helalm-4b"

def main():
    parser = argparse.ArgumentParser(description="QLoRA fine-tuning for Spoken Sinhala Subtitles")
    parser.add_argument("--model_id", type=str, default=DEFAULT_MODEL, help="Base model identifier")
    parser.add_argument("--dataset_path", type=str, default="data/subtitle_pairs.jsonl", help="Path to JSONL dataset")
    parser.add_argument("--output_dir", type=str, default="models/helalm-spoken-lora", help="Output directory for LoRA adapter")
    parser.add_argument("--epochs", type=int, default=3, help="Number of training epochs")
    parser.add_argument("--batch_size", type=int, default=2, help="Per device batch size")
    parser.add_argument("--grad_accum", type=int, default=4, help="Gradient accumulation steps")
    parser.add_argument("--lr", type=float, default=2e-4, help="Learning rate")
    args = parser.parse_args()

    print(f"=== Starting QLoRA fine-tuning for {args.model_id} ===")
    print(f"Dataset: {args.dataset_path}")
    print(f"Output adapter dir: {args.output_dir}")

    if not os.path.exists(args.dataset_path):
        print(f"Error: Dataset {args.dataset_path} does not exist.")
        print("Please prepare a JSONL file with 'messages' or ('english', 'sinhala') pairs.")
        return

    # 1. Quantization Configuration (4-bit NF4)
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True
    )

    # 2. Tokenizer & Base Model
    print("Loading tokenizer and quantized base model...")
    try:
        tokenizer = AutoTokenizer.from_pretrained(args.model_id, trust_remote_code=True, local_files_only=True)
    except Exception:
        tokenizer = AutoTokenizer.from_pretrained(args.model_id, trust_remote_code=True)

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    try:
        model = AutoModelForCausalLM.from_pretrained(
            args.model_id,
            quantization_config=bnb_config,
            device_map="auto",
            trust_remote_code=True,
            local_files_only=True
        )
    except Exception:
        model = AutoModelForCausalLM.from_pretrained(
            args.model_id,
            quantization_config=bnb_config,
            device_map="auto",
            trust_remote_code=True
        )
    model = prepare_model_for_kbit_training(model)

    # 3. LoRA Configuration targeting attention projections
    lora_config = LoraConfig(
        r=16,
        lora_alpha=32,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM"
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    # 4. Load dataset
    dataset = load_dataset("json", data_files=args.dataset_path, split="train")

    def format_chat_data(batch):
        formatted = []
        for msgs in batch["messages"]:
            text = tokenizer.apply_chat_template(msgs, tokenize=False)
            formatted.append(text)
        return {"text": formatted}

    if "messages" in dataset.column_names:
        dataset = dataset.map(format_chat_data, batched=True)

    # 5. Training Arguments via SFTConfig
    training_args = SFTConfig(
        output_dir=args.output_dir,
        dataset_text_field="text",
        max_length=512,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        learning_rate=args.lr,
        bf16=True,
        logging_steps=5,
        save_strategy="epoch",
        optim="paged_adamw_8bit",
        report_to="none"
    )

    trainer = SFTTrainer(
        model=model,
        train_dataset=dataset,
        processing_class=tokenizer,
        args=training_args
    )

    print("Beginning training...")
    trainer.train()

    print(f"Saving final trained LoRA adapter to {args.output_dir}...")
    model.save_pretrained(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)
    print("Fine-tuning completed successfully!")

if __name__ == "__main__":
    main()

