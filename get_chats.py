from telethon import TelegramClient
from telethon.tl import types, functions

from msgspec import json, Struct, ValidationError, DecodeError

import asyncio
import utils
import math

from rich.console import Console

import utils.chunk_by_amount
console = Console()

# --- #

SUCCESS = "[bold green]✓[/] "
FAIL = "[bold red]✗[/] "
QUESTION = "[bold blue]>[/] "

CONFIG_FILE = "config.json"

# --- #

class Config(Struct):
    # MANDATORY: values from https://api.telegram.org
    api_id: int
    api_hash: str 

    session_file: str = "telegram" # which session file to use

async def main():
    console.print("[blue bold]Telegram message cleaner") 
    console.print("[blue]https://github.com/helloryuko/messagecleaner")

    # TODO: come up with a way to make this modular
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            # Fuck you, JSON specification.

            # Comments are a valuable syntax to use in ANY
            # configuration file: from describing the data
            # to quickly removing it for testing.

            # This allows the use of comments.
            config_string = ""
            for line in f.readlines():
                config_string += line.split("//")[0]
                
            config = json.decode(config_string, type=Config)
    except FileNotFoundError:
        console.print(FAIL + "Config file not found.")
        exit(1)
    except (ValidationError, DecodeError) as e:
        console.print(FAIL + f"Invalid config file: {str(e)}")
        exit(1)
    
    with console.status('Authorizing') as status:
        client = TelegramClient(
            config.session_file, config.api_id, config.api_hash
        )
       
        await client.connect()

        if not await client.is_user_authorized():
            status.stop()

            await utils.auth_flow(
                client,

                on_number=lambda: console.input(QUESTION + "Enter your phone number: "),
                on_code=lambda: console.input(QUESTION + "Enter the code you received: "),
                on_password=lambda: console.input(QUESTION + "Enter your 2FA: ", password=True),
                
                on_incorrect_code=lambda: console.print(FAIL + "Invalid code."),
                on_incorrect_password=lambda: console.print(FAIL + "Invalid password."),
                on_too_many_attempts=lambda: console.print(FAIL + "Too much unsuccessful attempts.")
            )

    console.print(SUCCESS + "Authorized!")

    user = await client.get_me()
    console.print(f"[bold green]User:[/] {user.first_name} [grey30]({user.id})[/]")

    # --- #

    with console.status("Getting dialogs...") as status:
        dialogs = []

        first_req = await client(functions.messages.GetDialogsRequest(
            offset_date=None, offset_id=0, offset_peer=types.InputPeerEmpty(), limit=100, hash=0, exclude_pinned=False, folder_id=0
        ))

        dialogs.extend(first_req.dialogs)

        if first_req.count > len(first_req.dialogs):
            while True:
                last_message = await client.get_messages(dialogs[-1].peer, limit=1)
                offset_date = last_message[0].date

                result = await client(functions.messages.GetDialogsRequest(
                    offset_peer=types.InputPeerEmpty(), hash=0, exclude_pinned=False, folder_id=0, limit=100, offset_id=0,
                    offset_date=int(offset_date.timestamp())
                ))

                # console.print(f"[bold green]Query:[/] offset_date {offset_date}")

                if len(result.dialogs) == 0:
                    break

                dialogs.extend(result.dialogs) 

    console.print(SUCCESS + f"Found {len(dialogs)} dialogs")

    with console.status("Getting chat info...") as status:
        chats: dict[int, str] = {}

        chunked_dialogs = utils.chunk_by_amount(dialogs, 10)
        
        async def _task(chunk):
            for dialog in chunk:
                entity = None

                if isinstance(dialog.peer, types.PeerChannel):
                    entity = await client.get_entity(dialog.peer)

                    if not (entity.megagroup or entity.gigagroup):
                        continue

                    chats[int("-100" + str(dialog.peer.channel_id))] = entity.title
                elif isinstance(dialog.peer, types.PeerChat):
                    entity = await client.get_entity(dialog.peer)

                    chats[int("-" + str(dialog.peer.chat_id))] = entity.title

                if entity:
                    console.print(f"[bold green]Chat:[/] {entity.title} [grey30]{entity.id}[/]")

        tasks = [
            asyncio.create_task(_task(chunk))
            for chunk in chunked_dialogs
        ]

        await asyncio.gather(*tasks)

    console.print(SUCCESS + f"Filtered {len(chats)} chats")

    with console.status('Writing chats to file...') as status:
        with open("chats.json", "w", encoding="utf-8") as f:
            # Very horrible, but no parser knows how to write comments in JSON.
            f.write(
                "[\n" +
                    "\n".join(
                        f'    {id}, // {title}' for id, title in chats.items()
                    )
                + "\n]"
            )

    console.print(SUCCESS + "Wrote chats to file")
    console.print("! [bold blue]Friendly reminder:[/] you could've left some chats.")
    console.print("  Use various OSINT tools to find more chats to clean.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print(FAIL + "Aborted.")
        exit(1)
    except Exception as e:
        console.print(FAIL + f"Unexpected error: {str(e)}")
        exit(1)