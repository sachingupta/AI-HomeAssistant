"""
FastAPI backend — bridges the Android app to the agent system.
Endpoints:
  POST /chat          — single-turn HTTP request/response
  WS   /ws/{user_id} — persistent WebSocket for streaming + proactive alerts
  GET  /health        — liveness check
"""

import json
import logging
from contextlib import asynccontextmanager
from typing import Annotated

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.config import settings
from backend.agents.grocery.agent import GroceryAgent

# TODO (Phase 3): replace GroceryAgent with OrchestratorAgent so all messages
# are routed to the right sub-agent automatically:
#   from backend.orchestrator.agent import OrchestratorAgent
# main.py itself won't change beyond that one import swap.

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Per-user agent instances (keyed by user_id)
_agent_sessions: dict[str, GroceryAgent] = {}


def _get_agent(user_id: str) -> GroceryAgent:
    if user_id not in _agent_sessions:
        _agent_sessions[user_id] = GroceryAgent(user=user_id)
    return _agent_sessions[user_id]


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("AI Home Assistant backend starting — family: %s", settings.family_name)
    yield
    logger.info("Backend shutting down.")


app = FastAPI(title="AI Home Assistant", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten to Android app origin in production
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    user: str
    message: str
    session_id: str = ""


class ChatResponse(BaseModel):
    response: str
    agent_called: str
    session_id: str


# ---------------------------------------------------------------------------
# HTTP endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {"status": "ok", "family": settings.family_name}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Single-turn HTTP chat — suitable for simple request/response from Android."""
    try:
        agent = _get_agent(request.user)
        response_text = agent.chat(request.message)
        return ChatResponse(
            response=response_text,
            agent_called="grocery_agent",  # Phase 3: orchestrator will return the actual agent name
            session_id=request.session_id,
        )
    except Exception as exc:
        logger.exception("Chat error for user %s", request.user)
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------

@app.websocket("/ws/{user_id}")
async def websocket_chat(websocket: WebSocket, user_id: str):
    """
    Persistent WebSocket for real-time chat and proactive push alerts.

    Client → Server message format:
        {"type": "chat", "message": "...", "session_id": "..."}

    Server → Client message formats:
        {"type": "response", "message": "...", "agent_called": "grocery_agent"}
        {"type": "alert",    "message": "..."}
        {"type": "error",    "message": "..."}
    """
    await websocket.accept()
    logger.info("WebSocket connected: %s", user_id)
    agent = _get_agent(user_id)

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_text(
                    json.dumps({"type": "error", "message": "Invalid JSON"})
                )
                continue

            msg_type = payload.get("type")

            if msg_type == "chat":
                user_message = payload.get("message", "").strip()
                if not user_message:
                    continue
                try:
                    response_text = agent.chat(user_message)
                    await websocket.send_text(json.dumps({
                        "type": "response",
                        "message": response_text,
                        "agent_called": "grocery_agent",  # Phase 3: orchestrator will return the actual agent name
                    }))
                except Exception as exc:
                    logger.exception("Agent error for %s", user_id)
                    await websocket.send_text(
                        json.dumps({"type": "error", "message": str(exc)})
                    )

            elif msg_type == "reset":
                agent.reset()
                await websocket.send_text(
                    json.dumps({"type": "response", "message": "Session cleared."})
                )

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected: %s", user_id)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=True,
    )
