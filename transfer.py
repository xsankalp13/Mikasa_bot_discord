# transfer.py

import discord
from discord.ext import commands
from discord.ui import Button, View
from balances import update_balance

class TransferCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Transfer command
    @commands.command(name="transfer")
    async def transfer(self, ctx, user: discord.Member, amount: int):
        """Transfers cash to a user after confirmation."""
        # Only allow transfer if the user ID matches your specified master ID
        if ctx.author.id != 560132810556309525:
            await ctx.send("You don't have permission to use this command.")
            return

        # Define confirmation and cancellation buttons
        confirm_button = Button(label="Confirm", style=discord.ButtonStyle.success)
        cancel_button = Button(label="Cancel", style=discord.ButtonStyle.danger)

        async def confirm_callback(interaction):
            if interaction.user == ctx.author:
                # Update the user's balance after confirmation
                update_balance(user, amount)
                await interaction.response.edit_message(content=f"{amount} Mikasa Cash transferred to {user.mention}!", view=None)
            else:
                await interaction.response.send_message("You cannot confirm this action.", ephemeral=True)

        async def cancel_callback(interaction):
            if interaction.user == ctx.author:
                await interaction.response.edit_message(content="Transfer cancelled.", view=None)
            else:
                await interaction.response.send_message("You cannot cancel this action.", ephemeral=True)

        # Assign the callbacks to the buttons
        confirm_button.callback = confirm_callback
        cancel_button.callback = cancel_callback

        # Create the view and add the buttons
        view = View()
        view.add_item(confirm_button)
        view.add_item(cancel_button)

        # Send a message with the confirmation view
        await ctx.send(f"{ctx.author.mention}, confirm transfer of {amount} Mikasa Cash to {user.mention}?", view=view)


# Function to add the Cog to the bot
def setup(bot):
    bot.add_cog(TransferCog(bot))
