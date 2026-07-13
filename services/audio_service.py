class AgentAudioService:
    def __init__(self, transcription_client, synthesis_client):
        self.transcription_client = transcription_client
        self.synthesis_client = synthesis_client

    def transcribe_audio(self, audio_bytes: bytes, filename: str = "audio.wav", content_type: str = "audio/wav") -> str:
        return self.transcription_client.transcribe_audio(audio_bytes, filename, content_type)

    def synthesize_audio(self, text: str) -> bytes:
        return self.synthesis_client.synthesize_speech(text)
