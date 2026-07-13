import asyncio

from AI.agents.mock_agent import mockAgent


def test_mock_agent():
    async def _run():
        mock_agent = mockAgent()
        await mock_agent.create_agent()
        response = await mock_agent.run_agent("test")
        assert response == "This is a mock response from the mock agent."

    asyncio.run(_run())