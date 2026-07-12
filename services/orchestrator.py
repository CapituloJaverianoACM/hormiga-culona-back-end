import asyncio

from AI.open_ai_client import OpenAiClient
from AI.agents.response_agent import ResponseAgent
from AI.agents.mock_agent import mockAgent

class AgentOrchestratorService: 
    
    def __init__(self):
        # initialize the client and agents
        self.open_ai_client = OpenAiClient() 
        self.response_agent = ResponseAgent()
        self.mock_agent = mockAgent()

        asyncio.run(self.response_agent.create_agent(self.open_ai_client))
        asyncio.run(self.mock_agent.create_agent())

    def processMessage(self, content: str, chatId: str) -> dict:
        
        """
        Método central que orquesta la lógica de negocio.
        """
        agent_response = asyncio.run(self.mock_agent.run_agent(content)) # for testing without api key
        #agent_response = asyncio.run(self.response_agent.run_agent(content))
        
        return {
            "agent_reply": agent_response,
    }

    async def process_audio_stream(self, audio_bytes: bytes) -> bytes:
        """
        Recibe el audio crudo del usuario y retorna el audio generado por el LLM.
        """

        audioResponse = "RESPUESTA ACA"
        
        return audioResponse
