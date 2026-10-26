import os
import sys
import json
import time
import uuid
import asyncio
import threading
from pathlib import Path
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, Request, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

# Append project root src to path
current_file_dir = Path(__file__).resolve().parent
project_root = current_file_dir.parent.parent.parent
src_dir = project_root / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from aurora.config.loader import load_settings
from aurora.core.exceptions import (
    ContextFusionError,
    CorruptedDocumentError,
    EmbeddingError,
    ExtractionError,
    FileTooLargeError,
    FileValidationError,
    InvalidChunkingConfigError,
    InvalidContextBudgetError,
    InvalidTopKError,
    MalformedVectorError,
    RetrievalError,
    RuntimeFileNotFoundError,
    StorageOperationError,
    UnsupportedFileTypeError,
    VectorDimensionMismatchError,
    VectorStoreError,
)
from aurora.models.runtime_chunk import ChunkingConfig



from aurora.ingestion.runtime.file_validator import RuntimeFileValidator
from aurora.ingestion.runtime.file_storage import RuntimeFileStorage
from aurora.services.file_service import FileService
from aurora.storage.context_fusion import DEFAULT_GROUNDING_INSTRUCTIONS
from aurora.inference.loader import ModelLoader
from aurora.inference.adapter_manager import AdapterManager
from aurora.inference.generator import Generator
from aurora.inference.inference_engine import InferenceEngine
from aurora.inference.stt_service import FasterWhisperSTTService

app = FastAPI(title="Aurora Engine API Server", version="1.0.0")


# Enable CORS for frontend flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances of the inference subsystem
loader = ModelLoader()
manager = AdapterManager()
generator = Generator()
engine = InferenceEngine(loader, manager, generator)
stt_service = FasterWhisperSTTService()

# Load base model on startup
BASE_MODEL_NAME = "Qwen/Qwen3-8B"

ADAPTER_MAP = {
    "aurora-unified": "C:/AuroraEngine/data/output/unified_adapter/final_adapter",
    "aurora-dbms": "C:/AuroraEngine/data/output/stage1_smoke_test/final_adapter",
    "aurora-dsa": "C:/AuroraEngine/data/output/dsa_adapter/final_adapter",
    "aurora-oops": "C:/AuroraEngine/data/output/oops_adapter/final_adapter",
    "aurora-os": "C:/AuroraEngine/data/output/os_adapter/final_adapter",
    "aurora-cnt": "C:/AuroraEngine/data/output/cnt_adapter/final_adapter",
    "aurora-oose": "C:/AuroraEngine/data/output/oose_adapter/final_adapter",
    "qwen3-vanilla": "",
}

def resolve_adapter_path(model_id: str, messages: list) -> str:
    """Resolves adapter path based on selected model or defaults to unified multi-subject adapter."""
    if model_id in ADAPTER_MAP and ADAPTER_MAP[model_id] != "AUTO_ROUTING":
        return ADAPTER_MAP[model_id]
    
    # Fallback to single unified multi-subject adapter
    return "C:/AuroraEngine/data/output/unified_adapter/final_adapter"

AURORA_SYSTEM_PROMPT = (
    "You are Aurora Engine, a research-grade educational AI framework specialized strictly in Computer Science subject curricula:\n"
    "1. Database Management Systems (DBMS)\n"
    "2. Data Structures & Algorithms (DSA)\n"
    "3. Object-Oriented Programming Systems (OOPS)\n"
    "4. Operating Systems (OS)\n"
    "5. Computer Networks (CNT)\n"
    "6. Software Engineering (OOSE)\n\n"
    "CRITICAL CURRICULUM CONSTRAINTS:\n"
    "1. You must ONLY answer questions directly related to these Computer Science subject domains.\n"
    "2. If the user asks a question, prompt, or request that does NOT belong to these 6 Computer Science subject domains "
    "(for example: cooking, recipes, general trivia, entertainment, sports, non-CS academic topics, personal advice, casual chit-chat, etc.), "
    "you MUST politely decline to answer and respond with this exact note:\n"
    "\"I am specialized exclusively in Computer Science curriculum domains (DBMS, DSA, OOPS, OS, CNT, and OOSE). This query does not fall within our supported educational subjects.\""
)

