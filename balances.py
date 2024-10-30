import discord
from discord.ext import commands
import os

# File to store user balances
BALANCE_FILE = "balances.txt"
BOT_OWNER_ID = "560132810556309525"  # Replace with your actual Discord ID

# Helper function to read balances from the file
def read_balances():
    balances = {}
    if os.path.exists(BALANCE_FILE):
        with open(BALANCE_FILE, "r") as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) == 3:  # Only process lines with exactly three parts
                    user_id, nickname, money = parts
                    balances[user_id] = {"nickname": nickname, "money": int(money)}
                else:
                    print(f"Warning: Skipping malformed line: {line.strip()}")
    return balances

# Helper function to write balances to the file
def write_balances(balances):
    with open(BALANCE_FILE, "w") as f:
        for user_id, data in balances.items():
            f.write(f"{user_id} {data['nickname']} {data['money']}\n")

# Command to display the top 10 users with the most cash
@commands.command(name="top")
async def get_top_balances(ctx):
    balances = read_balances()
    sorted_balances = sorted(balances.items(), key=lambda x: x[1]['money'], reverse=True)
    top_balances = sorted_balances[:10]

    embed = discord.Embed(title="Top 10 Mikasa Cash Holders 💸", color=discord.Color.gold())
    for rank, (user_id, data) in enumerate(top_balances, start=1):
        embed.add_field(name=f"{rank}. {data['nickname']}", value=f"{data['money']} Mikasa Cash", inline=False)
    await ctx.send(embed=embed)

# Transfer command for the bot owner
@commands.command(name="transfer")
async def transfer_cash(ctx, user: discord.Member, amount: int):
    if str(ctx.author.id) != BOT_OWNER_ID:
        await ctx.send("You don't have permission to use this command.")
        return

    balances = read_balances()
    recipient_id = str(user.id)

    # Ensure amount is valid
    if amount <= 0:
        await ctx.send("Please enter a valid amount.")
        return

    # Confirmation message with button
    class ConfirmTransfer(discord.ui.View):
        @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
        async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user != ctx.author:
                await interaction.response.send_message("Only the initiator can confirm this action.", ephemeral=True)
                return
            
            balances[recipient_id] = balances.get(recipient_id, {"nickname": user.display_name, "money": 0})
            balances[recipient_id]["money"] += amount
            write_balances(balances)

            await interaction.response.send_message(f"{ctx.author.mention} transferred {amount} Mikasa Cash to {user.mention}.")
            self.stop()

        @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
        async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user != ctx.author:
                await interaction.response.send_message("Only the initiator can cancel this action.", ephemeral=True)
                return
            await interaction.response.send_message("Transfer canceled.")
            self.stop()

    await ctx.send(f"{ctx.author.mention} wants to transfer {amount} Mikasa Cash to {user.mention}. Confirm?", view=ConfirmTransfer())
