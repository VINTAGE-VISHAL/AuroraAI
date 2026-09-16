import os
import sys
import json
import unittest
from fastapi.testclient import TestClient

# Append project root to path
sys.path.append("c:/AuroraEngine/src")
from aurora.deployment.api_server import app

class TestAPIServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # We can use the TestClient to mock API requests
        cls.client = TestClient(app)

    def test_get_models(self):
        """Verify that GET /v1/models returns the expected models listing."""
        response = self.client.get("/v1/models")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertEqual(data["object"], "list")
        self.assertTrue("data" in data)
        
        model_ids = [m["id"] for m in data["data"]]
        self.assertIn("aurora-unified", model_ids)
        self.assertIn("qwen3-vanilla", model_ids)

    def test_chat_completions_non_streaming(self):
        """Verify that POST /v1/chat/completions returns correct JSON for non-streaming queries."""
        payload = {
            "model": "qwen3-vanilla",
            "messages": [
                {"role": "user", "content": "What is DBMS?"}
            ],
            "temperature": 0.7,
            "top_p": 0.8,
            "stream": False,
            "max_tokens": 100
        }
        
        # Test request
        response = self.client.post("/v1/chat/completions", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertTrue(data["id"].startswith("chatcmpl-"))
        self.assertEqual(data["object"], "chat.completion")
        self.assertEqual(data["model"], "qwen3-vanilla")
        self.assertTrue(len(data["choices"]) > 0)
        self.assertEqual(data["choices"][0]["message"]["role"], "assistant")
        self.assertTrue(len(data["choices"][0]["message"]["content"]) > 0)

    def test_chat_completions_streaming(self):
        """Verify that POST /v1/chat/completions returns valid SSE stream chunks and terminates correctly."""
        payload = {
            "model": "qwen3-vanilla",
            "messages": [
                {"role": "user", "content": "Explain DBMS advantages."}
            ],
            "temperature": 0.7,
            "top_p": 0.8,
            "stream": True,
            "max_tokens": 100
        }
        
        # Test request
        response = self.client.post("/v1/chat/completions", json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "text/event-stream; charset=utf-8")
        
        # Parse event stream lines
        lines = response.text.split("\n")
        chunks = []
        has_done = False
        
        for line in lines:
            if line.startswith("data: "):
                data_str = line[6:].strip()
                if data_str == "[DONE]":
                    has_done = True
                    break
                
                chunk_json = json.loads(data_str)
                self.assertEqual(chunk_json["object"], "chat.completion.chunk")
                self.assertEqual(chunk_json["model"], "qwen3-vanilla")
                delta = chunk_json["choices"][0]["delta"]
                
                if "content" in delta:
                    chunks.append(delta["content"])
        
        # Verify content was streamed and session terminated naturally
        self.assertTrue(len(chunks) > 0)
        self.assertTrue(has_done, "SSE stream did not terminate with [DONE]")

    def test_chat_completions_multi_turn_and_isolation(self):
        """Verify sequential multi-turn request isolation and history preservation."""
        # Request 1
        payload1 = {
            "model": "aurora-unified",
            "messages": [
                {"role": "user", "content": "What is DBMS?"}
            ],
            "temperature": 0.0,  # Greedy to be deterministic
            "stream": False,
            "max_tokens": 50
        }
        response1 = self.client.post("/v1/chat/completions", json=payload1)
        self.assertEqual(response1.status_code, 200)
        ans1 = response1.json()["choices"][0]["message"]["content"]
        
        # Request 2 (Multi-turn follow-up)
        payload2 = {
            "model": "aurora-unified",
            "messages": [
                {"role": "user", "content": "What is DBMS?"},
                {"role": "assistant", "content": ans1},
                {"role": "user", "content": "What is the difference between a DBMS and other software systems?"}
            ],
            "temperature": 0.0,
            "stream": False,
            "max_tokens": 100
        }
        response2 = self.client.post("/v1/chat/completions", json=payload2)
        self.assertEqual(response2.status_code, 200)
        ans2 = response2.json()["choices"][0]["message"]["content"]
        
        # Ensure we got different and valid responses
        self.assertTrue(len(ans2) > 0)
        self.assertNotEqual(ans1, ans2)


if __name__ == "__main__":
    unittest.main()