@app.on_event("startup")
def startup_event():
    print(f"Initializing Aurora Engine with base model: {BASE_MODEL_NAME}...")
    engine.initialize(BASE_MODEL_NAME)
    print("Aurora Engine loaded successfully.")
    print("Initializing Faster-Whisper STT Service...")
    stt_service.initialize()

    # Bounded, non-blocking background cleanup of stale runtime files
    if getattr(settings.runtime_storage, "cleanup_enabled", True):
        def run_background_startup_cleanup():
            try:
                # Give server a few seconds to finish boot sequence before running cleanup
                time.sleep(2.0)
                clean_res = file_service.cleanup_stale_files()
                if clean_res.cleaned_files_count > 0:
                    print(f"[Cleanup] Pruned {clean_res.cleaned_files_count} stale runtime files, {clean_res.cleaned_vectors_count} vectors.")
            except Exception as e:
                print(f"[Cleanup] Startup background cleanup notice: {e}")

        threading.Thread(target=run_background_startup_cleanup, daemon=True).start()

@app.post("/v1/speech/transcribe")
@app.post("/api/speech/transcribe")
async def transcribe_speech(file: UploadFile = File(...)):
    """Transcribes uploaded recorded audio file into English text using local Faster-Whisper."""
    if not file:
        raise HTTPException(status_code=400, detail="No audio file provided.")

    try:
        audio_bytes = await file.read()
        if not audio_bytes or len(audio_bytes) < 100:
            return {"text": ""}

        # Determine file extension from filename or content_type
        ext = ".wav"
        if file.filename:
            _, ext_found = os.path.splitext(file.filename)
            if ext_found:
                ext = ext_found.lower()

        transcribed_text = stt_service.transcribe_bytes(audio_bytes, file_extension=ext)
        return {"text": transcribed_text}
    except Exception as e:
        print(f"Speech transcription endpoint error: {e}")
        # Clean user-facing error message without exposing Python stack traces
        raise HTTPException(status_code=500, detail="Speech transcription processing failed.")

# File subsystem initialization

settings = load_settings()
file_validator = RuntimeFileValidator(settings.runtime_storage)
file_storage = RuntimeFileStorage(settings.runtime_storage)
file_service = FileService(file_validator, file_storage)

@app.post("/v1/files/upload")
async def upload_file(
    file: UploadFile = File(...),
    conversation_id: str = Form(...),
):
    """Uploads and validates a runtime conversation-scoped document (.pdf, .docx, .txt, .md)."""
    if not file:
        raise HTTPException(status_code=400, detail="No file provided.")
    if not conversation_id or not conversation_id.strip():
        raise HTTPException(status_code=400, detail="Missing or invalid conversation_id.")

    try:
        content_bytes = await file.read()
        response_dto = file_service.upload_file(
            conversation_id=conversation_id,
            filename=file.filename or "",
            content_type=file.content_type,
            content=content_bytes,
        )
        return response_dto.model_dump()
    except FileTooLargeError as e:
        raise HTTPException(status_code=413, detail=str(e))
    except FileValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except StorageOperationError as e:
        raise HTTPException(status_code=500, detail="Storage processing failure.")
    except Exception as e:
        print(f"File upload unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal file processing error.")

@app.get("/v1/files/{file_id}")
def get_file_metadata(
    file_id: str,
    conversation_id: Optional[str] = Query(None),
):
    """Retrieves metadata for a runtime uploaded file."""
    try:
        response_dto = file_service.get_file(file_id, conversation_id=conversation_id)
        return response_dto.model_dump()
    except RuntimeFileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        print(f"File get metadata error: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving file metadata.")

