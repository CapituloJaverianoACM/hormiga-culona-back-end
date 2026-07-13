import asyncio
import os

import pytest
from dotenv import load_dotenv

from AI.agents.query_agent import queryAgent
from AI.open_ai_client import OpenAiClient
from scripts.database_schema import sql_schema


@pytest.mark.skipif(os.getenv("RUN_LIVE_AGENT_TESTS") != "1", reason="live test")
def test_query_agent_live():
    async def _run():
        load_dotenv()
        database_schema = sql_schema()
        open_ai_client = OpenAiClient()
        query_agent = queryAgent()
        await query_agent.create_agent(open_ai_client, database_schema)
        response = await query_agent.run_agent(
            "podrias hacer una query que me diga la primera fila de las 2 bases de datos?"
        )
        assert response

    asyncio.run(_run())