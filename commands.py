import discord
from discord.ext import commands
from actions import action_response  # Assuming action_response is in a separate module


allowed_users = [560132810556309525, 1217740464971579432, 756042354816712775,763699750846857226]


async def send_action_response(ctx, action, user):
    """Handles sending the action response."""
    if ctx.author.id not in allowed_users:
        print(ctx.author.id)
        await ctx.send(f"Hey {ctx.author.mention} nigga, Only my master can use these commands! 😠")
        return
    if user == ctx.author:
        await ctx.send(f"You can't {action} yourself!")
        return
    print(user, ctx.author)
    user1 = ctx.author.display_name
    user2 = user.display_name
    message, gif_url = action_response(action, user1, user2)

    if gif_url:
        embed = discord.Embed(description=message)
        embed.set_image(url=gif_url)
        await ctx.send(embed=embed)
    else:
        await ctx.send("We currently do not support this action. Go through Mikasa help 👀")

# Define your command functions for all actions
@commands.command(name="kiss")
async def kiss(ctx, user: discord.Member):
    """Command to kiss another user."""
    await send_action_response(ctx, "kiss", user)

@commands.command(name="lick")
async def lick(ctx, user: discord.Member):
    """Command to lick another user."""
    await send_action_response(ctx, "lick", user)

@commands.command(name="hug")
async def hug(ctx, user: discord.Member):
    """Command to hug another user."""
    await send_action_response(ctx, "hug", user)

@commands.command(name="pat")
async def pat(ctx, user: discord.Member):
    """Command to pat another user."""
    await send_action_response(ctx, "pat", user)

@commands.command(name="poke")
async def poke(ctx, user: discord.Member):
    """Command to poke another user."""
    await send_action_response(ctx, "poke", user)

@commands.command(name="nuzzle")
async def nuzzle(ctx, user: discord.Member):
    """Command to nuzzle another user."""
    await send_action_response(ctx, "nuzzle", user)

@commands.command(name="slap")
async def slap(ctx, user: discord.Member):
    """Command to slap another user."""
    await send_action_response(ctx, "slap", user)

@commands.command(name="smack")
async def smack(ctx, user: discord.Member):
    """Command to smack another user."""
    await send_action_response(ctx, "smack", user)

@commands.command(name="dance")
async def dance(ctx, user: discord.Member):
    """Command to dance with another user."""
    await send_action_response(ctx, "dance", user)

@commands.command(name="cuddle")
async def cuddle(ctx, user: discord.Member):
    """Command to cuddle another user."""
    await send_action_response(ctx, "cuddle", user)

@commands.command(name="thumbsup")
async def thumbsup(ctx, user: discord.Member):
    """Command to give a thumbs up to another user."""
    await send_action_response(ctx, "thumbsup", user)

@commands.command(name="kill")
async def kill(ctx, user: discord.Member):
    """Command kill to another user."""
    await send_action_response(ctx, "kill", user)

@commands.command(name="wave")
async def wave(ctx, user: discord.Member):
    """Command to give a wave to another user."""
    await send_action_response(ctx, "wave", user)

@commands.command(name="tickle")
async def tickle(ctx, user: discord.Member):
    """Command to tickle to another user."""
    await send_action_response(ctx, "tickle", user)

@commands.command(name="stab")
async def stab(ctx, user: discord.Member):
    """Command to stab a another user."""
    await send_action_response(ctx, "stab", user)

@commands.command(name="shoot")
async def shoot(ctx, user: discord.Member):
    """Command to shoot a another user."""
    await send_action_response(ctx, "shoot", user)

@commands.command(name="punch")
async def punch(ctx, user: discord.Member):
    """Command to punch to another user."""
    await send_action_response(ctx, "punch", user)

@commands.command(name="kick")
async def kick(ctx, user: discord.Member):
    """Command to kick to another user."""
    await send_action_response(ctx, "kick", user)

@commands.command(name="handhold")
async def handhold(ctx, user: discord.Member):
    """Command to handhold to another user."""
    await send_action_response(ctx, "handhold", user)

@commands.command(name="love")
async def love(ctx, user: discord.Member):
    """Command to love to another user."""
    await send_action_response(ctx, "love", user)

@commands.command(name="bite")
async def bite(ctx, user: discord.Member):
    """Command to bite to another user."""
    await send_action_response(ctx, "bite", user)

@commands.command(name="airkiss")
async def airkiss(ctx, user: discord.Member):
    """Command to give a airkiss to another user."""
    await send_action_response(ctx, "airkiss", user)

@commands.command(name="spank")
async def spank(ctx, user: discord.Member):
    """Command to spank to another user."""
    await send_action_response(ctx, "spank", user)

@commands.command(name="suicide")
async def suicide(ctx, user: discord.Member):
    """Command to suicide to another user."""
    await send_action_response(ctx, "suicide", user)

# Add more action commands as needed
