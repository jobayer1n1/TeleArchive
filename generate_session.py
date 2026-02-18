import os
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession
from dotenv import load_dotenv

load_dotenv()

# Get credentials from your .env file
api_id = os.getenv("APP_ID")
api_hash = os.getenv("APP_HASH")

async def main():
    # We initialize the client inside the async function
    client = TelegramClient(StringSession(), api_id, api_hash)
    
    # .start() will prompt for phone/code/2FA in the terminal
    await client.start()
    
    print("\n" + "="*30)
    print("YOUR SESSION STRING:")
    print(client.session.save())
    print("="*30 + "\n")
    
    await client.disconnect()

if __name__ == "__main__":
    # This is the modern way to run an async main function
    asyncio.run(main())