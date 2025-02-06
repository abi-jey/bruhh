import sys
import tty
import termios
import asyncio
import logging
from asyncio import wait_for

import aiohttp
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.box import ROUNDED
from rich.align import Align

# Suppress ResourceWarnings.
import warnings

warnings.filterwarnings("ignore", category=ResourceWarning)

logger = logging.getLogger("bruhh.client")


def render_input_text(text, cursor_pos, cursor_visible):
    """
    Returns a Rich Text object for the input area.
    Inserts a blinking cursor at the cursor_pos if cursor_visible is True.
    """
    prefix = ">> "
    cursor_char = "|" if cursor_visible else " "
    new_text = prefix + text[:cursor_pos] + cursor_char + text[cursor_pos:]
    return Text(new_text, style="bold white on dark_blue")


def render_conversation(conversation, current_input="", cursor_position=None, cursor_visible=True):
    """
    Renders the conversation as a table of message panels,
    and always adds an input panel at the bottom showing the current input.
    """
    if cursor_position is None:
        cursor_position = len(current_input)
    console = Console()
    console_width = console.size.width
    message_width = int(console_width * 2 / 3)

    table = Table.grid(expand=True)
    table.add_column()

    for role, msg in conversation:
        if role == "user":
            user_panel = Panel(
                Text(msg, style="bold blue"),
                title="Me",
                title_align="left",
                border_style="bright_blue",
                box=ROUNDED,
                width=message_width,
            )
            aligned_panel = Align(user_panel, align="left", width=console_width)
        else:
            bot_panel = Panel(
                Text(msg, style="bold green"),
                title="Bruhh",
                title_align="right",
                border_style="green",
                box=ROUNDED,
                width=message_width,
            )
            aligned_panel = Align(bot_panel, align="right", width=console_width)
        table.add_row(aligned_panel)

    input_text = render_input_text(current_input, cursor_position, cursor_visible)
    input_panel = Panel(
        input_text,
        border_style="blue",
        box=ROUNDED,
        title="Input ctrl+c to exit",
        title_align="left",
        expand=True,
    )
    table.add_row(input_panel)

    conversation_panel = Panel(
        table,
        title="Conversation",
        border_style="cyan",
        box=ROUNDED,
        expand=True,
    )
    return conversation_panel


def setup_stdin():
    """Configure stdin for nonblocking, character-by-character input."""
    old_settings = termios.tcgetattr(sys.stdin)
    tty.setcbreak(sys.stdin.fileno())
    return old_settings


def restore_stdin(old_settings):
    """Restore the original terminal settings."""
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)


def update_live(live, state):
    """Refresh the live view using the current state."""
    live.update(
        render_conversation(
            state["conversation"],
            state["current_input"],
            state["cursor_position"],
            state["cursor_visible"],
        )
    )


async def blink_cursor(live, state):
    """
    Background task that toggles the cursor's visibility every 0.5 seconds
    and updates the live view.
    """
    try:
        while True:
            await asyncio.sleep(0.5)
            state["cursor_visible"] = not state["cursor_visible"]
            update_live(live, state)
    except asyncio.CancelledError:
        pass


def handle_keypress(state, live, ws, loop):
    """
    Read one character from stdin and update the state accordingly.
    Handles arrow keys, backspace, enter, and Ctrl+C.
    """
    ch = sys.stdin.read(1)
    if ch == "\x1b":  # Start of an escape sequence.
        seq = sys.stdin.read(2)
        if seq == "[D":  # Left arrow.
            if state["cursor_position"] > 0:
                state["cursor_position"] -= 1
        elif seq == "[C":  # Right arrow.
            if state["cursor_position"] < len(state["current_input"]):
                state["cursor_position"] += 1
    elif ch == "\x03":  # Ctrl+C detected.
        state["conversation"].append(("user", "[Ctrl+C pressed. Exiting.]"))
        update_live(live, state)
        loop.remove_reader(sys.stdin)
        raise KeyboardInterrupt
    elif ch in ("\n", "\r"):  # Enter key.
        if state["current_input"].strip():
            state["conversation"].append(("user", state["current_input"]))
            asyncio.create_task(ws.send_str(state["current_input"]))
        state["current_input"] = ""
        state["cursor_position"] = 0
    elif ch == "\x7f":  # Backspace.
        if state["cursor_position"] > 0:
            state["current_input"] = (
                state["current_input"][: state["cursor_position"] - 1]
                + state["current_input"][state["cursor_position"] :]
            )
            state["cursor_position"] -= 1
    else:
        # Insert any other character at the current cursor position.
        state["current_input"] = (
            state["current_input"][: state["cursor_position"]]
            + ch
            + state["current_input"][state["cursor_position"] :]
        )
        state["cursor_position"] += 1
    update_live(live, state)


