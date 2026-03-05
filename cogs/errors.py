import discord
from discord.ext import commands
import traceback

# ── Mikasa theme ──
MIKASA_ICON = "https://i.imgur.com/0GfnTBq.png"


class ErrorsCog(commands.Cog, name="Errors"):
    """Global error handler — catches command errors and sends clean embeds."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        error = getattr(error, "original", error)

        if isinstance(error, commands.CommandNotFound):
            return

        if isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                title="⚠️  Missing Argument",
                description=(
                    f"You're missing the **`{error.param.name}`** argument!\n"
                    f"Type `Mikasa bothelp` for command usage."
                ),
                color=0xF39C12,
            )

        elif isinstance(error, commands.MemberNotFound):
            embed = discord.Embed(
                title="❓  User Not Found",
                description="I couldn't find that user. Make sure to @mention them!",
                color=0xE67E22,
            )

        elif isinstance(error, commands.CommandOnCooldown):
            embed = discord.Embed(
                title="⏳  Slow Down!",
                description=f"Try again in **{error.retry_after:.1f}s**",
                color=0x95A5A6,
            )

        elif isinstance(error, commands.BadArgument):
            embed = discord.Embed(
                title="⚠️  Invalid Argument",
                description=(
                    "One of your arguments is the wrong type.\n"
                    "Type `Mikasa bothelp` for correct usage."
                ),
                color=0xF39C12,
            )

        elif isinstance(error, commands.CheckFailure):
            embed = discord.Embed(
                title="🚫  Permission Denied",
                description="You don't have permission to use this command.",
                color=0xE74C3C,
            )

        else:
            embed = discord.Embed(
                title="💥  Something Went Wrong",
                description="An unexpected error occurred. 😢",
                color=0xE74C3C,
            )
            traceback.print_exception(type(error), error, error.__traceback__)

        embed.set_footer(text="Mikasa", icon_url=MIKASA_ICON)
        await ctx.send(embed=embed, delete_after=15)


async def setup(bot: commands.Bot):
    await bot.add_cog(ErrorsCog(bot))
