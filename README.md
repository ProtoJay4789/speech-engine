# Speech Engine — Real-Time Voice Agents

> **Talk to someone who talks back.** Real-time voice conversations with AI personalities powered by ElevenLabs Speech Engine.

**Built for:** ElevenHacks #10
**Track:** Real-time voice agents
**Stack:** Python (FastAPI) + ElevenLabs Speech Engine + Vanilla JS

## What It Does

Two voice personas with distinct personalities:

- 🎤 **Steve Harvey** — Music critic. Tough love. Roasts bad tracks, praises great ones.
- 🔥 **Vanito** — Rapper from Cincinnati. Creative collaborator. Always ready to spit bars.

Pick a voice, click the orb, and start talking. The agent responds in real-time with voice.

## How It Works

```
Browser mic → ElevenLabs STT → Server processes → Response text → ElevenLabs TTS → Browser speaker
```

1. Browser captures microphone audio
2. ElevenLabs converts speech to text (STT)
3. Server receives transcript, generates response (LLM or demo mode)
4. Response streams back as text
5. ElevenLabs converts to speech and plays in browser
6. Interruption-aware — talk over the agent and it stops

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set API key
cp .env.example .env
# Edit .env with your ELEVENLABS_API_KEY

# Run server
python server.py

# Open browser
open http://localhost:8080
```

## Architecture

```
┌─────────────┐     ┌──────────────────┐     ┌────────────────┐
│   Browser    │────▶│  FastAPI Server   │────▶│  ElevenLabs    │
│  (JS Client) │◀────│  (WebSocket WS)   │◀────│  Speech Engine │
└─────────────┘     └──────────────────┘     └────────────────┘
     mic/audio          process events         STT + TTS
```

### Server (`server.py`)
- FastAPI with WebSocket endpoint at `/ws/{persona}`
- Token endpoint at `/api/token` for browser client auth
- Persona endpoint at `/api/personas` for UI configuration
- Response generation via OpenRouter LLM (or built-in demo mode)
- Interruption handling

### Frontend (`static/index.html`)
- Vanilla JS — no build step needed
- WebSocket connection to ElevenLabs
- MediaRecorder API for microphone capture
- Real-time transcript display
- Animated orb interface (idle → listening → speaking states)

## Personas

| Persona | Voice ID | Personality |
|---------|----------|-------------|
| Steve Harvey | `Rxk9LQxvNFEplpjjsjuN` | Music critic, tough love, honest feedback |
| Vanito | `eMQtaKLvw87ksRqmQVpS` | Rapper, creative, collaborative energy |

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Frontend UI |
| `/api/personas` | GET | List available personas |
| `/api/token?persona=steve` | GET | Get conversation token |
| `/ws/{persona}` | WebSocket | Speech Engine connection |

## Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| `ELEVENLABS_API_KEY` | Yes | ElevenLabs API authentication |
| `OPENROUTER_API_KEY` | No | LLM for smart responses (demo mode without) |
| `PORT` | No | Server port (default: 8080) |

## Demo Mode

Without an LLM API key, the server uses built-in demo responses that show the architecture and voice quality. The personas respond contextually to keywords (music, rap, collab, etc.) — not just canned phrases.

## Security Notes

- Speech-recognition text is treated as untrusted input
- WebSocket connections are authenticated via conversation tokens
- No persistent storage of audio or transcripts

## Built By

GenTech Labs — [ProtoJay4789](https://github.com/ProtoJay4789)
