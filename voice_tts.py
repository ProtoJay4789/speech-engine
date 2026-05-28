"""
Voice TTS — Standalone text-to-speech module.
ElevenLabs primary, Edge TTS fallback.
Importable without FastAPI dependencies.
"""

import json
import os
import tempfile
import urllib.request
from typing import Optional

# ── Config ───────────────────────────────────────────────────────────────

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")

EDGE_TTS_AVAILABLE = False
try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    pass


# ── Voice Configs ────────────────────────────────────────────────────────

VOICES = {
    "steve": {
        "voice_id": "Rxk9LQxvNFEplpjjsjuN",
        "name": "Steve Harvey",
        "persona": (
            "You are Steve Harvey — comedian, host, and music industry veteran. "
            "You give honest, no-nonsense feedback. You roast bad trades "
            "and praise great ones. You're warm but direct."
        ),
        "edge_tts_voice": "en-US-AndrewNeural",
        "edge_tts_rate": "-5%",
        "edge_tts_pitch": "-2Hz",
    },
    "vanito": {
        "voice_id": "eMQtaKLvw87ksRqmQVpS",
        "name": "Vanito",
        "persona": (
            "You are Vanito, a rapper from Cincinnati. You're creative, energetic. "
            "You spit bars, give feedback, and keep the vibe going."
        ),
        "edge_tts_voice": "en-US-BrianNeural",
        "edge_tts_rate": "+0%",
        "edge_tts_pitch": "+0Hz",
    },
}


# ── TTS Functions ────────────────────────────────────────────────────────

async def text_to_speech(text: str, voice_config: dict) -> Optional[str]:
    """
    Convert text to speech. ElevenLabs primary, Edge TTS fallback.
    Returns path to audio file.
    """
    # Try ElevenLabs first
    if ELEVENLABS_API_KEY and voice_config.get("voice_id"):
        try:
            return await _elevenlabs_tts(text, voice_config["voice_id"])
        except Exception as e:
            print(f"[TTS] ElevenLabs failed: {e}, trying Edge TTS")

    # Edge TTS fallback
    if EDGE_TTS_AVAILABLE and voice_config.get("edge_tts_voice"):
        return await _edge_tts(text, voice_config)

    return None


async def _elevenlabs_tts(text: str, voice_id: str) -> Optional[str]:
    """Generate speech using ElevenLabs API."""
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    payload = json.dumps({
        "text": text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
        },
    }).encode()

    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "xi-api-key": ELEVENLABS_API_KEY,
            "Content-Type": "application/json",
        },
    )

    with urllib.request.urlopen(req, timeout=30) as resp:
        audio_data = resp.read()

    tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    tmp.write(audio_data)
    tmp.close()
    return tmp.name


async def _edge_tts(text: str, voice_config: dict) -> Optional[str]:
    """Generate speech using Edge TTS (free fallback)."""
    if not EDGE_TTS_AVAILABLE:
        return None

    voice = voice_config.get("edge_tts_voice", "en-US-AndrewNeural")
    rate = voice_config.get("edge_tts_rate", "+0%")
    pitch = voice_config.get("edge_tts_pitch", "+0Hz")

    tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    tmp.close()

    communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)  # type: ignore
    await communicate.save(tmp.name)

    return tmp.name


def get_voice_config(persona: str, severity: str = "medium") -> dict:
    """
    Get voice config with severity-based adjustments.
    
    Args:
        persona: "steve" or "vanito"
        severity: "mild", "medium", "brutal", "legendary"
    """
    config = VOICES.get(persona, VOICES["steve"]).copy()

    # Severity adjustments — slower + lower pitch for more dramatic effect
    severity_adjustments = {
        "mild": {"rate": "-5%", "pitch": "-2Hz"},
        "medium": {"rate": "-8%", "pitch": "-3Hz"},
        "brutal": {"rate": "-12%", "pitch": "-4Hz"},
        "legendary": {"rate": "-15%", "pitch": "-5Hz"},
    }

    adjustments = severity_adjustments.get(severity, {})
    config.update(adjustments)

    return config


# ── Quick test ───────────────────────────────────────────────────────────

async def _test():
    print("🎤 Testing Voice TTS...")
    config = get_voice_config("steve", "brutal")
    result = await text_to_speech(
        "You bought at the top and sold at the bottom. "
        "That is not trading. That is donating to the market.",
        config,
    )
    if result:
        size = os.path.getsize(result)
        print(f"✅ Audio generated: {result} ({size} bytes)")
    else:
        print("❌ No audio generated")


if __name__ == "__main__":
    import asyncio
    asyncio.run(_test())
