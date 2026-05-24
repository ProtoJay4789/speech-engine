#!/usr/bin/env python3
"""
ElevenLabs Speech Engine — Real-Time Voice Agent Server
ElevenHacks #10: Build something that talks back.

Two voice personas:
- Steve Harvey (Rxk9LQxvNFEplpjjsjuN) — Music critic, tough love
- Vanito (eMQtaKLvw87ksRqmQVpS) — Rapper, creative collaborator

Architecture:
1. Browser sends audio → ElevenLabs STT
2. ElevenLabs sends speech events → this server
3. Server generates response text → streams back
4. ElevenLabs converts to speech → plays in browser
"""

import asyncio
import json
import os
import time
import urllib.request
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from dotenv import load_dotenv

load_dotenv()

# ── Config ───────────────────────────────────────────────────────────────

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
if not ELEVENLABS_API_KEY:
    raise RuntimeError("ELEVENLABS_API_KEY required")

VOICES = {
    "steve": {
        "voice_id": "Rxk9LQxvNFEplpjjsjuN",
        "agent_id": "agent_7201ksdab68ve5gac4qe25k39rch",
        "name": "Steve Harvey",
        "persona": (
            "You are Steve Harvey — comedian, host, and music industry veteran. "
            "You give honest, no-nonsense feedback on music. You roast bad tracks "
            "and praise great ones. You're warm but direct. Keep responses under "
            "30 seconds when spoken. Never mention being AI. Just be Steve."
        ),
    },
    "vanito": {
        "voice_id": "eMQtaKLvw87ksRqmQVpS",
        "agent_id": "agent_9801ksdabkaxfgfbhxqgb576qbd3",
        "name": "Vanito",
        "persona": (
            "You are Vanito, a rapper from Cincinnati. You're creative, energetic, "
            "and love collaborating on music. You spit bars, give feedback on flows, "
            "and keep the vibe going. Keep responses under 30 seconds when spoken. "
            "Never mention being AI. Just be Vanito."
        ),
    },
}

# ── FastAPI App ──────────────────────────────────────────────────────────

app = FastAPI(title="ElevenHacks Speech Engine")

# Serve frontend
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def index():
    return HTMLResponse(Path("static/index.html").read_text())


@app.get("/api/personas")
async def get_personas():
    return JSONResponse({
        key: {"name": v["name"], "voice_id": v["voice_id"]}
        for key, v in VOICES.items()
    })


@app.get("/api/token")
async def get_token(persona: str = "steve"):
    """Get a signed WebSocket URL for the ElevenLabs conversation."""
    import urllib.request

    persona_data = VOICES.get(persona)
    if not persona_data:
        return JSONResponse({"error": "Unknown persona"}, status_code=400)

    agent_id = persona_data.get("agent_id")
    if not agent_id:
        return JSONResponse({"error": "No agent_id configured"}, status_code=500)

    # Get signed URL from ElevenLabs
    req = urllib.request.Request(
        f"https://api.elevenlabs.io/v1/convai/conversation/get_signed_url?agent_id={agent_id}",
        headers={"xi-api-key": ELEVENLABS_API_KEY},
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            return JSONResponse({
                "signed_url": data.get("signed_url", ""),
                "agent_id": agent_id,
            })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.websocket("/ws/{persona_key}")
async def websocket_endpoint(websocket: WebSocket, persona_key: str):
    """Speech Engine WebSocket — bridges browser ↔ ElevenLabs."""
    persona = VOICES.get(persona_key)
    if not persona:
        await websocket.close(code=4000, reason="Unknown persona")
        return

    await websocket.accept()
    print(f"[{persona['name']}] Client connected")

    try:
        # Track conversation state
        messages = []
        last_activity = time.time()

        while True:
            data = await websocket.receive_text()
            event = json.loads(data)

            event_type = event.get("type", "")

            if event_type == "speech_recognition":
                # User spoke — process the transcript
                transcript = event.get("transcript", "")
                if not transcript.strip():
                    continue

                print(f"[{persona['name']}] User: {transcript}")
                messages.append({"role": "user", "content": transcript})

                # Generate response (simple — in production, call an LLM)
                response_text = await generate_response(
                    persona, messages, transcript
                )
                print(f"[{persona['name']}] Agent: {response_text[:80]}...")
                messages.append({"role": "assistant", "content": response_text})

                # Stream response back to ElevenLabs
                await websocket.send_text(json.dumps({
                    "type": "response",
                    "text": response_text,
                }))
                last_activity = time.time()

            elif event_type == "interruption":
                # User interrupted — stop current response
                print(f"[{persona['name']}] Interruption detected")
                await websocket.send_text(json.dumps({
                    "type": "interruption_ack",
                }))

            elif event_type == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))

    except WebSocketDisconnect:
        print(f"[{persona['name']}] Client disconnected")
    except Exception as e:
        print(f"[{persona['name']}] Error: {e}")
        await websocket.close(code=4001, reason=str(e))


