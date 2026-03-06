import discord
from discord.ext import commands
import aiohttp

# ── Mikasa theme ──
MIKASA_COLOR = 0xE91E63
MIKASA_ICON = "https://i.imgur.com/0GfnTBq.png"  # small Mikasa avatar for footer

# Actions mapping (API and name)
GIF_SOURCES = {
    "kiss": "nekos", "hug": "nekos", "pat": "nekos", "poke": "nekos", "slap": "nekos",
    "dance": "nekos", "cuddle": "nekos", "thumbsup": "nekos", "wave": "nekos", "tickle": "nekos",
    "shoot": "nekos", "punch": "nekos", "handhold": "nekos", "bite": "nekos",
    "airkiss": ("nekos", "blowkiss"),
    "smack": ("nekos", "peck"),
    "lick": "waifu", "kill": "waifu", "kick": "waifu", "smile": "waifu"
}

ACTIONS = list(GIF_SOURCES.keys())

# Emoji hints for common actions
ACTION_EMOJIS = {
    "kiss": "💋", "hug": "🤗", "pat": "🥰", "poke": "👉",
    "slap": "💥", "dance": "💃", "cuddle": "🫂", "thumbsup": "👍",
    "wave": "👋", "tickle": "🤭", "shoot": "🔫", "punch": "👊",
    "handhold": "🤝", "bite": "😬", "airkiss": "😘", "smack": "😳",
    "lick": "👅", "kill": "💀", "kick": "🦶", "smile": "😊",
}



class ActionsCog(commands.Cog, name="Actions"):
    """Cog for all anime action GIF commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.session: aiohttp.ClientSession | None = None
        self._dynamic_commands: list[commands.Command] = []

    async def cog_load(self):
        self.session = aiohttp.ClientSession()
        # Register all action commands
        for action_name in ACTIONS:
            self._add_action_command(action_name)

    async def cog_unload(self):
        if self.session:
            await self.session.close()
        # Remove dynamically added commands
        for cmd in self._dynamic_commands:
            self.bot.remove_command(cmd.name)

    async def _fetch_gif(self, query: str) -> str | None:
        if not self.session:
            return None

        source = GIF_SOURCES.get(query)
        if not source:
            return None

        if isinstance(source, tuple):
            api, endpoint = source
        else:
            api, endpoint = source, query

        try:
            if api == "nekos":
                url = f"https://nekos.best/api/v2/{endpoint}"
                async with self.session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data["results"][0]["url"]
            elif api == "waifu":
                url = f"https://api.waifu.pics/sfw/{endpoint}"
                async with self.session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data["url"]
        except Exception as e:
            print(f"Error fetching GIF from '{api}' for '{endpoint}': {e}")

        return None

    async def _do_action(self, ctx: commands.Context, action: str, user: discord.Member):
        if user == ctx.author:
            embed = discord.Embed(
                description=f"You can't **{action}** yourself, silly! 🫠",
                color=0xFFA500,
            )
            await ctx.send(embed=embed)
            return

        gif_url = await self._fetch_gif(action)
        emoji = ACTION_EMOJIS.get(action, "✨")
        description = f"{emoji}  **{ctx.author.display_name}** {action}s **{user.display_name}**!"

        embed = discord.Embed(description=description, color=MIKASA_COLOR)
        if gif_url:
            embed.set_image(url=gif_url)
        embed.set_footer(text=f"Mikasa Actions  •  {action.capitalize()}", icon_url=MIKASA_ICON)
        await ctx.send(embed=embed)

    def _add_action_command(self, action_name: str):
        cog_self = self  # capture reference

        @commands.command(name=action_name)
        @commands.cooldown(1, 3, commands.BucketType.user)
        async def action_cmd(ctx, user: discord.Member, _action=action_name):
            await cog_self._do_action(ctx, _action, user)

        action_cmd.__doc__ = f"Command to {action_name} another user."
        self.bot.add_command(action_cmd)
        self._dynamic_commands.append(action_cmd)


async def setup(bot: commands.Bot):
    await bot.add_cog(ActionsCog(bot))

