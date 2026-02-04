# Keep In Mind
Though Telegram allows file uploads, it is not intended to be used as cloud storage. Your files could be lost at any time. Don't rely on this project (or any similar ones) for storing important files on Telegram. Storing large amounts of files on this **could result in Telegram deleting your files or banning you, proceed at your own risk**.

# Telegram Drop (Local Web UI)
A local web app that lets you drag-and-drop files and send them to a Telegram channel, plus download recent uploads.

Though I demonstrated Discord in the video too, I haven't included the code here. While I believe that storing your OWN files on Discord does NOT violate TOS, I think that spreading the code to do so might. Idk I'm trying to not actually get banned :)

## Usage and How to Run
### Requirements
- Python - I used 3.10.12
- A non-negligible amount of memory if you plan to upload very large files.


### To Run (Web UI)
Before running this, I recommend creating a virtual environment in Python.

- (optional) Create a venv with `python -m venv <your-env-name>`
- Create `Telegram/.env` and fill in the variables with appropriate values. Here's a description of these values and where you can get them from:
    - `APP_ID` and `APP_HASH`: You can get these from https://my.telegram.org/myapp. **AGAIN, storing large amounts of files could get you banned. So be careful and take precautions if you care about losing your account.**
    - `CHANNEL_LINK`: the link to your Telegram channel.
    - `SESSION_NAME`: this can be whatever you want, just the name that will be used for the file storing details of your Telegram session.
- Run `pip install -r requirements.txt`.
- Run `python Telegram/main.py`
- Open `http://127.0.0.1:5000` in your browser.

## Known Issues
Uploading large files to Telegram (more than ~3GB) may result in degraded performance or the system
killing the process for using too much memory. This is probably my fault. I found the behavior of memory management in Python is a bit strange, even calling gc.collect() after clearing the buffer doesn't always seem to work. It could also be an issue with the LRU cache I implemented... I don't have the patience to wait 20 minutes for it to crash and then debug, especially because the vast majority of my files are pretty small.

Error handling is somewhat lacking. If Telegram uploads fail, you'll probably see message in console, but it won't retry. Worst case, you can delete whatever file you were trying to upload and try again.

