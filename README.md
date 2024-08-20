<img src="https://files.catbox.moe/blq1oq.gif" width="100%"></img>

<div align='center'>
  Telegram message cleaner
</div>

<div align='center'>
  <a href='https://t.me/run1t'>Contact me</a>
</div>

<br/>

Digital footprint nuker.

> [!NOTE]  
> The script may look stuck because of the Telegram rate limits.
> Just be patient.

### How to use?

1. `git clone` this repo
    - or just download it as a zip, I don't care
2. Install the requirements
    - `pip install .`
    - ...or `poetry install` if you're cute IRL
3. Create a config file `config.json`
    - see example: `config.example.json`
4. Run the script

Also, this repo includes `get_chats.py` script - it can help you form a list of chats to clean.

For more info on the config file and possible values, check out the comments in the `Config` class

*tss, you can use comments in the config file...*

### Why is it so fast?

- Utilizes asyncio tasks to perform multiple requests in parallel
  - why even use async libraries if you don't do that?
- Uses chunked deletion
  - up to 500 messages at a time!
- Uses custom search requests to fetch messages
  - `iter_messages` (and her sister `get_messages`) is notoriously known to be slow 

### Dependencies

- [telethon](https://github.com/LonamiWebs/Telethon) - interacting with the Telegram API
- [msgspec](https://github.com/jcrist/msgspec) - fast JSON file parsing
- [rich](https://github.com/willmcgugan/rich) - fancy console output