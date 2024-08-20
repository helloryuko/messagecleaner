from typing import Callable
from telethon import TelegramClient, errors

# ref: https://github.com/LonamiWebs/Telethon/blob/v1/telethon/client/auth.py#L180
async def auth_flow(
    client: TelegramClient,

    on_number: Callable[[], str],
    on_code: Callable[[], str],
    on_password: Callable[[], str],

    on_incorrect_code: Callable[[], None] = None,
    on_incorrect_password: Callable[[], None] = None,
    on_too_many_attempts: Callable[[], None] = None
):
    number = on_number()
    await client.send_code_request(number)

    is_2fa = False

    attempts = 0
    while attempts < 3:
        code = on_code()
        try:
            await client.sign_in(number, code)
            break
        except errors.SessionPasswordNeededError:
            is_2fa = True
            break
        except (
            errors.PhoneCodeEmptyError,
            errors.PhoneCodeExpiredError,
            errors.PhoneCodeHashEmptyError,
            errors.PhoneCodeInvalidError
        ):
            on_incorrect_code()

        attempts += 1
    else:
        on_too_many_attempts()
        exit(1)

    if is_2fa:
        attempts = 0
        while attempts < 3:
            password = on_password()
            try:
                await client.sign_in(number, password=password)
                break
            except errors.PasswordHashInvalidError:
                on_incorrect_password()
                attempts += 1
        else:
            on_too_many_attempts()
            exit(1)