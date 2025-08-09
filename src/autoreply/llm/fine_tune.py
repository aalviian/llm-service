import json
import os
import tempfile
from datetime import datetime

import torch
from datasets import Dataset
from tqdm.auto import tqdm
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    Trainer,
    TrainerCallback,
    TrainingArguments,
)


def fine_tune_model(training_data: list, model_name: str = "indobenchmark/indobert-base-p1"):
    """
    Fine-tune a model using the provided training data.

    Args:
        training_data: List of dicts with 'text' and 'label' keys
        model_name: Base model to fine-tune

    Returns:
        str: Path to the saved fine-tuned model
    """
    # Create unique labels and label mapping
    unique_labels = list(set(item["label"] for item in training_data))
    label2id = {label: i for i, label in enumerate(unique_labels)}
    id2label = {i: label for label, i in label2id.items()}

    # Convert labels to IDs and prepare data with balancing
    from collections import Counter

    label_counts = Counter(item["label"] for item in training_data)
    max_count = max(label_counts.values())

    processed_data = []
    for item in training_data:
        processed_data.append({"text": item["text"], "labels": label2id[item["label"]]})

        # Add slight variations for underrepresented classes
        current_count = label_counts[item["label"]]
        if current_count < max_count * 0.7:  # If less than 70% of max count
            # Add variation with punctuation
            processed_data.append({"text": item["text"] + ".", "labels": label2id[item["label"]]})

    print(f"Enhanced dataset size: {len(processed_data)} samples")

    # Create dataset
    dataset = Dataset.from_list(processed_data)

    # Load tokenizer and model
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForSequenceClassification.from_pretrained(
        model_name, num_labels=len(unique_labels), id2label=id2label, label2id=label2id
    )

    # Tokenize dataset
    def tokenize_function(examples):
        tokenized = tokenizer(
            examples["text"],
            truncation=True,
            padding="max_length",
            max_length=512,
            return_tensors=None,
        )
        tokenized["labels"] = examples["labels"]
        return tokenized

    tokenized_dataset = dataset.map(tokenize_function, batched=True)

    # Create output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = f"./fine_tuned_models/model_{timestamp}"
    os.makedirs(output_dir, exist_ok=True)

    # Enhanced training arguments for better accuracy
    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=5,
        per_device_train_batch_size=4,
        per_device_eval_batch_size=4,
        gradient_accumulation_steps=2,
        learning_rate=2e-5,
        warmup_steps=200,
        weight_decay=0.01,
        logging_dir=f"{output_dir}/logs",
        save_strategy="epoch",
        eval_strategy="no",
        load_best_model_at_end=False,
        dataloader_pin_memory=False,
        fp16=False,
        disable_tqdm=False,
        logging_steps=5,
        save_total_limit=2,
        seed=42,
    )

    # Create trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_dataset,
        tokenizer=tokenizer,
    )

    # Clear cache before training
    if torch.backends.mps.is_available():
        torch.mps.empty_cache()

    # Train the model with time tracking
    print("------------------ start training ------------------")
    start_time = datetime.now()

    with tqdm(total=training_args.num_train_epochs, desc="Training Progress", unit="epoch") as pbar:

        class TqdmCallback(TrainerCallback):
            def on_epoch_end(self, args, state, control, **kwargs):
                elapsed = datetime.now() - start_time
                pbar.set_postfix(
                    {
                        "Elapsed": str(elapsed).split(".")[0],
                        "Epoch": f"{state.epoch:.0f}/{args.num_train_epochs}",
                    }
                )
                pbar.update(1)

        trainer.add_callback(TqdmCallback())
        trainer.train()

    total_time = datetime.now() - start_time
    print(f"------------------ finished train (Total time: {total_time}) ------------------")

    # Clear cache after training
    if torch.backends.mps.is_available():
        torch.mps.empty_cache()

    # Save the model
    trainer.save_model(output_dir)
    tokenizer.save_pretrained(output_dir)

    return output_dir
