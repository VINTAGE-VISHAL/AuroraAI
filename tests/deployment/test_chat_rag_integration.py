"""Comprehensive automated tests for Module 08: Chat API Integration with RAG.

Covers:
1. Existing non-RAG chat request compatibility (streaming and non-streaming)
2. RAG-enabled request with relevant indexed document chunks
3. Verification that assembled grounded prompt reaches the real generation call
4. Streaming response format (SSE chunks) compatibility
5. Non-streaming response format compatibility
6. Conversation isolation (conv_A cannot retrieve from conv_B)
7. File ownership validation (file must belong to specified conversation_id)
8. Missing or unindexed file handling (clear HTTP error returned)
9. Empty retrieval results handling (graceful prompt instructing not to invent answers)
10. Preservation of existing system prompts and conversation history
11. Rejection when file_id provided without conversation_id
"""

import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from aurora.deployment.api_server import app, engine, file_service
from aurora.models.inference import GenerationResult


@pytest.fixture
def client():
    return TestClient(app)


# =========================================================================
# 1. Non-RAG Backward Compatibility Tests
# =========================================================================

def test_non_rag_chat_completions_non_streaming(client):
    """Verify standard non-RAG request works exactly as before."""
    mock_gen_result = GenerationResult(
        answer="A process is an instance of a computer program being executed.",
        generation_time=0.2,
        tokens_generated=15,
        tokens_per_second=75.0,
        base_load_time=0.0,
        adapter_load_time=0.0,
    )

    with patch.object(engine, "generate", return_value=mock_gen_result) as mock_generate:
        payload = {
            "model": "aurora-os",
            "messages": [{"role": "user", "content": "What is a process?"}],
            "stream": False,
        }
        res = client.post("/v1/chat/completions", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["object"] == "chat.completion"
        assert data["choices"][0]["message"]["content"] == mock_gen_result.answer

        # Verify engine.generate was called with prompt containing base AURORA_SYSTEM_PROMPT and without reference context
        mock_generate.assert_called_once()
        called_prompt = mock_generate.call_args.kwargs["prompt"]
        assert any("You are Aurora Engine" in m["content"] for m in called_prompt)
        assert not any("<reference_context>" in m["content"] for m in called_prompt)


def test_non_rag_chat_completions_streaming(client):
    """Verify standard non-RAG streaming request streams SSE chunks as before."""
    mock_chunks = ["A process ", "is an executing ", "program."]

    with patch.object(engine, "generate_stream", return_value=iter(mock_chunks)) as mock_stream:
        payload = {
            "model": "aurora-os",
            "messages": [{"role": "user", "content": "What is a process?"}],
            "stream": True,
        }
        res = client.post("/v1/chat/completions", json=payload)
        assert res.status_code == 200
        assert "text/event-stream" in res.headers["content-type"]

        lines = res.text.strip().split("\n\n")
        assert len(lines) >= 3  # initial role, tokens, stop, [DONE]

        # Verify stream generator received non-RAG prompt
        mock_stream.assert_called_once()
        called_prompt = mock_stream.call_args.kwargs["prompt"]
        assert not any("<reference_context>" in m["content"] for m in called_prompt)


# =========================================================================
# 2. RAG Chat Integration Tests
# =========================================================================

def test_rag_chat_completions_with_indexed_document(client):
    """Verify that uploading + indexing a file allows RAG grounded prompt to reach engine.generate."""
    conv_id = "test_conv_rag_flow"

    # 1. Upload a file
    doc_text = "Virtual memory in AuroraOS uses inverted page tables with TLB caching."
    upload_res = client.post(
        "/v1/files/upload",
        data={"conversation_id": conv_id},
        files={"file": ("virtual_memory.txt", doc_text.encode("utf-8"), "text/plain")},
    )
    assert upload_res.status_code == 200
    file_id = upload_res.json()["file_id"]

    try:
        # 2. Index file
        idx_res = client.post(f"/v1/files/{file_id}/index", params={"conversation_id": conv_id})
        assert idx_res.status_code == 200

        # 3. Chat with conversation_id and file_id
        mock_gen_result = GenerationResult(
            answer="According to [Source 1], AuroraOS uses inverted page tables.",
            generation_time=0.1,
            tokens_generated=10,
            tokens_per_second=100.0,
            base_load_time=0.0,
            adapter_load_time=0.0,
        )

        with patch.object(engine, "generate", return_value=mock_gen_result) as mock_generate:
            payload = {
                "model": "aurora-os",
                "conversation_id": conv_id,
                "file_id": file_id,
                "messages": [
                    {"role": "user", "content": "How does virtual memory work in AuroraOS?"}
                ],
                "stream": False,
            }
            res = client.post("/v1/chat/completions", json=payload)
            assert res.status_code == 200
            data = res.json()
            assert data["choices"][0]["message"]["content"] == mock_gen_result.answer

            # 4. Verify grounded prompt with reference context reached engine.generate
            mock_generate.assert_called_once()
            called_prompt = mock_generate.call_args.kwargs["prompt"]
            system_msg = next(m["content"] for m in called_prompt if m["role"] == "system")
            assert "<reference_context>" in system_msg
            assert "inverted page tables" in system_msg
            assert "[Source 1]" in system_msg
            assert "virtual_memory.txt" in system_msg
            assert "DOCUMENT GROUNDING & SAFETY INSTRUCTIONS" in system_msg

    finally:
        client.delete(f"/v1/files/{file_id}", params={"conversation_id": conv_id})


def test_rag_chat_completions_streaming(client):
    """Verify RAG streaming request streams tokens and passes grounded prompt to generate_stream."""
    conv_id = "test_conv_rag_stream"

    # 1. Upload & Index
    doc_text = "TCP guarantees delivery via sequence numbers and ACK packets."
    upload_res = client.post(
        "/v1/files/upload",
        data={"conversation_id": conv_id},
        files={"file": ("tcp_notes.txt", doc_text.encode("utf-8"), "text/plain")},
    )
    assert upload_res.status_code == 200
    file_id = upload_res.json()["file_id"]

    try:
        idx_res = client.post(f"/v1/files/{file_id}/index", params={"conversation_id": conv_id})
        assert idx_res.status_code == 200

        mock_stream_tokens = ["TCP ", "uses ", "ACK packets."]

        with patch.object(engine, "generate_stream", return_value=iter(mock_stream_tokens)) as mock_stream:
            payload = {
                "model": "aurora-cnt",
                "conversation_id": conv_id,
                "file_ids": [file_id],
                "messages": [
                    {"role": "user", "content": "How does TCP guarantee delivery?"}
                ],
                "stream": True,
            }
            res = client.post("/v1/chat/completions", json=payload)
            assert res.status_code == 200
            assert "text/event-stream" in res.headers["content-type"]

            # Verify generate_stream received the grounded prompt
            mock_stream.assert_called_once()
            called_prompt = mock_stream.call_args.kwargs["prompt"]
            system_msg = next(m["content"] for m in called_prompt if m["role"] == "system")
            assert "<reference_context>" in system_msg
            assert "sequence numbers and ACK packets" in system_msg

    finally:
        client.delete(f"/v1/files/{file_id}", params={"conversation_id": conv_id})


# =========================================================================
# 3. Validation, Isolation & Error Handling Tests
# =========================================================================

def test_rag_missing_conversation_id_when_files_provided(client):
    """If file_id or file_ids is provided without conversation_id, reject with 400."""
    payload = {
        "model": "aurora-unified",
        "file_id": "file_xyz123",
        "messages": [{"role": "user", "content": "Query"}],
    }
    res = client.post("/v1/chat/completions", json=payload)
    assert res.status_code == 400
    assert "conversation_id is required" in res.json()["detail"]


def test_rag_unauthorized_or_non_existent_file(client):
    """Referencing a file not in the conversation must return 404."""
    payload = {
        "model": "aurora-unified",
        "conversation_id": "conv_user_real",
        "file_id": "file_non_existent",
        "messages": [{"role": "user", "content": "Query"}],
    }
    res = client.post("/v1/chat/completions", json=payload)
    assert res.status_code == 404
    assert "was not found in conversation" in res.json()["detail"]


def test_rag_conversation_isolation(client):
    """File uploaded in conv_A cannot be accessed from conv_B."""
    # 1. Upload file in conv_A
    upload_res = client.post(
        "/v1/files/upload",
        data={"conversation_id": "conv_A"},
        files={"file": ("secret.txt", b"Secret text in conv A", "text/plain")},
    )
    assert upload_res.status_code == 200
    file_id = upload_res.json()["file_id"]

    try:
        # 2. Try to query that file_id using conv_B
        payload = {
            "model": "aurora-unified",
            "conversation_id": "conv_B",
            "file_id": file_id,
            "messages": [{"role": "user", "content": "What is the secret?"}],
        }
        res = client.post("/v1/chat/completions", json=payload)
        assert res.status_code == 404
        assert "was not found in conversation 'conv_B'" in res.json()["detail"]
    finally:
        client.delete(f"/v1/files/{file_id}", params={"conversation_id": "conv_A"})


def test_rag_unindexed_file_rejected(client):
    """If file is uploaded but not indexed into vector store, reject with clear 400 error."""
    conv_id = "conv_unindexed"
    upload_res = client.post(
        "/v1/files/upload",
        data={"conversation_id": conv_id},
        files={"file": ("notes.txt", b"Raw unindexed text", "text/plain")},
    )
    assert upload_res.status_code == 200
    file_id = upload_res.json()["file_id"]

    try:
        payload = {
            "model": "aurora-unified",
            "conversation_id": conv_id,
            "file_id": file_id,
            "messages": [{"role": "user", "content": "Explain notes"}],
        }
        res = client.post("/v1/chat/completions", json=payload)
        assert res.status_code == 400
        assert "has not been indexed yet" in res.json()["detail"]
    finally:
        client.delete(f"/v1/files/{file_id}", params={"conversation_id": conv_id})


def test_rag_conversation_without_files_empty_results(client):
    """If conversation_id provided on an empty conversation, grounding prompt instructs no relevant sections."""
    mock_gen_result = GenerationResult(
        answer="The uploaded documents do not contain sufficient information.",
        generation_time=0.1,
        tokens_generated=8,
        tokens_per_second=80.0,
        base_load_time=0.0,
        adapter_load_time=0.0,
    )

    with patch.object(engine, "generate", return_value=mock_gen_result) as mock_generate:
        payload = {
            "model": "aurora-os",
            "conversation_id": "conv_completely_empty",
            "messages": [{"role": "user", "content": "What is in the document?"}],
            "stream": False,
        }
        res = client.post("/v1/chat/completions", json=payload)
        assert res.status_code == 200

        mock_generate.assert_called_once()
        called_prompt = mock_generate.call_args.kwargs["prompt"]
        system_msg = next(m["content"] for m in called_prompt if m["role"] == "system")
        assert "[No relevant document sections found for this query.]" in system_msg


def test_rag_citations_in_response(client):
    """Verify that retrieved document chunks produce citation metadata in non-streaming and streaming responses."""
    conv_id = "test_conv_citations"

    doc_text = "Page replacement algorithms include LRU, FIFO, and Optimal (Belady's anomaly)."
    upload_res = client.post(
        "/v1/files/upload",
        data={"conversation_id": conv_id},
        files={"file": ("page_replacement.txt", doc_text.encode("utf-8"), "text/plain")},
    )
    assert upload_res.status_code == 200
    file_id = upload_res.json()["file_id"]

    try:
        idx_res = client.post(f"/v1/files/{file_id}/index", params={"conversation_id": conv_id})
        assert idx_res.status_code == 200

        mock_gen_result = GenerationResult(
            answer="Belady's anomaly occurs in FIFO page replacement.",
            generation_time=0.1,
            tokens_generated=8,
            tokens_per_second=80.0,
            base_load_time=0.0,
            adapter_load_time=0.0,
        )

        # 1. Non-streaming citations check
        with patch.object(engine, "generate", return_value=mock_gen_result):
            res = client.post(
                "/v1/chat/completions",
                json={
                    "model": "aurora-os",
                    "conversation_id": conv_id,
                    "file_id": file_id,
                    "messages": [{"role": "user", "content": "What is Belady's anomaly?"}],
                    "stream": False,
                },
            )
            assert res.status_code == 200
            data = res.json()
            assert "citations" in data
            assert len(data["citations"]) > 0
            first_cit = data["citations"][0]
            assert first_cit["filename"] == "page_replacement.txt"
            assert first_cit["file_id"] == file_id
            assert "relevance_score" in first_cit
            assert "label" in first_cit

        # 2. Streaming citations check (final chunk contains citations)
        with patch.object(engine, "generate_stream", return_value=iter(["Belady ", "anomaly."])):
            res = client.post(
                "/v1/chat/completions",
                json={
                    "model": "aurora-os",
                    "conversation_id": conv_id,
                    "file_id": file_id,
                    "messages": [{"role": "user", "content": "What is Belady's anomaly?"}],
                    "stream": True,
                },
            )
            assert res.status_code == 200
            chunks = []
            for block in res.text.strip().split("\n\n"):
                if block.startswith("data: ") and not block.endswith("[DONE]"):
                    chunks.append(json.loads(block.replace("data: ", "")))

            # Find the chunk with citations
            citation_chunks = [c for c in chunks if "citations" in c or "citations" in c.get("choices", [{}])[0]]
            assert len(citation_chunks) > 0
            found_cit = citation_chunks[0].get("citations") or citation_chunks[0]["choices"][0]["citations"]
            assert found_cit[0]["filename"] == "page_replacement.txt"

    finally:
        client.delete(f"/v1/files/{file_id}", params={"conversation_id": conv_id})

