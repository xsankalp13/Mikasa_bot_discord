import discord
from discord.ext import commands
import random

# Define a list of basic responses for simple chat
predefined_responses = [
    "I'm here to help! 😊",
    "What can I do for you today?",
    "Did someone call for me? 😄",
    "I'm just a bot, but I'm here for you!",
    "Tell me what's on your mind!",
    "Oh, hi there! How can I assist you?",
    "Ask away! I'm here to chat. 🌸"
]

def generate_response(message,ctx):
    """
    Basic response generator. 
    Can be expanded for more complex or AI-driven responses.
    """
    message_lower = message.lower()
    
    # Check for love-related messages
    love_phrases = ["i love you", "ily", "i love u", "love you", "i <3 you"]
    if any(phrase in message_lower for phrase in love_phrases):
        if ctx.author.id != 1217740464971579432:
            return f"Hey {ctx.author.mention}, listen carefully I only love Riri ❤️"
        return f"Hey {ctx.author.mention} baby, I love you too! ❤️"

    # Check for other keywords
    if "hello" in message_lower:
        return "Hello! How can I help you today?"
    elif "how are you" in message_lower:
        return "I'm just a bot, but I'm doing great! Thanks for asking. 😊"
    elif "what's up" in message_lower:
        return "Just hanging out, waiting to assist you!"
    else:
        # Return a random response if no specific keywords are found
        return random.choice(predefined_responses)

# Chat command for Mikasa
@commands.command(name="baby")
async def chat(ctx, *, message: str):
    """Command to chat with the bot."""
    # Generate a response based on the input message
    response = generate_response(message,ctx)
    await ctx.send(response)