class BruhhClient:
    def __init__(self, base_url="http://127.0.0.1:7878"):
        self.base_url = base_url
        self.session = aiohttp.ClientSession()
        self.ws: aiohttp.ClientWebSocketResponse | None = None

    async def close(self):
        if self.ws is not None and not self.ws.closed:
            await self.ws.close()
        if not self.session.closed:
            await self.session.close()

    async def get_health(self) -> dict:
        url = f"{self.base_url}/health"
        logger.info(f"[client]: GET {url}")
        # keep two context managers in otherwise aiohttp will raise an error
        async with self.session, self.session.get(url) as resp:
            resp.raise_for_status()
            return await resp.json()

    async def get_version(self):
        url = f"{self.base_url}/version"
        logger.info(f"[client]: GET {url}")
        async with self.session.get(url) as resp:
            resp.raise_for_status()
            return await resp.json()

    async def connect_cli_user(self, prompt: str = "Hello, world!") -> None:
        """
        Connects via WebSocket and renders a live Rich panel that shows
        the conversation and an input area. Keystrokes from stdin are captured
        (without echoing) and rendered in the input area. Supports in-line editing,
        a blinking cursor, and a Ctrl+C exit handler.
        """
        url = f"{self.base_url}/ws"
        logger.info(f"[client]: WS {url}")

        # Shared state for rendering.
        state = {
            "conversation": [("user", prompt)],
            "current_input": "",
            "cursor_position": 0,
            "cursor_visible": True,
        }

        console = Console()
        loop = asyncio.get_event_loop()
        old_settings = setup_stdin()

        try:
            async with self.session.ws_connect(url) as ws:
                self.ws = ws
                await ws.send_str(prompt)
                with Live(
                    render_conversation(
                        state["conversation"],
                        state["current_input"],
                        state["cursor_position"],
                        state["cursor_visible"],
                    ),
                    console=console,
                    refresh_per_second=20,
                    vertical_overflow="visible",
                ) as live:
                    loop.add_reader(sys.stdin, handle_keypress, state, live, ws, loop)
                    blink_task = asyncio.create_task(blink_cursor(live, state))
                    # Main loop to Handle incoming messages from Daemon, the user input is handled by `handle_keypress`
                    while True:
                        try:
                            res = await wait_for(ws.receive(), timeout=0.5)
                            if res.type == aiohttp.WSMsgType.TEXT:
                                data = res.data
                                if data == "bruhh:EOF/Interrupted":
                                    continue # Skip updating the conversation after receiving this message.
                                # Replace the last bot message if it exists.
                                if state["conversation"] and state["conversation"][-1][0] == "bot":
                                    state["conversation"].pop()
                                state["conversation"].append(("bot", data))
                                update_live(live, state)
                        except asyncio.TimeoutError:
                            pass
                        except asyncio.CancelledError:
                            break
                    blink_task.cancel()
        finally:
            loop.remove_reader(sys.stdin)
            restore_stdin(old_settings)
            logger.info("Websocket closed.")


async def _main():
    client = BruhhClient(base_url="http://127.0.0.1:7878")
    try:
        health = await client.get_health()
        logger.info(f"Health Response: {health}")

        version_data = await client.get_version()
        logger.info(f"Version Response: {version_data}")

        await client.connect_cli_user(prompt="Hey, how are you?")
    except (aiohttp.ClientError, KeyboardInterrupt) as e:
        logger.error(f"Error: {e}")
    finally:
        await client.close()
        await asyncio.sleep(0.1)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(_main())
    except KeyboardInterrupt:
        print("\nExiting...")
