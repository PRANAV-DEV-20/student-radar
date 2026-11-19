"""Minimal OpenAI-compatible API surface.

Local AI tooling (OpenCode providers, Ollama-compatible clients, IDE
extensions, ...) discovers models with ``GET /v1/models`` on its configured
base URL. When that base URL accidentally points at this API, every probe used
to return 404 and flood the server log. Implementing the small contract those
clients actually use keeps them quiet and makes the backend usable as an
OpenAI-style endpoint in its own right.

All chat requests are mapped onto the configured Gemini text model; the
embeddings endpoint reuses the existing embedding service. No extra API key is
required thanks to the deterministic fallbacks in ``GeminiService``.
"""

import json
import time
import uuid
from typing import Any, Dict, List, Optional, Union

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.gemini_client import gemini_service

router = APIRouter(tags=["OpenAI-compatible"])


# ----------------------------------------------------------------------
# Schemas
# ----------------------------------------------------------------------
class ChatMessage(BaseModel):
    role: str = "user"
    content: Any = ""


class ChatCompletionRequest(BaseModel):
    model: Optional[str] = None
    messages: List[ChatMessage] = Field(default_factory=list)
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    stream: bool = False


class EmbeddingRequest(BaseModel):
    model: Optional[str] = None
    input: Union[str, List[str]]


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
def _model_ids() -> List[str]:
    """Model ids advertised by ``/v1/models``.

    The first entry is the real configured text model. The remaining ids are
    compatibility aliases so tools that hard-code a common OpenAI model name
    still work; all of them are served by the same Gemini-backed generator.
    """
    candidates = (
        settings.GEMINI_TEXT_MODEL,
        "student-radar",
        "gpt-4o-mini",
    )
    models: List[str] = []
    for candidate in candidates:
        if candidate and candidate not in models:
            models.append(candidate)
    return models


def _model_payload(model_id: str) -> Dict[str, Any]:
    return {
        "id": model_id,
        "object": "model",
        "created": 0,
        "owned_by": "student-radar",
    }


def _message_text(message: ChatMessage) -> str:
    """Flatten OpenAI text or multimodal content parts into plain text."""
    content = message.content
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: List[str] = []
        for part in content:
            if isinstance(part, dict):
                text = part.get("text")
                if isinstance(text, str):
                    parts.append(text)
            elif isinstance(part, str):
                parts.append(part)
        return "\n".join(parts)
    return str(content or "")


def _prompt_from_messages(messages: List[ChatMessage]) -> str:
    lines = [
        f"{(message.role or 'user').strip().upper()}: {_message_text(message)}"
        for message in messages
    ]
    return "\n\n".join(lines) + "\n\nASSISTANT:"


# ----------------------------------------------------------------------
# Routes
# ----------------------------------------------------------------------
@router.get("/v1/models")
@router.get("/v1/models/", include_in_schema=False)
async def list_models() -> Dict[str, Any]:
    """OpenAI-compatible model discovery (the endpoint polled by clients)."""
    return {"object": "list", "data": [_model_payload(model) for model in _model_ids()]}


@router.get("/v1/models/{model_id:path}")
async def retrieve_model(model_id: str) -> Dict[str, Any]:
    if model_id not in _model_ids():
        raise HTTPException(status_code=404, detail=f"Unknown model: {model_id}")
    return _model_payload(model_id)


@router.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest) -> Any:
    if not request.messages:
        raise HTTPException(status_code=400, detail="messages must not be empty")

    model = request.model or settings.GEMINI_TEXT_MODEL
    completion_id = f"chatcmpl-{uuid.uuid4().hex}"
    created = int(time.time())
    content = await gemini_service.generate_chat_text(
        _prompt_from_messages(request.messages),
        model=model,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
    )

    def build_chunk(delta: str, finish_reason: Optional[str] = None) -> Dict[str, Any]:
        return {
            "id": completion_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "delta": {"content": delta} if delta else {},
                    "finish_reason": finish_reason,
                }
            ],
        }

    if request.stream:
        def event_stream():
            yield f"data: {json.dumps(build_chunk(content))}\n\n"
            yield f"data: {json.dumps(build_chunk('', 'stop'))}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(event_stream(), media_type="text/event-stream")

    return {
        "id": completion_id,
        "object": "chat.completion",
        "created": created,
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }


@router.post("/v1/embeddings")
async def embeddings(request: EmbeddingRequest) -> Dict[str, Any]:
    texts = [request.input] if isinstance(request.input, str) else request.input
    if not texts:
        raise HTTPException(status_code=400, detail="input must not be empty")

    data = []
    for index, text in enumerate(texts):
        vector = await gemini_service.generate_embedding(text)
        data.append({"object": "embedding", "index": index, "embedding": vector})

    return {
        "object": "list",
        "model": request.model or settings.GEMINI_EMBEDDING_MODEL,
        "data": data,
        "usage": {"prompt_tokens": 0, "total_tokens": 0},
    }
