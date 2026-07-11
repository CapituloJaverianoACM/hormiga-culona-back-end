import asyncio
import websockets

async def test_audio_stream():
    uri = "ws://127.0.0.1:8000/ws/agent/voice/test_client"
    
    async with websockets.connect(uri) as websocket:
        print("Conectado al servidor.")
        
        # 1. Leer un archivo de audio real de tu computadora
        with open("himno.mp3", "rb") as f:
            audio_data = f.read()
            
        # 2. Enviar los bytes crudos (Binary Frame)
        await websocket.send(audio_data)
        print("Audio enviado, esperando respuesta del agente...")
        
        # 3. Recibir la respuesta binaria
        agent_response_bytes = await websocket.recv()
        
        # 4. Guardar la respuesta del agente como un nuevo archivo de audio
        with open("respuesta_agente.wav", "wb") as f:
            f.write(agent_response_bytes)
            
        print("Respuesta recibida y guardada exitosamente.")

if __name__ == "__main__":
    asyncio.run(test_audio_stream())