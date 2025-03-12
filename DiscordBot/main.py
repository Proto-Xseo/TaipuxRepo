import asyncio
import discord
import os
from discord.ext import commands
from dotenv import load_dotenv
from pathlib import Path

# Import database modules
from models.base import init_db, engine
from utils.db import initialize_database, migrate_json_to_db, load_characters_from_json

try:
    # Get absolute path to .env file
    env_path = Path(__file__).parent.absolute() / '.env'
    print(f"Looking for .env file at: {env_path}")
    
    if not env_path.exists():
        raise FileNotFoundError(f".env file not found at {env_path}")
    
    load_dotenv(dotenv_path=env_path)
    
    # Load environment variables
    DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
    SPAWN_CHANNEL_ID = os.getenv("SPAWN_CHANNEL_ID")
    DB_TYPE = os.getenv("DB_TYPE", "sqlite")
    
    if not DISCORD_TOKEN:
        raise ValueError("Missing required environment variable: DISCORD_TOKEN")
    
    # SPAWN_CHANNEL_ID is now optional since it can be set per server
    if SPAWN_CHANNEL_ID:
        SPAWN_CHANNEL_ID = int(SPAWN_CHANNEL_ID)
        print(f"Default Spawn Channel ID: {SPAWN_CHANNEL_ID}")
    
    print("Environment variables loaded successfully:")
    print(f"Database Type: {DB_TYPE}")
    
except Exception as e:
    print(f"Failed to load environment: {str(e)}")
    raise

# Initialize database
print("Initializing database...")
if initialize_database():
    print("Database initialized successfully.")
else:
    print("Failed to initialize database.")

# Bot intents
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.reactions = True
intents.members = True  # Needed for user registration

bot = commands.Bot(command_prefix="t", intents=intents)

bot.remove_command('help')

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    print(f"Bot is in {len(bot.guilds)} guilds")
    
    # Load characters from JSON files
    print("Loading characters from JSON files...")
    characters = load_characters_from_json()
    print(f"Loaded {len(characters)} characters.")
    
    # Migrate data from JSON to database if needed
    if os.path.exists("DiscordBot/utils/users.json"):
        print("Migrating data from JSON to database...")
        if migrate_json_to_db():
            print("Data migration completed successfully.")
        else:
            print("Failed to migrate data.")

# Add the new setup cog to the initial extensions
initial_extensions = [
    "cogs.setup",  # New setup cog
    "cogs.spawn",
    "cogs.claim",
    "cogs.collection",
    "cogs.profile",
    "cogs.archive",
    "cogs.trade",
    "cogs.pve",
    "cogs.leaderboard",
    "cogs.pass",
    "cogs.economy",
    "cogs.lookup",
    "cogs.gacha",
    "cogs.affection",
    "cogs.management",
    "cogs.preview"
]

async def load_extensions():
    for ext in initial_extensions:
        try:
            await bot.load_extension(ext)  
            print(f"✅ Loaded extension: {ext}")
        except Exception as e:
            print(f"❌ Failed to load extension {ext}: {e}")

async def main():
    async with bot:
        await load_extensions()
        await bot.start(os.getenv("DISCORD_TOKEN"))

asyncio.run(main())