from logging import getLogger
from asyncio import wait_for
from asyncio import TimeoutError
from asyncio import sleep
from getpass import getuser
from fastapi import WebSocket
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai import Agent
from pydantic_ai.messages import ModelResponse
from pydantic_ai.messages import ModelRequest
from pydantic_ai.messages import TextPart
from typing import Dict, List, Any
from typing import AsyncGenerator
from uuid import uuid4

logger = getLogger("bruhh.deamon.daemon")


class _ModelResponse(ModelResponse):
    incomplete: bool = False


class Daemon:
    def __init__(self):
        logger.info("[daemon] Initializing...")
        self.message_history: Dict[str, List[Any]] = {}

    async def run_forever(self):
        """
        Background task that runs indefinitely.
        """
        while True:
            try:
                logger.info(f"[daemon]: running main loop with user: {getuser()}")
                await self.check_on_backgrounds()
                await self.notify_user()
            except Exception as _:
                logger.exception("[daemon]: main loop failed")
            await sleep(5)

    async def health_check(self):
        """
        Example of a health check.
        """
        logger.info("[daemon] Running health check...")

    async def check_on_backgrounds(self):
        """
        Example of a background task.
        """
        logger.info("[daemon] Checking on backgrounds...")

    async def notify_user(self):
        """
        Example of a notification.
        """
        logger.info("[daemon] Notifying user...")

    async def ws_handler(self, websocket: WebSocket):
        """
        Example of a websocket handler.
        """
        logger.info("[daemon]: Handling user...")
        await websocket.accept()
        self.model = OpenAIModel(model_name="deepseek-r1:14b", base_url="http://localhost:11434/v1", api_key="some-key")
        system_prompt = """
        You are the assistant. we call you bruhh, you are an expert and currently you are running in a daemon mode.
        meaning you are on a local machine and client is the users that are using the machine.
        Always remember to responsd in the same language as user, be short and concise, no mombo jumbo. be friendly like
        a Bro.
        
        Ask questions when it comes to technical topic, like when you are not sure about what user actually needs.
        you will develop things toghether with the user, so try to understand them as much as you can.
        
        The users are the professionals developers, they are expercinced and do this for their living, 
        so you should try to reach their standards. you should as valuable as a google engieer is.
        """
        session_id = str(uuid4())
        self.message_history[session_id] = []
        agent = Agent(model=self.model, system_prompt=system_prompt)
        while True:
            try:
                data = await websocket.receive_text()
                logger.info(f"[daemon]: received data: {data}")
                hist = self.message_history[session_id]
                async for response in self.stream_response(agent=agent, input=data, hist=hist):
                    client_response = await self.communicate(websocket, response)
                    if client_response:
                        logger.info(f"[daemon]: received response: {response}")
                        break
                await websocket.send_text("bruhh:EOF/Interrupted")
            except Exception as _:
                logger.exception("[daemon] User handler failed")
                break

    async def stream_response(
        self, input: str, agent: Agent, hist: List[ModelResponse | ModelRequest]
    ) -> AsyncGenerator[str, None]:
        """
        Example of a streaming response.
        """
        logger.info("[daemon]: streaming response...")
        async with agent.run_stream(user_prompt=input, message_history=hist) as response:
            async for chunk in response.stream():
                logger.info(f"[daemon]: streaming chunk, len: {len(chunk)}")
                yield chunk

            new_hist = response.all_messages()
            hist.clear()
            hist.extend(new_hist)
        logger.info("[daemon]: streaming response complete")

    async def communicate(self, websocket: WebSocket, response: str) -> bool | str:
        """
        If interrupted, stop sending the return value.
        """
        await websocket.send_text(response)
        try:
            data = await wait_for(websocket.receive_text(), timeout=0.05)
            return data
        except TimeoutError:
            return False