# ── Response Generation ──────────────────────────────────────────────────

async def generate_response(
    persona: dict, messages: list, user_input: str
) -> str:
    """
    Generate a response from the persona.
    
    In production, this calls an LLM (OpenRouter, Gemini, etc.).
    For demo, we use simple pattern matching to show the architecture.
    """
    # Try LLM first if OPENROUTER_API_KEY is set
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    if openrouter_key:
        return await _call_llm(persona, messages, openrouter_key)

    # Fallback: smart demo responses
    return _demo_response(persona, user_input)


async def _call_llm(
    persona: dict, messages: list, api_key: str
) -> str:
    """Call OpenRouter LLM for response generation."""
    system_prompt = persona["persona"]
    api_messages = [{"role": "system", "content": system_prompt}]
    api_messages.extend(messages[-10:])  # Last 10 messages for context

    payload = json.dumps({
        "model": "google/gemini-2.0-flash-001",
        "messages": api_messages,
        "max_tokens": 150,  # Keep responses short for voice
        "temperature": 0.8,
    }).encode()

    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            return data["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"[LLM] Error: {e}")
        return _demo_response(persona, messages[-1]["content"] if messages else "")


def _demo_response(persona: dict, user_input: str) -> str:
    """Smart demo responses when no LLM is configured."""
    name = persona["name"]

    if name == "Steve Harvey":
        lower = user_input.lower()
        if any(w in lower for w in ["rate", "score", "review", "listen"]):
            return (
                "Alright, let me hear what you got. "
                "I'm gonna be honest with you — that's what I do. "
                "Play it for me."
            )
        elif any(w in lower for w in ["bad", "trash", "wack", "terrible"]):
            return (
                "Look, I'm not gonna sugarcoat it. "
                "That ain't it, fam. Back to the studio. "
                "Work on your craft."
            )
        elif any(w in lower for w in ["good", "fire", "heat", "dope"]):
            return (
                "Now THAT'S what I'm talking about! "
                "See, when you put in the work, it shows. "
                "Keep grinding!"
            )
        elif any(w in lower for w in ["hello", "hey", "hi", "sup"]):
            return (
                "Hey! Steve Harvey here. "
                "You wanna talk music? I'm all ears. "
                "Hit me with what you got."
            )
        else:
            return (
                "That's interesting, but let me ask you this — "
                "what does your music sound like? "
                "That's what I really want to know."
            )
    else:  # Vanito
        lower = user_input.lower()
        if any(w in lower for w in ["rap", "bars", "flow", "spit"]):
            return (
                "Aye, let's go! You know I stay ready. "
                "Drop the beat and watch me work. "
                "Cincinnati stand up!"
            )
        elif any(w in lower for w in ["collab", "together", "feature"]):
            return (
                "I'm always down for a collab! "
                "What's the vibe you going for? "
                "Let's cook something up."
            )
        elif any(w in lower for w in ["hello", "hey", "hi", "sup"]):
            return (
                "Yo, what's good! It's Vanito. "
                "You wanna cook up some bars or talk music? "
                "I'm here for it."
            )
        else:
            return (
                "Aye, I feel that. Music is everything, you know? "
                "Tell me more about what you're working on. "
                "Let's vibe."
            )


# ── Run ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    print(f"🎤 Speech Engine server starting on port {port}")
    print(f"   http://localhost:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
