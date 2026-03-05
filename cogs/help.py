import discord
from discord.ext import commands

# ── Mikasa theme ──
MIKASA_COLOR = 0xE91E63
MIKASA_ICON = "https://i.imgur.com/0GfnTBq.png"


# ── Category Embeds ──────────────────────────────────────────

def _actions_embed() -> discord.Embed:
    embed = discord.Embed(
        title="⚔️  Actions",
        description="Send anime GIF reactions to other users!",
        color=0xFF69B4,
    )
    actions = [
        "kiss", "lick", "hug", "pat", "poke", "slap", "smack", "dance",
        "cuddle", "thumbsup", "kill", "wave", "tickle", "shoot", "punch",
        "kick", "handhold", "bite", "airkiss", "smile"
    ]
    embed.add_field(
        name="📝  Usage",
        value="`Mikasa <action> @user`",
        inline=False,
    )
    embed.add_field(
        name="🎯  Available Actions",
        value=" ".join(f"`{a}`" for a in actions),
        inline=False,
    )
    embed.add_field(
        name="⏱️  Cooldown",
        value="3 seconds per command",
        inline=False,
    )
    embed.set_footer(text="Mikasa Actions", icon_url=MIKASA_ICON)
    return embed


def _economy_embed() -> discord.Embed:
    embed = discord.Embed(
        title="💰  Economy",
        description="Earn, bet, and trade Mikasa Cash!",
        color=0xFFD700,
    )
    cmds = [
        ("💵  `Mikasa cash`", "Check your balance *(5s cooldown)*"),
        ("🪙  `Mikasa cf <amount> <heads/tails>`", "Coin flip bet *(3s cooldown)*"),
        ("💸  `Mikasa give @user <amount>`", "Give cash to someone *(10s cooldown)*"),
        ("🏦  `Mikasa transfer @user <amount>`", "Owner-only: mint cash *(10s cooldown)*"),
        ("🏆  `Mikasa top`", "Top 10 leaderboard *(10s cooldown)*"),
    ]
    for name, value in cmds:
        embed.add_field(name=name, value=value, inline=False)
    embed.set_footer(text="Mikasa Economy", icon_url=MIKASA_ICON)
    return embed


def _games_embed() -> discord.Embed:
    embed = discord.Embed(
        title="🎲  Games",
        description="Party games for your server!",
        color=0x3498DB,
    )
    embed.add_field(
        name="🎮  `Mikasa tnd @user`",
        value="Start a **Truth, Dare, or Situation** game with interactive buttons.",
        inline=False,
    )
    embed.add_field(
        name="📛  Aliases",
        value="`truthdare`, `truthdaregame`",
        inline=False,
    )
    embed.set_footer(text="Mikasa Games", icon_url=MIKASA_ICON)
    return embed


def _chat_embed() -> discord.Embed:
    embed = discord.Embed(
        title="💬  Chat",
        description="AI-powered conversation with Mikasa! *(Owner only)*",
        color=0xE91E63,
    )
    embed.add_field(
        name="🌸  `Mikasa suno <message>`",
        value="Chat with Mikasa using AI.",
        inline=False,
    )
    embed.add_field(
        name="🧠  `Mikasa changeAI <model>`",
        value=(
            "Switch between AI models.\n"
            "Available: `gemini-flash` (default), `gemini-pro`, `gpt-4o`, `gpt-4o-mini`, `grok`, `grok-3`"
        ),
        inline=False,
    )
    embed.set_footer(text="Mikasa Chat  •  Owner only", icon_url=MIKASA_ICON)
    return embed


CATEGORY_EMBEDS = {
    "actions": _actions_embed,
    "economy": _economy_embed,
    "games": _games_embed,
    "chat": _chat_embed,
}


# ── Select Menu View ────────────────────────────────────────

class HelpSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Actions", value="actions", emoji="⚔️", description="Anime GIF reactions"),
            discord.SelectOption(label="Economy", value="economy", emoji="💰", description="Mikasa Cash system"),
            discord.SelectOption(label="Games", value="games", emoji="🎲", description="Truth, Dare & more"),
            discord.SelectOption(label="Chat", value="chat", emoji="💬", description="Talk with Mikasa"),
        ]
        super().__init__(placeholder="Choose a category…", options=options)

    async def callback(self, interaction: discord.Interaction):
        embed_fn = CATEGORY_EMBEDS[self.values[0]]
        await interaction.response.edit_message(embed=embed_fn(), view=self.view)


class HelpView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)
        self.add_item(HelpSelect())


# ── Cog ─────────────────────────────────────────────────────

class HelpCog(commands.Cog, name="Help"):
    """Interactive help menu with category dropdown."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="bothelp", aliases=["help"])
    async def show_help(self, ctx: commands.Context):
        """Shows an interactive help menu."""
        embed = discord.Embed(
            title="🌸  Mikasa Help",
            description=(
                "Hey there! I'm **Mikasa** — your anime bot companion.\n\n"
                "Use the **dropdown** below to explore my commands!\n\n"
                "**📂  Categories**\n"
                "⚔️ Actions  •  💰 Economy  •  🎲 Games  •  💬 Chat"
            ),
            color=MIKASA_COLOR,
        )
        embed.set_thumbnail(url=MIKASA_ICON)
        embed.set_footer(text="Mikasa Bot  •  Use 'Mikasa' as prefix", icon_url=MIKASA_ICON)
        await ctx.send(embed=embed, view=HelpView())


async def setup(bot: commands.Bot):
    await bot.add_cog(HelpCog(bot))
