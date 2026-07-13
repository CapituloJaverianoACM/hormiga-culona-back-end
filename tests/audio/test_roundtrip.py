import argparse
import asyncio
import json
from pathlib import Path
import sys

import websockets
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env")

from AI.audio_client import AzureSpeechSynthesisClient, AzureTranscriptionClient
from fastapi.encoders import jsonable_encoder


ARTIFACTS_DIR = Path(__file__).parent / "artifacts"
DEFAULT_PROMPT = "Hola dime los gastos de 2017"
DEFAULT_MODE = "response"
DEFAULT_PREVIEW_LIMIT = 5
DEFAULT_SESSION_ID = "test-session"


def _assert_file(path: Path) -> None:
    assert path.exists(), f"Missing artifact: {path}"
    assert path.stat().st_size > 0, f"Empty artifact: {path}"


def _save_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(jsonable_encoder(data), ensure_ascii=False, indent=2), encoding="utf-8")


def _slug(value: str) -> str:
    cleaned = [c.lower() if c.isalnum() else "_" for c in value.strip()]
    slug = "".join(cleaned).strip("_")
    while "__" in slug:
        slug = slug.replace("__", "_")
    return slug or "run"


async def _send_audio_and_get_response(
    audio_bytes: bytes,
    session_id: str,
    mode: str,
    preview_limit: int,
    output: str = "both",
) -> tuple[dict | None, bytes | None]:
    ws_url = f"ws://127.0.0.1:8000/ws/agent/voice/{session_id}?mode={mode}&preview_limit={preview_limit}&output={output}"
    async with websockets.connect(ws_url, max_size=None) as websocket:
        await websocket.send(audio_bytes)

        response_payload = None
        response_audio = None

        if output in {"json", "both"}:
            response_json = await websocket.recv()
            assert isinstance(response_json, str), f"Expected JSON text frame, got: {type(response_json)!r}"
            response_payload = json.loads(response_json)

        if output in {"audio", "both"}:
            response_audio = await websocket.recv()
            assert isinstance(response_audio, bytes), f"Expected audio bytes, got: {type(response_audio)!r}"

        return response_payload, response_audio


def run_voice_workflow(
    prompt: str,
    mode: str = DEFAULT_MODE,
    preview_limit: int = DEFAULT_PREVIEW_LIMIT,
    session_id: str = DEFAULT_SESSION_ID,
    output: str = "both",
) -> dict:
    mode = mode.strip().lower()
    if mode not in {"response", "ui"}:
        raise ValueError("mode must be 'response' or 'ui'")
    if output not in {"audio", "json", "both"}:
        raise ValueError("output must be 'audio', 'json' or 'both'")

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    run_name = f"{mode}_{_slug(prompt)[:60]}"

    question_audio_path = ARTIFACTS_DIR / f"{run_name}_question.wav"
    question_transcription_path = ARTIFACTS_DIR / f"{run_name}_question_transcription.json"
    response_json_path = ARTIFACTS_DIR / f"{run_name}_response.json"
    response_audio_path = ARTIFACTS_DIR / f"{run_name}_response.wav"
    response_transcription_path = ARTIFACTS_DIR / f"{run_name}_response_transcription.json"
    workflow_path = ARTIFACTS_DIR / f"{run_name}_workflow.json"

    synthesis_client = AzureSpeechSynthesisClient()
    transcription_client = AzureTranscriptionClient()

    question_audio = synthesis_client.synthesize_speech(prompt)
    question_audio_path.write_bytes(question_audio)
    _assert_file(question_audio_path)

    question_transcription = transcription_client.transcribe_audio(
        question_audio,
        question_audio_path.name,
        "audio/wav",
    )
    question_payload = {
        "stage": "question",
        "mode": mode,
        "prompt": prompt,
        "transcription": question_transcription,
        "audio_path": str(question_audio_path),
    }
    _save_json(question_transcription_path, question_payload)
    _assert_file(question_transcription_path)
    assert question_transcription.strip(), "Question transcription is empty"

    response_payload, response_audio = asyncio.run(
        _send_audio_and_get_response(question_audio, session_id, mode, preview_limit, output)
    )

    spoken_payload = None
    if response_payload is not None:
        _save_json(response_json_path, response_payload)
        _assert_file(response_json_path)

        assert response_payload.get("type") == "agent_result"
        assert response_payload.get("mode") == mode
        assert isinstance(response_payload.get("data"), dict)
        assert response_payload.get("voice_reply", "").strip()
        assert response_payload.get("explanation", "").strip()

        data = response_payload["data"]
        assert data.get("voice_reply", "").strip()
        assert data.get("explanation", "").strip()
        assert "transcription" not in json.dumps(data, ensure_ascii=False).lower(), "Query result must not be injected into transcript fields"

    if response_audio is not None:
        response_audio_path.write_bytes(response_audio)
        _assert_file(response_audio_path)

        response_transcription = transcription_client.transcribe_audio(
            response_audio,
            response_audio_path.name,
            "audio/wav",
        )
        spoken_payload = {
            "stage": "response_audio",
            "mode": mode,
            "transcription": response_transcription,
            "audio_path": str(response_audio_path),
        }

        _save_json(response_transcription_path, spoken_payload)
        _assert_file(response_transcription_path)
        assert response_transcription.strip(), "Response transcription is empty"

    workflow_payload = {
        "session_id": session_id,
        "mode": mode,
        "preview_limit": preview_limit,
        "output": output,
        "question": question_payload,
        "response_json": response_payload,
        "response_audio": spoken_payload,
    }

    _save_json(workflow_path, workflow_payload)
    _assert_file(workflow_path)

    return {
        "question_audio": question_audio_path,
        "question_transcription": question_transcription_path,
        "response_json": response_json_path,
        "response_audio": response_audio_path,
        "response_transcription": response_transcription_path,
        "workflow": workflow_path,
        "workflow_payload": workflow_payload,
    }


def test_full_voice_workflow_only_websocket():
    result = run_voice_workflow(DEFAULT_PROMPT, DEFAULT_MODE, DEFAULT_PREVIEW_LIMIT, DEFAULT_SESSION_ID)
    assert result["workflow_payload"]["mode"] in {"response", "ui"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    parser.add_argument("--mode", choices=["response", "ui"], default=DEFAULT_MODE)
    parser.add_argument("--preview-limit", type=int, default=DEFAULT_PREVIEW_LIMIT)
    parser.add_argument("--session-id", default=DEFAULT_SESSION_ID)
    parser.add_argument("--output", choices=["audio", "json", "both"], default="both")
    args = parser.parse_args()

    result = run_voice_workflow(args.prompt, args.mode, args.preview_limit, args.session_id, args.output)
    print(f"ok question audio: {result['question_audio']}")
    print(f"ok question transcription: {result['question_transcription']}")
    if args.output in {"json", "both"}:
        print(f"ok response json: {result['response_json']}")
    if args.output in {"audio", "both"}:
        print(f"ok response audio: {result['response_audio']}")
        print(f"ok response transcription: {result['response_transcription']}")
    print(f"ok workflow json: {result['workflow']}")
