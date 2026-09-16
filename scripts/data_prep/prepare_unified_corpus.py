"""Prepares a balanced unified training corpus across all CS subjects: DBMS, DSA, OOPS, OS, CNT, and OOSE."""

import os
import json
import random

# Resolve repository root dynamically
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

def main() -> None:
    corpus_dir = os.path.join(REPO_ROOT, "data", "corpus")
    output_file = os.path.join(corpus_dir, "unified_all_subjects_training.jsonl")

    subject_files = {
        "DBMS": os.path.join(corpus_dir, "training.jsonl"),
        "DSA": os.path.join(corpus_dir, "ds_training.jsonl"),
        "OOPS": os.path.join(corpus_dir, "oops_training.jsonl"),
        "OS": os.path.join(corpus_dir, "os_training.jsonl"),
        "CNT": os.path.join(corpus_dir, "cnt_training.jsonl"),
        "OOSE": os.path.join(corpus_dir, "oose_training.jsonl"),
    }

    unified_samples = []
    sample_counts = {}

    for subject, file_path in subject_files.items():
        if not os.path.exists(file_path):
            print(f"Notice: File for {subject} not found at {file_path} (skipping)")
            continue

        count = 0
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    # Standardize subject metadata tag
                    if isinstance(data, dict):
                        if "subject" not in data:
                            data["subject"] = subject
                        if "metadata" in data and isinstance(data["metadata"], dict):
                            data["metadata"]["subject"] = subject
                        unified_samples.append(data)
                        count += 1
                except json.JSONDecodeError:
                    continue

        sample_counts[subject] = count
        print(f"Loaded {count:,} samples for {subject}")

    # Shuffle combined dataset deterministically for balanced multi-task training
    random.seed(42)
    random.shuffle(unified_samples)

    with open(output_file, "w", encoding="utf-8") as out_f:
        for sample in unified_samples:
            out_f.write(json.dumps(sample, ensure_ascii=False) + "\n")

    total_samples = len(unified_samples)
    file_size_mb = os.path.getsize(output_file) / (1024 * 1024) if os.path.exists(output_file) else 0.0

    print("=" * 60)
    print("UNIFIED MULTI-SUBJECT CORPUS PREPARATION COMPLETE")
    print("=" * 60)
    print(f"Total Unified Samples: {total_samples:,}")
    print(f"Corpus File Location:  {output_file}")
    print(f"File Size:             {file_size_mb:.2f} MB")
    print("Breakdown per Subject:")
    for subj, cnt in sample_counts.items():
        print(f"  - {subj:6s}: {cnt:,} samples")
    print("=" * 60)

if __name__ == "__main__":
    main()

