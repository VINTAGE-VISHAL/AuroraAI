import os
import sys
import torch
import unittest
from peft import PeftModel

# Append project root to path
sys.path.append("c:/AuroraEngine/src")
from aurora.inference.loader import ModelLoader
from aurora.inference.adapter_manager import AdapterManager
from aurora.inference.generator import Generator
from aurora.inference.inference_engine import InferenceEngine

class TestAdapterLifecycle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base_model_name = "Qwen/Qwen3-8B"
        cls.adapter_path = "C:/AuroraEngine/data/output/stage1_smoke_test_reasoning_v2/final_adapter"
        
        cls.loader = ModelLoader()
        cls.manager = AdapterManager()
        cls.generator = Generator()
        cls.engine = InferenceEngine(cls.loader, cls.manager, cls.generator)
        cls.engine.initialize(cls.base_model_name)

    def test_lora_toggling_lifecycle(self):
        """Verify that LoRA toggling lifecycle runs Stage 1 (enabled) and Stage 2 (disabled) correctly."""
        model, tokenizer = self.loader.get_loaded()
        
        # 1. Wrap model in PeftModel
        peft_model = self.manager.set_adapter(model, self.adapter_path)
        self.assertTrue(isinstance(peft_model, PeftModel))

        # Capture a hash of base model weights to verify immutability
        base_weights_hash = hash(next(peft_model.get_base_model().parameters()).sum().item())

        # 2. Run Stage 1 with LoRA Enabled
        print("\n--- Running Stage 1 Specialist Query ---")
        prompt = "What is DBMS?"
        specialist_res = self.generator.generate(
            model=peft_model,
            tokenizer=tokenizer,
            prompt=prompt,
            temperature=0.7,
            max_new_tokens=80,
            top_p=0.8
        )
        self.assertTrue(len(specialist_res.answer) > 0)
        print("Specialist Answer:", specialist_res.answer)

        # 3. Run Stage 2 with LoRA Disabled
        print("\n--- Running Stage 2 Vanilla Query ---")
        augmented_prompt = f"{prompt}\n\nSpecialist Context:\n{specialist_res.answer.strip()}"
        with peft_model.disable_adapter():
            vanilla_res = self.generator.generate(
                model=peft_model,
                tokenizer=tokenizer,
                prompt=augmented_prompt,
                temperature=0.7,
                max_new_tokens=256,
                top_p=0.8
            )
        print("Vanilla Answer:", vanilla_res.answer)

        # 4. Verify base model remains completely unchanged
        current_weights_hash = hash(next(peft_model.get_base_model().parameters()).sum().item())
        self.assertEqual(base_weights_hash, current_weights_hash, "Base model weights were contaminated/merged!")

    def test_session_isolation_and_no_leakage(self):
        """Verify that old context (like PL/pgSQL) from previous runs does not leak into subsequent fresh requests."""
        model, tokenizer = self.loader.get_loaded()
        peft_model = self.manager.set_adapter(model, self.adapter_path)

        # Session 1: PL/pgSQL Request
        print("\n--- Session 1: PL/pgSQL Request ---")
        plpgsql_prompt = "Write a loop in PL/pgSQL code."
        res1 = self.engine.generate(
            prompt=plpgsql_prompt,
            adapter_path=self.adapter_path,
            temperature=0.7,
            max_new_tokens=256,
            top_p=0.8
        )
        self.assertTrue("PL/pgSQL" in res1.answer or "loop" in res1.answer)

        # Session 2: Fresh "What is DBMS?" Request
        print("\n--- Session 2: Fresh DBMS Request ---")
        dbms_prompt = "What is DBMS?"
        res2 = self.engine.generate(
            prompt=dbms_prompt,
            adapter_path=self.adapter_path,
            temperature=0.7,
            max_new_tokens=256,
            top_p=0.8
        )
        
        # Verify no PL/pgSQL context leaked into the fresh DBMS request
        self.assertFalse("PL/pgSQL" in res2.answer, "Contamination detected: PL/pgSQL leaked into DBMS request!")
        self.assertFalse("loop" in res2.answer, "Contamination detected: PL/pgSQL loop details leaked!")

if __name__ == "__main__":
    unittest.main()
