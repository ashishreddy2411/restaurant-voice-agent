"""
Quick diagnostic — run this BEFORE starting the full agent to confirm
Azure OpenAI is wired correctly via the LiveKit plugin.

Usage:
    python test_llm.py
"""
import asyncio
import logging
import os

import certifi
os.environ.setdefault("SSL_CERT_FILE", certifi.where())

from dotenv import load_dotenv
load_dotenv()

from livekit.agents.llm import ChatContext
from livekit.plugins import openai

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("test-llm")


async def main() -> None:
    deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-5.2-chat")
    logger.info(f"Testing Azure deployment: {deployment}")

    llm = openai.LLM.with_azure(
        azure_deployment=deployment,
        api_version=os.environ.get("OPENAI_API_VERSION", "2024-10-01-preview"),
    )

    ctx = ChatContext()
    ctx.add_message(role="user", content="Say exactly: Azure LLM is working correctly")

    logger.info("Sending request...")
    stream = llm.chat(chat_ctx=ctx)

    text = []
    async for chunk in stream:
        if chunk.delta and chunk.delta.content:
            text.append(chunk.delta.content)
            print(chunk.delta.content, end="", flush=True)

    print()
    logger.info(f"Full response: {''.join(text)}")
    await llm.aclose()


if __name__ == "__main__":
    asyncio.run(main())
