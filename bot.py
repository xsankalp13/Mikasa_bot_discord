import discord
from discord.ext import commands
import server
import os
from commands import (  # Import all action commands
    kiss, lick, hug, pat, poke,
    nuzzle, slap, smack, dance,
    cuddle, thumbsup, kill, wave, tickle, 
    stab, shoot,punch, kick, handhold,
    love, bite, airkiss, spank, suicide
)

from coinflip import check_balance, coinflip, give_cash    # Import coin flip commands
from chat import chat  # Import the chat command
from balances import get_top_balances, transfer_cash  # Import the get_top_balances function

# Set up intents
intents = discord.Intents.default()
intents.message_content = True  # Allows the bot to read message content (required for commands)

# Set up the bot command prefix
bot = commands.Bot(command_prefix=["Mikasa ","mikasa "], intents=intents)


#coinflip commands
bot.add_command(check_balance)
bot.add_command(coinflip)
bot.add_command(give_cash)

# Define the transfer command
bot.add_command(transfer_cash)

# Define the top command
bot.add_command(get_top_balances)


# Add the chat command to the bot
bot.add_command(chat)  

@bot.event
async def on_ready():
    print(f"We have logged in as {bot.user}")

@bot.command(name="bothelp")
async def bot_help(ctx):
    """Provides information about the available commands."""
    embed = discord.Embed(
        title="Mikasa Help",
        description="Here are the available commands for Mikasa!",
        color=discord.Color.blue()
    )
    embed.add_field(name="Mikasa kiss @user", value="Sends a kiss GIF and lets everyone know you kissed the tagged user.", inline=False)
    embed.add_field(name="Mikasa lick @user", value="Sends a lick GIF and lets everyone know you licked the tagged user.", inline=False)
    embed.add_field(name="Mikasa hug @user", value="Sends a hug GIF and lets everyone know you hugged the tagged user.", inline=False)
    embed.add_field(name="Mikasa pat @user", value="Sends a pat GIF and lets everyone know you patted the tagged user.", inline=False)
    embed.add_field(name="Mikasa poke @user", value="Sends a poke GIF and lets everyone know you poked the tagged user.", inline=False)
    embed.add_field(name="Mikasa nuzzle @user", value="Sends a nuzzle GIF and lets everyone know you nuzzled the tagged user.", inline=False)
    embed.add_field(name="Mikasa slap @user", value="Sends a slap GIF and lets everyone know you slapped the tagged user.", inline=False)
    embed.add_field(name="Mikasa smack @user", value="Sends a smack GIF and lets everyone know you smacked the tagged user.", inline=False)
    embed.add_field(name="Mikasa dance @user", value="Sends a dance GIF and lets everyone know you danced with the tagged user.", inline=False)
    embed.add_field(name="Mikasa cuddle @user", value="Sends a cuddle GIF and lets everyone know you cuddled with the tagged user.", inline=False)
    embed.add_field(name="Mikasa thumbs up @user", value="Sends a thumbs up GIF and lets everyone know you gave a thumbs up to the tagged user.", inline=False)
    # Add more fields for other actions as needed
    embed.set_footer(text="Use these commands by typing 'Mikasa' followed by the command name.")
    await ctx.send(embed=embed)

# Add the imported commands to the bot
bot.add_command(kiss)
bot.add_command(lick)
bot.add_command(hug)
bot.add_command(pat)
bot.add_command(poke)
bot.add_command(nuzzle)
bot.add_command(slap)
bot.add_command(smack)
bot.add_command(dance)
bot.add_command(cuddle)
bot.add_command(thumbsup)
bot.add_command(kill)
bot.add_command(wave)
bot.add_command(tickle)
bot.add_command(stab)
bot.add_command(shoot)
bot.add_command(punch)
bot.add_command(kick)
bot.add_command(handhold)
bot.add_command(love)
bot.add_command(bite)
bot.add_command(airkiss)
bot.add_command(spank)
bot.add_command(suicide)






# Run the Server
server.keep_alive()


# Run the bot
bot.run(os.environ['DISCORD_TOKEN'])