@app.delete("/v1/files/{file_id}")
def delete_file(
    file_id: str,
    conversation_id: Optional[str] = Query(None),
):
    """Deletes a runtime uploaded file and its metadata."""
    try:
        deleted = file_service.delete_file(file_id, conversation_id=conversation_id)
        if deleted:
            return {"deleted": True, "file_id": file_id}
        raise HTTPException(status_code=404, detail=f"File '{file_id}' was not found.")
    except RuntimeFileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        print(f"File delete error: {e}")
        raise HTTPException(status_code=500, detail="Error deleting file.")

@app.delete("/v1/conversations/{conversation_id}")
def delete_conversation(
    conversation_id: str,
):
    """Deletes all files, metadata, and ChromaDB vector collections for a conversation."""
    if not conversation_id or not conversation_id.strip():
        raise HTTPException(status_code=400, detail="Missing or invalid conversation_id.")

    try:
        deleted = file_service.delete_conversation(conversation_id.strip())
        return {"deleted": deleted, "conversation_id": conversation_id}
    except Exception as e:
        print(f"Conversation delete error: {e}")
        raise HTTPException(status_code=500, detail="Error deleting conversation.")

@app.post("/v1/files/cleanup")
def cleanup_stale_files(
    max_age_hours: Optional[float] = Query(None),
):
    """Safely executes automatic cleanup of genuinely stale/abandoned runtime files."""
    try:
        retention = max_age_hours if max_age_hours is not None else settings.runtime_storage.retention_hours
        result = file_service.cleanup_stale_files(max_age_hours=retention)
        return result.model_dump()
    except Exception as e:
        print(f"Automatic cleanup error: {e}")
        raise HTTPException(status_code=500, detail="Cleanup operation failed.")

@app.post("/v1/files/{file_id}/extract")
def extract_file_content(
    file_id: str,
    conversation_id: Optional[str] = Query(None),
):
    """Triggers runtime text extraction for an uploaded document."""
    try:
        response_dto = file_service.extract_file(file_id, conversation_id=conversation_id)
        return response_dto.model_dump()
    except RuntimeFileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except UnsupportedFileTypeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except (ExtractionError, CorruptedDocumentError) as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        print(f"File extraction error: {e}")
        raise HTTPException(status_code=500, detail="Internal file extraction failure.")

