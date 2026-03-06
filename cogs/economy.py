import discord
from discord.ext import commands
from supabase import create_client, Client, ClientOptions
import httpx
import random
from config import SUPABASE_URL, SUPABASE_KEY

# ── Mikasa theme ──
MIKASA_COLOR = 0xE91E63
GOLD_COLOR = 0xFFD700
MIKASA_ICON = "https://i.imgur.com/0GfnTBq.png"

BOT_OWNER_ID = 560132810556309525
DEFAULT_BALANCE = 100000


class EconomyCog(commands.Cog, name="Economy"):
    """Cog for the Mikasa Cash economy system (Supabase-backed)."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        
        http_client = httpx.Client(
            http2=False,
            limits=httpx.Limits(max_keepalive_connections=5, keepalive_expiry=5.0)
        )
        opts = ClientOptions(httpx_client=http_client)
        self.db: Client = create_client(SUPABASE_URL, SUPABASE_KEY, options=opts)

    # ── helpers ──────────────────────────────────────────────

    def _get_balance(self, user_id: str) -> dict | None:
        res = self.db.table("balances").select("*").eq("user_id", user_id).execute()
        return res.data[0] if res.data else None

    def _upsert_balance(self, user_id: str, nickname: str, money: int):
        self.db.table("balances").upsert({
            "user_id": user_id,
            "nickname": nickname,
            "money": money,
        }).execute()

    def _ensure_user(self, user_id: str, nickname: str) -> dict:
        row = self._get_balance(user_id)
        if row is None:
            self._upsert_balance(user_id, nickname, DEFAULT_BALANCE)
            return {"user_id": user_id, "nickname": nickname, "money": DEFAULT_BALANCE}
        return row

    # ── nickname sync ────────────────────────────────────────

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.display_name != after.display_name:
            row = self._get_balance(str(after.id))
            if row is not None:
                self.db.table("balances").update({
                    "nickname": after.display_name,
                }).eq("user_id", str(after.id)).execute()

    # ── commands ─────────────────────────────────────────────

    @commands.command(name="cash")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def check_balance(self, ctx: commands.Context):
        """Check your Mikasa Cash balance."""
        user_id = str(ctx.author.id)
        row = self._get_balance(user_id)

        if row is None:
            self._upsert_balance(user_id, ctx.author.display_name, DEFAULT_BALANCE)
            embed = discord.Embed(
                title="🎉  Welcome to Mikasa Cash!",
                description=(
                    f"Hey {ctx.author.mention}!\n"
                    f"You've been credited with an initial balance of **{DEFAULT_BALANCE:,}** 💰\n\n"
                    f"Use `Mikasa cf` to gamble or `Mikasa give` to share!"
                ),
                color=GOLD_COLOR,
            )
        else:
            embed = discord.Embed(
                title="💰  Mikasa Cash Balance",
                color=MIKASA_COLOR,
            )
            embed.add_field(name="👤  User", value=ctx.author.mention, inline=True)
            embed.add_field(name="💵  Balance", value=f"**{row['money']:,}**", inline=True)

        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        embed.set_footer(text="Mikasa Economy", icon_url=MIKASA_ICON)
        await ctx.send(embed=embed)

    @commands.command(name="cf")
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def coinflip(self, ctx: commands.Context, amount: int, side: str = "heads"):
        """Flip a coin and bet your Mikasa Cash! Usage: Mikasa cf <amount> <heads/tails>"""
        user_id = str(ctx.author.id)
        row = self._ensure_user(user_id, ctx.author.display_name)

        if amount <= 0:
            embed = discord.Embed(description="❌  Bet amount must be positive!", color=0xFF0000)
            await ctx.send(embed=embed)
            return

        if row["money"] < amount:
            embed = discord.Embed(
                description=f"❌  {ctx.author.mention}, you don't have enough cash to bet **{amount:,}**!",
                color=0xFF0000,
            )
            await ctx.send(embed=embed)
            return

        side = side.lower()
        if side not in ("heads", "tails"):
            side = "heads"

        flip_result = random.choice(["heads", "tails"])
        won = flip_result == side

        if won:
            new_money = row["money"] + amount
            embed = discord.Embed(
                title="🪙  Coin Flip — You Won! 🎉",
                description=(
                    f"**Result:** {flip_result.capitalize()}\n"
                    f"**Profit:** +{amount:,} 💰\n"
                    f"**New Balance:** {new_money:,}"
                ),
                color=0x2ECC71,
            )
        else:
            new_money = row["money"] - amount
            embed = discord.Embed(
                title="🪙  Coin Flip — You Lost 😢",
                description=(
                    f"**Result:** {flip_result.capitalize()}\n"
                    f"**Lost:** -{amount:,} 💸\n"
                    f"**New Balance:** {new_money:,}"
                ),
                color=0xE74C3C,
            )

        self._upsert_balance(user_id, ctx.author.display_name, new_money)
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        embed.set_footer(text=f"You picked: {side.capitalize()}", icon_url=MIKASA_ICON)
        await ctx.send(embed=embed)

    @commands.command(name="give")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def give_cash(self, ctx: commands.Context, user: discord.Member, amount: int):
        """Give cash to another user with confirmation."""
        giver_id = str(ctx.author.id)
        recipient_id = str(user.id)
        giver_row = self._ensure_user(giver_id, ctx.author.display_name)

        if giver_row["money"] < amount:
            embed = discord.Embed(
                description=f"❌  {ctx.author.mention}, you don't have enough cash to give!",
                color=0xFF0000,
            )
            await ctx.send(embed=embed)
            return

        cog = self

        class ConfirmGive(discord.ui.View):
            @discord.ui.button(label="✅ Confirm", style=discord.ButtonStyle.green)
            async def confirm(self_btn, interaction: discord.Interaction, button: discord.ui.Button):
                if interaction.user != ctx.author:
                    await interaction.response.send_message("Only the initiator can confirm.", ephemeral=True)
                    return
                latest = cog._ensure_user(giver_id, ctx.author.display_name)
                if latest["money"] < amount:
                    await interaction.response.send_message("You no longer have enough cash!", ephemeral=True)
                    self_btn.stop()
                    return
                cog._upsert_balance(giver_id, ctx.author.display_name, latest["money"] - amount)
                recipient_row = cog._ensure_user(recipient_id, user.display_name)
                cog._upsert_balance(recipient_id, user.display_name, recipient_row["money"] + amount)
                embed = discord.Embed(
                    title="💸  Transfer Complete!",
                    description=f"{ctx.author.mention} gave **{amount:,}** cash to {user.mention}",
                    color=0x2ECC71,
                )
                embed.set_footer(text="Mikasa Economy", icon_url=MIKASA_ICON)
                await interaction.response.send_message(embed=embed)
                self_btn.stop()

            @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.red)
            async def cancel(self_btn, interaction: discord.Interaction, button: discord.ui.Button):
                if interaction.user != ctx.author:
                    await interaction.response.send_message("Only the initiator can cancel.", ephemeral=True)
                    return
                embed = discord.Embed(description="Transfer cancelled.", color=0x95A5A6)
                await interaction.response.send_message(embed=embed)
                self_btn.stop()

        confirm_embed = discord.Embed(
            title="💳  Confirm Transfer",
            description=(
                f"**From:** {ctx.author.mention}\n"
                f"**To:** {user.mention}\n"
                f"**Amount:** {amount:,} 💰"
            ),
            color=GOLD_COLOR,
        )
        confirm_embed.set_footer(text="Click Confirm or Cancel below", icon_url=MIKASA_ICON)
        await ctx.send(embed=confirm_embed, view=ConfirmGive())

    @commands.command(name="transfer")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def transfer_cash(self, ctx: commands.Context, user: discord.Member, amount: int):
        """(Owner only) Transfer cash to a user."""
        if ctx.author.id != BOT_OWNER_ID:
            embed = discord.Embed(description="🚫  You don't have permission.", color=0xFF0000)
            await ctx.send(embed=embed)
            return

        if amount <= 0:
            embed = discord.Embed(description="❌  Please enter a valid amount.", color=0xFF0000)
            await ctx.send(embed=embed)
            return

        cog = self
        recipient_id = str(user.id)

        class ConfirmTransfer(discord.ui.View):
            @discord.ui.button(label="✅ Confirm", style=discord.ButtonStyle.green)
            async def confirm(self_btn, interaction: discord.Interaction, button: discord.ui.Button):
                if interaction.user != ctx.author:
                    await interaction.response.send_message("Only the initiator can confirm.", ephemeral=True)
                    return
                recipient_row = cog._ensure_user(recipient_id, user.display_name)
                cog._upsert_balance(recipient_id, user.display_name, recipient_row["money"] + amount)
                embed = discord.Embed(
                    title="🏦  Admin Transfer Complete!",
                    description=f"Credited **{amount:,}** Mikasa Cash to {user.mention}",
                    color=0x2ECC71,
                )
                embed.set_footer(text="Mikasa Economy — Admin", icon_url=MIKASA_ICON)
                await interaction.response.send_message(embed=embed)
                self_btn.stop()

            @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.red)
            async def cancel(self_btn, interaction: discord.Interaction, button: discord.ui.Button):
                if interaction.user != ctx.author:
                    await interaction.response.send_message("Only the initiator can cancel.", ephemeral=True)
                    return
                embed = discord.Embed(description="Transfer cancelled.", color=0x95A5A6)
                await interaction.response.send_message(embed=embed)
                self_btn.stop()

        confirm_embed = discord.Embed(
            title="🏦  Admin Transfer",
            description=(
                f"**To:** {user.mention}\n"
                f"**Amount:** {amount:,} 💰"
            ),
            color=GOLD_COLOR,
        )
        confirm_embed.set_footer(text="Admin action — Confirm or Cancel", icon_url=MIKASA_ICON)
        await ctx.send(embed=confirm_embed, view=ConfirmTransfer())

    @commands.command(name="top")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def get_top_balances(self, ctx: commands.Context):
        """Display the top 10 users with the most Mikasa Cash."""
        res = (
            self.db.table("balances")
            .select("*")
            .order("money", desc=True)
            .limit(10)
            .execute()
        )

        medals = ["🥇", "🥈", "🥉"]
        lines = []
        for rank, row in enumerate(res.data, start=1):
            medal = medals[rank - 1] if rank <= 3 else f"`#{rank}`"
            lines.append(f"{medal}  **{row['nickname']}** — {row['money']:,} 💰")

        embed = discord.Embed(
            title="🏆  Mikasa Cash Leaderboard",
            description="\n".join(lines) if lines else "No users found.",
            color=GOLD_COLOR,
        )
        embed.set_footer(text="Mikasa Economy  •  Top 10", icon_url=MIKASA_ICON)
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(EconomyCog(bot))
