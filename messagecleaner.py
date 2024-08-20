# telegram message cleaner (c) t.me/ryukohk
# github.com/helloryuko/messagecleaner
#
# a cute and fast script to delete messages from multiple chats
#
# how to use?
# ├ create a config file config.json (see example below)
# ├ run the script
#
# example config file: config.example.json
"""
{
    "api_id": 123456,
    "api_hash": "abcdef1234567890",

    "chats": [
        "@stalkers",
        "@CryptoBotRussian",
        -1001833869332
    ]
}
"""
# for more info on the config file and
# possible values, check out the comments
# in the `Config` class a little bit below
#
# dependencies:
# ├ telethon: interacting with the telegram api
# ├ msgspec: fast json file parsing
# ├ rich: fancy console output
#
# why is it so fast?
# ├ utilizes asyncio tasks to perform multiple
#   requests in parallel
# ├ uses chunked deletion
#   (up to 500 messages at a time!)
# ├ uses custom search request to fetch messages
#   instead of using iter_messages (or even 
#   get_messages), which is notoriously
#   known to be slow

from telethon import TelegramClient
from telethon.tl import types, functions

from typing import List, Callable
from msgspec import json, Struct, ValidationError, DecodeError

import asyncio
import utils

from rich.console import Console
console = Console()

# --- #

SUCCESS = "[bold green]✓[/] "
FAIL = "[bold red]✗[/] "
QUESTION = "[bold blue]>[/] "

CONFIG_FILE = "config.json"

# --- #

# so, the reason behind this is that
# Python doesn't have "references" nor
# "pointers" as in C/C++. so, we need
# to use a class to store the value.
# this way the value becomes "immutable"
# and can be passed around like a reference.

# more on this:
# https://stackoverflow.com/questions/986006

class int_wrapper:
    value: int = 0
    def increment(self, amount: int = 1):
        self.value += amount

# --- #

class Config(Struct):
    # MANDATORY: values from https://api.telegram.org
    api_id: int
    api_hash: str 

    chats: List[int | str] # list of chats to clean

    session_file: str = "telegram" # which session file to use
    remove_from: int | str = "me" # who to remove messages from
    query: str = "" # requires message to contain this string, empty = search all

    chunk_size: int = 500 # amount of messages to delete per request
    delete_threads: int = 10 # amount of parallel delete requests
    search_threads: int = 5 # amount of parallel search requests

# --- #

async def perform_search(
    client: TelegramClient,
    chat_id: int,
    from_id: int,
    query: str,
    search_threads: int,
    on_progress: Callable[[int], None] = None
):
    messages = []

    offset = 0
    while True:
        async def _task(offset):
            ret = await client(functions.messages.SearchRequest(
                peer=chat_id, from_id=from_id, add_offset=offset, q=query,
                filter=types.InputMessagesFilterEmpty(), offset_id=0, min_date=None, max_date=None, limit=1000000, max_id=0, min_id=0, hash=0
            ))

            on_progress(len(ret.messages))

            return ret

        gather = await asyncio.gather(*[
            _task(i) for i in range(
                offset, offset + search_threads * 100, 100
            )
        ])

        for request in gather:
            messages.extend([ message.id for message in request.messages ])

        # --- #

        messages_gathered_count = sum(
            [ len(request.messages) for request in gather ]
        )

        if messages_gathered_count < search_threads * 100:
            break

        offset += messages_gathered_count

    return messages

# --- #

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

            # This allows the use of comments in config files.
            config_string = ""
            for line in f.readlines():
                config_string += line.split("//")[0]
                
            config = json.decode(config_string, type=Config)
    except FileNotFoundError:
        console.print(FAIL + "Config file not found.")
        exit(1)
    except (ValidationError, DecodeError) as e:
        console.print(FAIL + f"Invalid config file: {str(e).lower()}")
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

    # --- #

    user, remove_from, chats = await asyncio.gather(
        client.get_me(),
        client.get_entity(config.remove_from),
        asyncio.gather(*[ client.get_entity(chat) for chat in config.chats ])
    )

    console.print(f"[bold green]User:[/] {user.first_name} [grey30]({user.id})[/]")
    console.print(f"[bold green]Removing from:[/] {remove_from.first_name} [grey30]({remove_from.id})[/]")

    console.print("[bold green]Chats:[/]")
    for chat in chats:
        console.print(f"[bold green]├[/] {chat.title} [grey30]({chat.id})[/]")

    # --- #

    with console.status('Fetching messages') as status:
        messages = {}
        counter = int_wrapper()

        for chat in chats:
            task = asyncio.create_task(perform_search(
                client,

                chat.id,
                remove_from,
                config.query,
                config.search_threads,

                on_progress=lambda count: counter.increment(count)
            ))

            while not task.done():
                await asyncio.sleep(0.1)
                status.update(f"Fetching messages [grey30]{ counter.value }[/]")

            messages[chat.id] = task.result()
                
    console.print(SUCCESS + f"Gathered {sum(len(messages[chat]) for chat in messages)} messages")

    with console.status('Creating message chunks') as status:
        chunks = []
        for chat, messages_list in messages.items():
            for chunk in utils.chunk_by_size(messages_list, config.chunk_size):
                chunks.append((chat, chunk))
        
    console.print(SUCCESS + f"Created {len(chunks)} chunks")

    with console.status('Creating tasks') as status:
        counter = int_wrapper()

        async def _task(chunk_of_chunks, counter):
            for chunk in chunk_of_chunks:
                await client.delete_messages(chunk[0], chunk[1])
                counter.value += len(chunk[1])

        tasks = [
            asyncio.create_task(_task(chunk, counter))
            for chunk in utils.chunk_by_amount(chunks, config.delete_threads)
        ]

    console.print(SUCCESS + f"Created {len(tasks)} tasks")
    
    with console.status(f'Deleting messages [grey30]{ counter.value }/{ len(messages) }[/]') as status:
        gather = asyncio.gather(*tasks)

        while not gather.done():
            await asyncio.sleep(0.1)
            status.update(f"deleting messages [grey30]{ counter.value }/{ len(messages) }[/]")

    console.print(SUCCESS + f"Deleted {counter.value} messages")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print(FAIL + "Aborted.")
        exit(1)
    except Exception as e:
        console.print(FAIL + f"Unexpected error: {str(e)}")
        exit(1)