@app.post("/v1/files/{file_id}/chunk")
def chunk_file_content(
    file_id: str,
    conversation_id: Optional[str] = Query(None),
    chunk_size: Optional[int] = Query(None),
    chunk_overlap: Optional[int] = Query(None),
):
    """Triggers runtime document text extraction and recursive chunking."""
    try:
        config = None
        if chunk_size is not None or chunk_overlap is not None:
            config = ChunkingConfig(
                chunk_size=chunk_size if chunk_size is not None else 500,
                chunk_overlap=chunk_overlap if chunk_overlap is not None else 50,
            )
        response_dto = file_service.chunk_file(file_id, conversation_id=conversation_id, config=config)
        return response_dto.model_dump()
    except RuntimeFileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except (UnsupportedFileTypeError, InvalidChunkingConfigError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except (ExtractionError, CorruptedDocumentError) as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        print(f"File chunking error: {e}")
        raise HTTPException(status_code=500, detail="Internal file chunking failure.")

@app.post("/v1/files/{file_id}/embed")
def embed_file_content(
    file_id: str,
    conversation_id: Optional[str] = Query(None),
    chunk_size: Optional[int] = Query(None),
    chunk_overlap: Optional[int] = Query(None),
):
    """Triggers runtime extraction, chunking, and dense vector embedding generation."""
    try:
        config = None
        if chunk_size is not None or chunk_overlap is not None:
            config = ChunkingConfig(
                chunk_size=chunk_size if chunk_size is not None else 500,
                chunk_overlap=chunk_overlap if chunk_overlap is not None else 50,
            )
        response_dto = file_service.embed_file(file_id, conversation_id=conversation_id, config=config)
        return response_dto.model_dump()
    except RuntimeFileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except (UnsupportedFileTypeError, InvalidChunkingConfigError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except (ExtractionError, CorruptedDocumentError, EmbeddingError) as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        print(f"File embedding error: {e}")
        raise HTTPException(status_code=500, detail="Internal file embedding failure.")

@app.post("/v1/files/{file_id}/index")
def index_file_content(
    file_id: str,
    conversation_id: Optional[str] = Query(None),
    chunk_size: Optional[int] = Query(None),
    chunk_overlap: Optional[int] = Query(None),
):
    """Triggers the full pipeline: Upload (prior) -> Extract -> Chunk -> Embed -> Store in vector database."""
    try:
        config = None
        if chunk_size is not None or chunk_overlap is not None:
            config = ChunkingConfig(
                chunk_size=chunk_size if chunk_size is not None else 500,
                chunk_overlap=chunk_overlap if chunk_overlap is not None else 50,
            )
        response_dto = file_service.index_file(file_id, conversation_id=conversation_id, config=config)
        return response_dto.model_dump()
    except RuntimeFileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except (UnsupportedFileTypeError, InvalidChunkingConfigError, VectorDimensionMismatchError, MalformedVectorError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except (ExtractionError, CorruptedDocumentError, EmbeddingError, VectorStoreError) as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        print(f"File indexing error: {e}")
        raise HTTPException(status_code=500, detail="Internal file indexing failure.")

@app.post("/v1/retrieval/search")
def retrieve_chunks(
    query: str = Query(..., description="User search query"),
    conversation_id: str = Query(..., description="Conversation isolation identifier"),
    top_k: Optional[int] = Query(None, description="Maximum chunks to retrieve"),
    file_id: Optional[str] = Query(None, description="Optional file filter"),
):
    """Retrieves top-k relevant chunks for a query within a conversation scope."""
    if not query or not query.strip():
        raise HTTPException(status_code=400, detail="Search query cannot be empty.")
    if not conversation_id or not conversation_id.strip():
        raise HTTPException(status_code=400, detail="conversation_id cannot be empty.")

    try:
        result = file_service.retrieve_context(
            query=query,
            conversation_id=conversation_id,
            top_k=top_k,
            file_id=file_id,
        )
        return result.model_dump()
    except InvalidTopKError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except (RetrievalError, VectorStoreError, EmbeddingError) as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        print(f"Retrieval endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal semantic retrieval failure.")

@app.post("/v1/retrieval/context")
def build_context(
    query: str = Query(..., description="User search query"),
    conversation_id: str = Query(..., description="Conversation isolation identifier"),
    top_k: Optional[int] = Query(None, description="Maximum chunks to retrieve"),
    file_id: Optional[str] = Query(None, description="Optional file filter"),
    max_tokens: Optional[int] = Query(None, description="Maximum token budget for context"),
):
    """Retrieves and fuses document chunks into a structured, budget-bounded context."""
    if not query or not query.strip():
        raise HTTPException(status_code=400, detail="Search query cannot be empty.")
    if not conversation_id or not conversation_id.strip():
        raise HTTPException(status_code=400, detail="conversation_id cannot be empty.")

    try:
        fused = file_service.build_rag_context(
            query=query,
            conversation_id=conversation_id,
            top_k=top_k,
            file_id=file_id,
            max_tokens=max_tokens,
        )
        return fused.model_dump()
    except (InvalidTopKError, InvalidContextBudgetError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except (ContextFusionError, RetrievalError, VectorStoreError, EmbeddingError) as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        print(f"Context fusion endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal context fusion failure.")

@app.get("/v1/models")
def get_models():




    """Returns OpenAI-compatible model listing for all trained Aurora domain adapters."""
    models_list = []
    for m_id in ADAPTER_MAP.keys():
        models_list.append({
            "id": m_id,
            "object": "model",
            "created": int(time.time()),
            "owned_by": "aurora"
        })
    return {
        "object": "list",
        "data": models_list
    }

@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    """Processes chat completion requests and streams tokens using OpenAI SSE protocol."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    model_id = body.get("model", "aurora-unified")
    messages = body.get("messages", [])
    temperature = body.get("temperature", 0.7)
    top_p = body.get("top_p", 0.8)
    stream = body.get("stream", False)
    max_tokens = body.get("max_tokens", 3072)

    # Document RAG parameters
    conversation_id = body.get("conversation_id")
    file_id = body.get("file_id")
    file_ids = body.get("file_ids")

    if not messages:
        raise HTTPException(status_code=400, detail="Messages array cannot be empty")

    # Normalize file_ids list if file_id or file_ids provided
    target_file_ids: List[str] = []
    if file_id and isinstance(file_id, str) and file_id.strip():
        target_file_ids.append(file_id.strip())
    if file_ids and isinstance(file_ids, list):
        for fid in file_ids:
            if isinstance(fid, str) and fid.strip() and fid.strip() not in target_file_ids:
                target_file_ids.append(fid.strip())

    # RAG Validation & Context Assembly
    rag_context_text: Optional[str] = None
    rag_citations: List[dict] = []
    if conversation_id and conversation_id.strip():
        conv_id = conversation_id.strip()

        # Validate file ownership if files were explicitly specified
        for fid in target_file_ids:
            meta = file_storage.get_metadata(fid, conversation_id=conv_id)
            if not meta:
                raise HTTPException(
                    status_code=404,
                    detail=f"File '{fid}' was not found in conversation '{conv_id}' or is unauthorized.",
                )

            # Check that file has actually been indexed into the vector store
            indexed_vector_count = file_service.vector_store.count(conv_id, file_id=fid)
            if indexed_vector_count == 0:
                raise HTTPException(
                    status_code=400,
                    detail=f"File '{fid}' has not been indexed yet. Please index the file before querying.",
                )

        # Extract latest user message for retrieval
        latest_user_query = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                latest_user_query = m.get("content", "").strip()
                break

        if latest_user_query:
            try:
                # If target_file_ids has exactly 1 file, pass it as filter; otherwise search conversation
                single_filter = target_file_ids[0] if len(target_file_ids) == 1 else None
                fused = file_service.build_rag_context(
                    query=latest_user_query,
                    conversation_id=conv_id,
                    file_id=single_filter,
                )
                if fused.has_context:
                    rag_context_text = fused.context_text
                    for s in fused.sources:
                        rag_citations.append({
                            "chunk_id": s.chunk_id,
                            "file_id": s.file_id,
                            "filename": s.filename,
                            "source_page": s.source_page,
                            "chunk_index": s.chunk_index,
                            "relevance_score": round(float(s.relevance_score), 4),
                            "label": s.label,
                        })
                else:
                    # Explicit instructions when no relevant document chunks are found
                    rag_context_text = (
                        "<reference_context>\n"
                        "[No relevant document sections found for this query.]\n"
                        "</reference_context>"
                    )
            except Exception as e:
                print(f"RAG retrieval/fusion error: {e}")
                raise HTTPException(status_code=500, detail=f"Document retrieval failed: {e}")
    elif target_file_ids:
        # Client supplied file_ids but omitted conversation_id
        raise HTTPException(
            status_code=400,
            detail="conversation_id is required when file_id or file_ids are provided.",
        )

    # Sanitize input messages (strip out previous error strings or empty turns)
    clean_messages = []
    for m in messages:
        content = m.get("content", "")
        if content and isinstance(content, str) and not content.startswith("[Aurora System Error:") and not content.startswith("[Error:"):
            clean_messages.append(m)

    if not clean_messages:
        clean_messages = messages

    # Determine base system prompt (with RAG grounding if applicable)
    if rag_context_text:
        effective_system_prompt = (
            f"{AURORA_SYSTEM_PROMPT}\n\n"
            f"{DEFAULT_GROUNDING_INSTRUCTIONS}\n\n"
            f"{rag_context_text}"
        )
    else:
        effective_system_prompt = AURORA_SYSTEM_PROMPT

    # Inject system prompt with CS domain constraints (and RAG context)
    formatted_messages = []
    has_system = False
    for m in clean_messages:
        if m.get("role") == "system":
            has_system = True
            formatted_messages.append({
                "role": "system",
                "content": f"{effective_system_prompt}\n\n{m.get('content', '')}"
            })
        else:
            formatted_messages.append(m)

    if not has_system:
        formatted_messages.insert(0, {"role": "system", "content": effective_system_prompt})

    adapter_path = resolve_adapter_path(model_id, formatted_messages)

    # Generate request unique ID
    chat_id = f"chatcmpl-{uuid.uuid4()}"
    created_time = int(time.time())

    if stream:
        queue: asyncio.Queue = asyncio.Queue()
        loop = asyncio.get_running_loop()

        def produce_tokens():
            try:
                stream_generator = engine.generate_stream(
                    prompt=formatted_messages,
                    adapter_path=adapter_path,
                    temperature=temperature,
                    max_new_tokens=max_tokens,
                    top_p=top_p
                )
                for chunk in stream_generator:
                    loop.call_soon_threadsafe(queue.put_nowait, ("chunk", chunk))
                loop.call_soon_threadsafe(queue.put_nowait, ("done", None))
            except Exception as e:
                loop.call_soon_threadsafe(queue.put_nowait, ("error", e))

        threading.Thread(target=produce_tokens, daemon=True).start()

        async def event_generator():
            try:
                # Yield initial chunk (role definition)
                initial_chunk = {
                    "id": chat_id,
                    "object": "chat.completion.chunk",
                    "created": created_time,
                    "model": model_id,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"role": "assistant"},
                            "finish_reason": None
                        }
                    ]
                }
                yield f"data: {json.dumps(initial_chunk)}\n\n"

                while True:
                    event_type, val = await queue.get()
                    if event_type == "done":
                        break
                    elif event_type == "error":
                        raise val
                    elif event_type == "chunk":
                        token_chunk = {
                            "id": chat_id,
                            "object": "chat.completion.chunk",
                            "created": created_time,
                            "model": model_id,
                            "choices": [
                                {
                                    "index": 0,
                                    "delta": {"content": val},
                                    "finish_reason": None
                                }
                            ]
                        }
                        yield f"data: {json.dumps(token_chunk)}\n\n"

                # Yield final stop chunk with citations if RAG sources were retrieved
                final_choice = {
                    "index": 0,
                    "delta": {},
                    "finish_reason": "stop"
                }
                if rag_citations:
                    final_choice["citations"] = rag_citations

                final_chunk = {
                    "id": chat_id,
                    "object": "chat.completion.chunk",
                    "created": created_time,
                    "model": model_id,
                    "choices": [final_choice]
                }
                if rag_citations:
                    final_chunk["citations"] = rag_citations

                yield f"data: {json.dumps(final_chunk)}\n\n"
                yield "data: [DONE]\n\n"
            except Exception as e:
                print(f"Error during streaming inference: {e}")
                err_chunk = {
                    "id": chat_id,
                    "object": "chat.completion.chunk",
                    "created": created_time,
                    "model": model_id,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"content": f"\n[Aurora System Error: {e}]"},
                            "finish_reason": "error"
                        }
                    ]
                }
                yield f"data: {json.dumps(err_chunk)}\n\n"
                yield "data: [DONE]\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    else:
        # Non-streaming implementation offloaded to worker thread
        try:
            result = await asyncio.to_thread(
                engine.generate,
                prompt=formatted_messages,
                adapter_path=adapter_path,
                temperature=temperature,
                max_new_tokens=max_tokens,
                top_p=top_p
            )
            msg_obj = {
                "role": "assistant",
                "content": result.answer
            }
            if rag_citations:
                msg_obj["citations"] = rag_citations

            resp_payload = {
                "id": chat_id,
                "object": "chat.completion",
                "created": created_time,
                "model": model_id,
                "choices": [
                    {
                        "index": 0,
                        "message": msg_obj,
                        "finish_reason": "stop"
                    }
                ],
                "usage": {
                    "prompt_tokens": -1,
                    "completion_tokens": result.tokens_generated,
                    "total_tokens": -1
                }
            }
            if rag_citations:
                resp_payload["citations"] = rag_citations

            return resp_payload
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

