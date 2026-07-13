import os
from html import escape

import requests
from azure.ai.transcription import TranscriptionClient
from azure.ai.transcription.models import TranscriptionContent, TranscriptionOptions
from azure.core.credentials import AzureKeyCredential


class AzureTranscriptionClient:
    def __init__(self):
        self.endpoint = _require_env("AZURE_SPEECH_ENDPOINT").rstrip("/")
        self.api_key = _get_speech_api_key()
        self.client = TranscriptionClient(
            endpoint=self.endpoint,
            credential=AzureKeyCredential(self.api_key),
        )

    def transcribe_audio(self, audio_bytes: bytes, filename: str = "audio.wav", content_type: str = "audio/wav") -> str:
        audio_content = TranscriptionContent(
            definition=TranscriptionOptions(locales=["es-ES"]),
            audio=(filename, audio_bytes, content_type),
        )
        transcription_result = self.client.transcribe(audio_content)
        combined_phrases = getattr(transcription_result, "combined_phrases", None) or []
        if combined_phrases:
            return " ".join(phrase.text for phrase in combined_phrases if getattr(phrase, "text", "")).strip()
        return " ".join(phrase.display_text for phrase in getattr(transcription_result, "phrases", []) if getattr(phrase, "display_text", "")).strip()


class AzureSpeechSynthesisClient:
    def __init__(self):
        self.api_key = _get_speech_api_key()
        self.voice = os.getenv("AZURE_SPEECH_VOICE", "es-CO-GonzaloNeural")
        self.output_format = os.getenv(
            "AZURE_SPEECH_OUTPUT_FORMAT",
            "riff-24khz-16bit-mono-pcm",
        )
        self.tts_endpoint = _resolve_tts_endpoint()

    def synthesize_speech(self, text: str) -> bytes:
        text = text.strip()
        if not text:
            return b""

        response = requests.post(
            self.tts_endpoint,
            headers={
                "Ocp-Apim-Subscription-Key": self.api_key,
                "Content-Type": "application/ssml+xml",
                "X-Microsoft-OutputFormat": self.output_format,
                "User-Agent": "hormiga-culona-back-end",
            },
            data=self._build_ssml(text).encode("utf-8"),
            timeout=30,
        )
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            if response.status_code == 404:
                raise ValueError(
                    "Speech synthesis endpoint not found. Set AZURE_SPEECH_TTS_ENDPOINT or AZURE_SPEECH_REGION. "
                    f"Current endpoint: {self.tts_endpoint}"
                ) from exc
            raise
        return response.content

    def _build_ssml(self, text: str) -> str:
        safe_text = escape(text)
        return (
            "<speak version='1.0' xml:lang='es-CO'>"
            f"<voice name='{self.voice}'>{safe_text}</voice>"
            "</speak>"
        )


class AzureSyntesisClient(AzureSpeechSynthesisClient):
    pass



def _get_speech_api_key() -> str:
    return os.getenv("AZURE_SPEECH_API_KEY") or _require_env("AZURE_AI_FOUNDRY_API_KEY")



def _resolve_tts_endpoint() -> str:
    explicit = os.getenv("AZURE_SPEECH_TTS_ENDPOINT")
    if explicit:
        return explicit.rstrip("/")

    region = os.getenv("AZURE_SPEECH_REGION")
    if region:
        return f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1"

    endpoint = _require_env("AZURE_SPEECH_ENDPOINT").rstrip("/")
    if endpoint.endswith("/cognitiveservices/v1"):
        return endpoint
    if ".tts.speech.microsoft.com" in endpoint:
        return f"{endpoint}/cognitiveservices/v1"
    return f"{endpoint}/cognitiveservices/v1"



def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"Missing environment variable: {name}")
    return value
