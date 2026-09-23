from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.agent.langchain_vehicle_agent import langchain_agent
from app.agent.vehicle_agent import agent
from app.config.settings import settings


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Local autonomous AI agent for live Pitstrack fleet/vehicle data.",
)


class Utf8JsonResponse(JSONResponse):
    media_type = "application/json; charset=utf-8"


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2_000)
    user_id: int = Field(ge=1)


class ChatResponse(BaseModel):
    answer: str
    meta: dict[str, Any]


def verify_local_access(x_api_secret: str = Header(default="")) -> None:
    if x_api_secret != settings.api_secret:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized local agent request.",
        )


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": settings.app_name,
        "model": settings.ollama_model,
        "mode": "autonomous-tool-agent",
    }


@app.post(
    "/api/v1/chat",
    response_model=ChatResponse,
    response_class=Utf8JsonResponse,
)
def chat(
    request: ChatRequest,
    _: None = Depends(verify_local_access),
) -> ChatResponse:
    """Plain Ollama tool-calling agent (app.agent.vehicle_agent)."""
    return ChatResponse(**agent.chat(request.message, request.user_id))


@app.post(
    "/api/v2/chat",
    response_model=ChatResponse,
    response_class=Utf8JsonResponse,
)
def chat_langchain(
    request: ChatRequest,
    _: None = Depends(verify_local_access),
) -> ChatResponse:
    """Same contract as /api/v1/chat, served by the LangChain/LangGraph
    agent in app.agent.langchain_vehicle_agent instead, for comparison."""
    return ChatResponse(**langchain_agent.chat(request.message, request.user_id))
