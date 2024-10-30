import discord
from discord.ext import commands
import random
from balances import read_balances, write_balances

# File to store user balances
BALANCE_FILE = "balances.txt"

# Command to check balance or give initial 100k if user is new
@commands.command(name="cash")
async def check_balance(ctx):
    user_id = str(ctx.author.id)
    balances = read_balances()

    if user_id not in balances:
        # Store user info in a dict
        balances[user_id] = {"nickname": ctx.author.display_name, "money": 100000}
        write_balances(balances)
        await ctx.send(f"Welcome, {ctx.author.mention}! 🎉 You have been given an initial cash of 100k!")
    else:
        await ctx.send(f"{ctx.author.mention}, you have {balances[user_id]['money']:,} cash available.")

# Command to place a bet on heads/tails with the specified amount
@commands.command(name="cf")
async def coinflip(ctx, amount: int, side: str = "heads"):
    user_id = str(ctx.author.id)
    balances = read_balances()

    # Ensure user has an initial balance if not already set
    if user_id not in balances:
        balances[user_id] = {"nickname": ctx.author.display_name, "money": 100000}
        write_balances(balances)
        await ctx.send(f"Welcome, {ctx.author.mention}! 🎉 You have been given an initial cash of 100k!")

    # Check if user has enough money
    if balances[user_id]['money'] < amount:
        await ctx.send(f"{ctx.author.mention}, you don’t have enough cash to bet {amount}!")
        return

    # Default side to 'heads' if not specified
    side = side.lower()
    if side not in ["heads", "tails"]:
        side = "heads"

    # Perform the coin flip
    flip_result = random.choice(["heads", "tails"])
    if flip_result == side:
        balances[user_id]['money'] += amount  # Win: Double the money
        result_message = f"🪙 It's {flip_result}! You won {amount} cash, {ctx.author.mention}! 🎉"
    else:
        balances[user_id]['money'] -= amount  # Lose: Deduct the money
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
    if user_id not in balances or balances[user_id]['money'] < amount:
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
            balances[user_id]['money'] -= amount
            balances[recipient_id] = balances.get(recipient_id, {"nickname": user.display_name, "money": 0})
            balances[recipient_id]['money'] += amount
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
