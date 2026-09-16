import json
import os
import sys

def main():
    dataset_path = "data/corpus/reasoning_experiment_20.jsonl"
    print(f"=================================================")
    print(f"VERIFYING DATASET: {dataset_path}")
    print(f"=================================================")

    if not os.path.exists(dataset_path):
        print(f"ERROR: Dataset file '{dataset_path}' does not exist on disk.")
        sys.exit(1)

    questions = set()
    total_samples = 0
    errors = 0

    with open(dataset_path, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            total_samples += 1
            
            # 1. Valid JSON
            try:
                sample = json.loads(line)
            except Exception as e:
                print(f"Line {idx+1}: ERROR - Invalid JSON syntax: {e}")
                errors += 1
                continue

            # 2. Schema Key check
            if "sample_id" not in sample or "sequence_number" not in sample or "payload" not in sample:
                print(f"Line {idx+1}: ERROR - Missing required SerializedSample root keys.")
                errors += 1
                continue

            payload = sample["payload"]
            if "messages" not in payload:
                print(f"Line {idx+1}: ERROR - Missing 'messages' key inside payload.")
                errors += 1
                continue
            
            messages = payload["messages"]
            # Exclude system prompt when looking for user/assistant roles
            user_msg = next((msg for msg in messages if msg.get("role") == "user"), None)
            assistant_msg = next((msg for msg in messages if msg.get("role") == "assistant"), None)

            if not user_msg or "content" not in user_msg:
                print(f"Line {idx+1}: ERROR - Missing 'user' message or 'content'.")
                errors += 1
                continue

            if not assistant_msg or "content" not in assistant_msg:
                print(f"Line {idx+1}: ERROR - Missing 'assistant' message or 'content'.")
                errors += 1
                continue

            question_text = user_msg["content"]
            answer_text = assistant_msg["content"]

            # 3. No Duplicate Questions
            if question_text in questions:
                print(f"Line {idx+1}: ERROR - Duplicate question detected.")
                errors += 1
            else:
                questions.add(question_text)

            # 4. Reasoning Section is Present
            if "Step-by-step reasoning:" not in answer_text:
                print(f"Line {idx+1}: ERROR - Missing 'Step-by-step reasoning:' section in assistant response.")
                errors += 1

            # 5. Answer Length exceeds threshold (150 chars)
            if len(answer_text) < 150:
                print(f"Line {idx+1}: ERROR - Answer length too short ({len(answer_text)} chars, expected >= 150).")
                errors += 1

    print(f"\nSummary of Validation:")
    print(f"  Total Samples Inspected : {total_samples}")
    print(f"  Total Errors Detected  : {errors}")
    print(f"=================================================")

    if errors > 0:
        print("RESULT: VALIDATION FAILED")
        sys.exit(1)
    else:
        print("RESULT: VALIDATION PASSED (Dataset is 100% compliant)")
        sys.exit(0)

if __name__ == "__main__":
    main()
