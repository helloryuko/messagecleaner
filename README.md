<img src="https://files.catbox.moe/blq1oq.gif" width="100%"></img>

<div align='center'>
  telegram message cleaner
</div>

<div align='center'>
  <a href='https://t.me/run1t'>contact me</a>
</div>

<br/>

a cute and fast script to delete messages from multiple chats

### how to use?

1. `git clone` this repo
    - or just download it as a zip, i don't care
2. install the requirements
    - `pip install .`
    - ...or `poetry install` if you're cute irl
3. create a config file `messagecleaner.json`
    - see example: `messagecleaner.example.json`
4. run the script

for more info on the config file and possible values, check out the comments in the `Config` classbelow

### why is it so fast?

- utilizes asyncio tasks to perform multiple requests in parallel
  - why even use async libraries if you don't do that?
- uses chunked deletion
  - up to 500 messages at a time!
- uses custom search request to fetch messages
  - `iter_messages` (and her sister `get_messages`) is notoriously known to be slow 

### dependencies

- [telethon](https://github.com/LonamiWebs/Telethon) - interacting with the telegram api
- [msgspec](https://github.com/jcrist/msgspec) - fast json file parsing
- [rich](https://github.com/willmcgugan/rich) - fancy console output