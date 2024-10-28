import discord
from discord.ext import commands
import random
import os

# File to store user balances
BALANCE_FILE = "balances.txt"

# Helper function to read balances from the file
def read_balances():
    balances = {}
    if os.path.exists(BALANCE_FILE):
        with open(BALANCE_FILE, "r") as f:
            for line in f:
                name, money = line.strip().split()
                balances[name] = int(money)
    return balances

# Helper function to write balances to the file
def write_balances(balances):
    with open(BALANCE_FILE, "w") as f:
        for name, money in balances.items():
            f.write(f"{name} {money}\n")

# Command to check balance or give initial 100k if user is new
@commands.command(name="cash")
async def check_balance(ctx):
    user_id = str(ctx.author.id)
    balances = read_balances()

    if user_id not in balances:
        balances[user_id] = 100000  # Grant initial 100k for first-time users
        write_balances(balances)
        await ctx.send(f"Welcome, {ctx.author.mention}! 🎉 You have been given an initial cash of 100k!")
    else:
        await ctx.send(f"{ctx.author.mention}, you have {balances[user_id]:,} cash available.")

# Command to place a bet on heads/tails with the specified amount
@commands.command(name="cf")
async def coinflip(ctx, amount: int, side: str = "heads"):
    user_id = str(ctx.author.id)
    balances = read_balances()

    # Ensure user has an initial balance if not already set
    if user_id not in balances:
        balances[user_id] = 100000  # Give 100k for first-time users
        write_balances(balances)
        await ctx.send(f"Welcome, {ctx.author.mention}! 🎉 You have been given an initial cash of 100k!")

    # Check if user has enough money
    if balances[user_id] < amount:
        await ctx.send(f"{ctx.author.mention}, you don’t have enough cash to bet {amount}!")
        return

    # Default side to 'heads' if not specified
    side = side.lower()
    if side not in ["heads", "tails"]:
        side = "heads"

    # Perform the coin flip
    flip_result = random.choice(["heads", "tails"])
    if flip_result == side:
        balances[user_id] += amount  # Win: Double the money
        result_message = f"🪙 It's {flip_result}! You won {amount} cash, {ctx.author.mention}! 🎉"
    else:
        balances[user_id] -= amount  # Lose: Deduct the money
        result_message = f"🪙 It's {flip_result}. You lost {amount} cash, {ctx.author.mention}. 😢"

    # Update and save the new balance
    write_balances(balances)
    await ctx.send(result_message)

# Command to give cash to another user with confirmation
@commands.command(name="give")
async def give_cash(ctx, user: discord.Member, amount: int):
    user_id = str(ctx.author.id)
    recipient_id = str(user.id)
    balances = read_balances()

    # Ensure the giver has enough balance
    if user_id not in balances or balances[user_id] < amount:
        await ctx.send(f"{ctx.author.mention}, you don't have enough cash to give!")
        return

    # Confirmation message with button
    class ConfirmGive(discord.ui.View):
        @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
        async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user != ctx.author:
                await interaction.response.send_message("Only the initiator can confirm this action.", ephemeral=True)
                return
            # Transfer the amount
            balances[user_id] -= amount
            balances[recipient_id] = balances.get(recipient_id, 0) + amount
            write_balances(balances)
            await interaction.response.send_message(f"{ctx.author.mention} gave {amount} cash to {user.mention}.")
            self.stop()

        @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
        async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user != ctx.author:
                await interaction.response.send_message("Only the initiator can cancel this action.", ephemeral=True)
                return
            await interaction.response.send_message("Cash transfer canceled.")
            self.stop()

    await ctx.send(f"{ctx.author.mention} wants to give {amount} cash to {user.mention}. Confirm?", view=ConfirmGive())
