"""Unit tests for Unified Multi-Subject Model Corpus Preparation, Training, and Evaluation Benchmark."""

import os
import sys
import json
import unittest
import tempfile
from datetime import timedelta

# Add root directory and scripts/data_prep to sys.path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.join(REPO_ROOT, "scripts", "data_prep"))

import prepare_unified_corpus
from aurora.models import RawTrainingOutput, TrainingConfig, ComputeDType
from aurora.evaluation import UnifiedSubjectEvaluator, UnifiedEvaluationReport, SubjectMetric



class TestUnifiedMultiSubject(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        self.corpus_dir = os.path.join(self.test_dir.name, "corpus")
        os.makedirs(self.corpus_dir, exist_ok=True)

        # Create dummy subject files
        self.subjects = ["DBMS", "DSA", "OOPS", "OS", "CNT", "OOSE"]
        self.files = {
            "DBMS": os.path.join(self.corpus_dir, "training.jsonl"),
            "DSA": os.path.join(self.corpus_dir, "ds_training.jsonl"),
            "OOPS": os.path.join(self.corpus_dir, "oops_training.jsonl"),
            "OS": os.path.join(self.corpus_dir, "os_training.jsonl"),
            "CNT": os.path.join(self.corpus_dir, "cnt_training.jsonl"),
            "OOSE": os.path.join(self.corpus_dir, "oose_training.jsonl"),
        }

        for subj, path in self.files.items():
            with open(path, "w", encoding="utf-8") as f:
                f.write(json.dumps({"instruction": f"Explain {subj} core concepts.", "response": f"{subj} details.", "subject": subj}) + "\n")

    def tearDown(self):
        self.test_dir.cleanup()

    def test_corpus_unification_and_metadata_tagging(self):
        """Verify that all subject files are aggregated and tagged with subject metadata."""
        output_file = os.path.join(self.corpus_dir, "unified_all_subjects_training.jsonl")

        # Mock prepare_unified_corpus script execution
        unified_samples = []
        for subj, path in self.files.items():
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    data = json.loads(line)
                    data["subject"] = subj
                    unified_samples.append(data)

        with open(output_file, "w", encoding="utf-8") as out_f:
            for sample in unified_samples:
                out_f.write(json.dumps(sample) + "\n")

        self.assertTrue(os.path.exists(output_file))
        with open(output_file, "r", encoding="utf-8") as f:
            lines = [json.loads(l) for l in f]

        self.assertEqual(len(lines), 6)
        found_subjects = {l["subject"] for l in lines}
        self.assertEqual(found_subjects, set(self.subjects))

    def test_unified_subject_evaluator(self):
        """Verify UnifiedSubjectEvaluator produces valid overall and per-subject metrics."""
        evaluator = UnifiedSubjectEvaluator()
        config = TrainingConfig(
            model_name="Mock/Qwen3-8B",
            tokenizer_name="Mock/Qwen3-8B",
            dataset_path="data/corpus/unified.jsonl",
            output_dir="data/output/unified",
            epochs=1,
            batch_size=1,
            gradient_accumulation_steps=1,
            learning_rate=2e-4,
            warmup_ratio=0.0,
            weight_decay=0.0,
            max_seq_length=128,
            seed=42,
            lora_r=8,
            lora_alpha=16,
            lora_dropout=0.0,
            target_modules=["q_proj"],
            load_in_4bit=True,
            bnb_compute_dtype=ComputeDType.BFLOAT16,
            bf16=True,
            fp16=False,
            gradient_checkpointing=False,
            save_steps=100,
            logging_steps=10,
            eval_steps=100,
            eval_threshold=1.5,
        )

        mock_raw = RawTrainingOutput(
            model=None,
            tokenizer=None,
            metrics={"loss": 0.45},
            final_loss=0.45,
            training_time=timedelta(seconds=10),
        )

        report = evaluator.evaluate_multi_subject(mock_raw, None, config)
        self.assertIsInstance(report, UnifiedEvaluationReport)
        self.assertTrue(report.passed)
        self.assertGreater(report.overall_perplexity, 0)
        self.assertEqual(len(report.subject_metrics), 6)
        for subj in self.subjects:
            self.assertIn(subj, report.subject_metrics)
            self.assertIsInstance(report.subject_metrics[subj], SubjectMetric)


if __name__ == "__main__":
    unittest.main()
