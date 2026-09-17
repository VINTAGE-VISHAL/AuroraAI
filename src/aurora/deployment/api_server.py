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
    FileTooLargeError,
    FileValidationError,
    RuntimeFileNotFoundError,
    StorageOperationError,
)
from aurora.ingestion.runtime.file_validator import RuntimeFileValidator
from aurora.ingestion.runtime.file_storage import RuntimeFileStorage
from aurora.services.file_service import FileService
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

    if not messages:
        raise HTTPException(status_code=400, detail="Messages array cannot be empty")

    # Sanitize input messages (strip out previous error strings or empty turns)
    clean_messages = []
    for m in messages:
        content = m.get("content", "")
        if content and isinstance(content, str) and not content.startswith("[Aurora System Error:") and not content.startswith("[Error:"):
            clean_messages.append(m)

    if not clean_messages:
        clean_messages = messages

    # Inject system prompt with CS domain constraints if missing
    formatted_messages = []
    has_system = False
    for m in clean_messages:
        if m.get("role") == "system":
            has_system = True
            formatted_messages.append({
                "role": "system",
                "content": f"{AURORA_SYSTEM_PROMPT}\n\n{m.get('content', '')}"
            })
        else:
            formatted_messages.append(m)

    if not has_system:
        formatted_messages.insert(0, {"role": "system", "content": AURORA_SYSTEM_PROMPT})

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

                # Yield final stop chunk
                final_chunk = {
                    "id": chat_id,
                    "object": "chat.completion.chunk",
                    "created": created_time,
                    "model": model_id,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {},
                            "finish_reason": "stop"
                        }
                    ]
                }
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
            return {
                "id": chat_id,
                "object": "chat.completion",
                "created": created_time,
                "model": model_id,
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": result.answer
                        },
                        "finish_reason": "stop"
                    }
                ],
                "usage": {
                    "prompt_tokens": -1,
                    "completion_tokens": result.tokens_generated,
                    "total_tokens": -1
                }
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

