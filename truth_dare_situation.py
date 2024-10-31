import discord
from discord.ext import commands
import random

# Define the lists of R-rated questions and dares
truths = [
     "Type out your wildest fantasy in the chat!",
  "Have you ever sent a risky text to the wrong person? If so, what happened?",
  "What's the most embarrassing thing you've done on a date? Describe it!",
  "Who in this server would you want to kiss? Tag them!",
  "Share the most scandalous photo in your phone (describe it, no need to post!).",
  "What’s the craziest place you’ve gotten intimate? Describe the scene!",
  "What's one thing you wish you could tell your crush but haven't?",
  "What's the most awkward romantic moment you've had? Share the details!",
  "What's a wild secret you've kept from your family?",
  "What’s something you fantasize about that no one knows?",
  "Have you ever lied about your experience level to someone? Share the story!",
  "Have you ever been caught doing something naughty? What happened?",
  "What's something you secretly enjoy but would never admit out loud?",
  "Who was your best kiss? Describe it!",
  "What’s a scandalous thing you wish you could try?",
  "Who here would you want to go on a virtual date with? Tag them and say why!",
  "What’s a personal kink you don’t usually talk about?",
  "What's the naughtiest thing you've done that you'd be embarrassed to admit?",
  "What’s the strangest thing you've been attracted to?",
  "Have you ever had a spicy dream about someone here? Describe it!",
  "What's the naughtiest message you've ever sent?",
  "Have you ever used a dating app just to find a fling? Share what happened!",
  "If you could kiss any celebrity, who would it be?",
  "What’s the most awkward moment you’ve had while flirting?",
  "Have you ever been embarrassed by something you did in front of a crush?"
]

dares = [
    "DM the last person you messaged with a flirty emoji.",
  "Send a playful text to the fifth person in your contacts.",
  "Share your most recent search history in the chat.",
  "Flirt with the bot and tag them in a message!",
  "Send a compliment to someone random in this server.",
  "Send a virtual kiss emoji to someone of your choice here.",
  "Send a spicy pick-up line to the bot.",
  "Make a silly voice memo and post it in the chat!",
  "Share an embarrassing selfie (or describe it if you don’t want to post it!).",
  "React to five random messages in the chat with the kiss emoji 😘.",
  "Change your Discord status to something flirty for the next 5 minutes.",
  "Send a heart emoji to the last person you DM'd.",
  "Post a GIF of how you’re feeling right now.",
  "Send a flirty message to someone online in the server right now.",
  "Send a made-up confession to your crush.",
  "DM a friend and confess your 'feelings' for them, real or not.",
  "Post a romantic song link that you love in the chat.",
  "Use only romantic emojis for your next five messages.",
  "Tag someone in the server you secretly have a crush on.",
  "React to the next five messages you see with a blushing emoji 😊."
]

situations = [
    "Imagine you're stuck in a virtual chat room with your crush here. What's your first message to them?",
  "You have to impress your crush in 5 words or less. What do you say?",
  "Describe how you'd start a conversation with someone you find attractive here.",
  "Imagine a steamy elevator scene with your favorite celebrity. What's happening?",
  "You're dared to send a playful DM to someone on this server. Who do you pick, and what do you say?",
  "You're in a romantic dinner setting over Discord video. Describe your ideal virtual date.",
  "Someone on this server sends you a virtual kiss emoji. How do you respond?",
  "You find yourself in a Discord room with only your crush. What's your first message to break the ice?",
  "You’ve got 10 seconds to choose someone to flirt with. Who do you pick?",
  "You're given the power to read someone's DMs for a minute. Who's would you read and why?",
  "Imagine you’re on a virtual date. What's your go-to question to break the ice?",
  "Describe your perfect virtual hangout with someone on this server.",
  "You’ve been dared to confess a spicy secret to your last DM contact. What do you say?",
  "Someone challenges you to write a flirty haiku for your crush. Give it a try!",
  "You have to convince your crush to go on a virtual movie night with you. How do you ask?",
  "You're given a choice to send one anonymous message to someone on the server. What's the message?",
  "Imagine you’re hosting a virtual game night for you and a crush. Describe the vibe.",
  "You can react with any emoji to someone's message here. What would it be and why?",
  "Imagine you’re playing 20 questions with your crush. What's your first question?",
  "You’re dared to describe someone in this server without mentioning their name. Go!"
]

# Function to get a random prompt based on category
def get_prompt(category):
    if category == "truth":
        return random.choice(truths)
    elif category == "dare":
        return random.choice(dares)
    elif category == "situation":
        return random.choice(situations)
    else:  # Random selection from all
        all_prompts = truths + dares + situations
        return random.choice(all_prompts)

# Button interaction view for Truth/Dare/Situation/Random
class TruthDareView(discord.ui.View):
    def __init__(self, user):
        super().__init__()
        self.user = user

    @discord.ui.button(label="Truth", style=discord.ButtonStyle.green)
    async def truth_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.send_prompt(interaction, "truth")

    @discord.ui.button(label="Dare", style=discord.ButtonStyle.red)
    async def dare_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.send_prompt(interaction, "dare")

    @discord.ui.button(label="Situation", style=discord.ButtonStyle.blurple)
    async def situation_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.send_prompt(interaction, "situation")

    @discord.ui.button(label="Random", style=discord.ButtonStyle.gray)
    async def random_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.send_prompt(interaction, "random")

    async def send_prompt(self, interaction, category):
        prompt = get_prompt(category)
        await interaction.response.send_message(f"{self.user.display_name.capitalize()} asked for a **{category.capitalize()}**: \n {prompt}", view=TruthDareView(interaction.user))


# Truth command to start the game
@commands.command(name="tnd", aliases=["truthdare", "truthdaregame"])
async def truth_dare_game(ctx, user: discord.Member = None):
    """Starts a Truth, Dare, or Situation game with interactive buttons."""
    if not user:
        user = ctx.author  # If no user is mentioned, use the message author
    
    await ctx.send(
        f"{ctx.author.mention} has started a game with {user.mention}! Choose an option below:",
        view=TruthDareView(user)
    )
