import asyncio
import logging
from typing import Any, Optional

from .adapter import ChannelAdapter
from .protocol import PetRequest, PetResponse, ChannelType

logger = logging.getLogger(__name__)


class CLIAdapter(ChannelAdapter):
    """命令行终端 — 最基础的接入方式, 开发调试用"""

    def __init__(self, user_id: str = "local_user"):
        super().__init__()
        self._user_id = user_id
        self._session_id = ""

    @property
    def channel_name(self) -> str:
        return ChannelType.CLI.value

    def receive(self, raw_input: str) -> PetRequest:
        return PetRequest(
            user_id=self._user_id,
            channel=self.channel_name,
            message_type="text",
            content=raw_input,
            session_id=self._session_id
        )

    def send(self, response: PetResponse):
        print(f"\n{'='*40}")
        print(response.text)
        if response.actions:
            print(f"\nActions: {response.actions}")
        print(f"{'='*40}\n")

    def start(self):
        logger.info("Starting CLI adapter...")
        self._running = True
        asyncio.create_task(self._run_loop())

    async def _run_loop(self):
        """Run CLI input loop"""
        while self._running:
            try:
                user_input = input("You: ").strip()
                if not user_input:
                    continue

                if user_input == "/quit":
                    self.stop()
                    break

                if user_input == "/clear":
                    print("\n" * 50)
                    continue

                if self._message_handler:
                    request = self.receive(user_input)
                    await self._handle_message(request)

            except EOFError:
                logger.info("CLI input ended")
                self.stop()
                break
            except Exception as e:
                logger.error(f"CLI error: {e}")

    def stop(self):
        self._running = False
        logger.info("CLI adapter stopped")
