import asyncio

class AgentOrchestratorService: 

    def processMessage(self, content: str, chatId: str) -> dict:
        
        """
        Método central que orquesta la lógica de negocio.
        """

        agent_response = f"Agente recibió el mensaje: '{content}'. Procesamiento exitoso para usuario {chatId}."
        
        return {
            "agent_reply": agent_response,
    }

    async def process_audio_stream(self, audio_bytes: bytes) -> bytes:
        """
        Recibe el audio crudo del usuario y retorna el audio generado por el LLM.
        """

        audioResponse = "RESPUESTA ACA"
        
        return audioResponse
