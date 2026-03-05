import discord
from discord.ext import commands
import asyncio
import config  # validates .env on import
import server

# ── Mikasa theme color ──
MIKASA_COLOR = 0xE91E63  # vibrant pink/rose

# Set up intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # Required for nickname sync (on_member_update)

# Set up the bot — disable default help command
bot = commands.Bot(
    command_prefix=["Mikasa ", "mikasa "],
    intents=intents,
    help_command=None,  # We use our own interactive help
)

# List of cogs to load
COGS = [
    "cogs.actions",
    "cogs.economy",
    "cogs.games",
    "cogs.chat",
    "cogs.help",
    "cogs.errors",
]


@bot.event
async def on_ready():
    print(f"We have logged in as {bot.user}")


async def main():
    async with bot:
        for cog in COGS:
            await bot.load_extension(cog)
            print(f"Loaded cog: {cog}")
        # Start the keep-alive server
        server.keep_alive()
        # Run the bot
        await bot.start(config.DISCORD_TOKEN)


asyncio.run(main())
