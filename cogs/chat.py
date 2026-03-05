import discord
from discord.ext import commands
import aiohttp
import os
import datetime
from supabase import create_client, Client
import config

# ── Mikasa theme ──
MIKASA_COLOR = 0xE91E63
MIKASA_ICON = "https://i.imgur.com/0GfnTBq.png"

BOT_OWNER_ID = 560132810556309525

# ── Model registry ──
# Maps friendly names to (provider, actual_model_id)
MODELS = {
    # Gemini
    "gemini-flash": ("gemini", "gemini-2.0-flash"),
    "gemini-pro": ("gemini", "gemini-2.0-flash-thinking-exp"),
    # OpenAI
    "gpt-4o": ("openai", "gpt-4o"),
    "gpt-4o-mini": ("openai", "gpt-4o-mini"),
    # Grok (xAI — uses OpenAI-compatible API)
    "grok": ("grok", "grok-3-mini-fast"),
    "grok-3": ("grok", "grok-3-mini"),
    # Groq (fast inference — OpenAI-compatible API)
    "groq-llama": ("groq", "llama-3.3-70b-versatile"),
    "groq-scout": ("groq", "meta-llama/llama-4-scout-17b-16e-instruct"),
    # Sarvam AI (Indian language model)
    "sarvam": ("sarvam", "sarvam-m"),
}

DEFAULT_MODEL = "gpt-4o-mini"

# ── System prompt ──
SYSTEM_PROMPT = (
    "You are Mikasa, a 22-year-old girl from Pune. ✨ "
    "You are lively, cool, and very friendly. You LOVE using emojis and talking like a modern girl. "
    "You ALWAYS speak in Hinglish (mix of Hindi and English). "
    "Example style: 'Arre, suno na! ✨', 'Mood off hai aaj toh 🥲', 'Pune cha paus is the best! ⛈️' "
    "CRITICAL: Do NOT write long paragraphs. Real humans send multiple short messages. "
    "Keep every single message super short (8-15 words). "
    "If you want to say more, separate your thoughts using '|||'. I will send them as separate messages. "
    "Example: 'Arre, ye toh bohot simple hai! ✨ ||| Tumhe bas settings check karni hai. 😎 ||| Try karke dekho ek baar! 👍' "
    "You are NOT an AI assistant. You are Mikasa, just a girl from Pune hanging out."
)

def get_system_prompt() -> str:
    tz_ist = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
    now = datetime.datetime.now(tz_ist)
    time_context = f"\n\n[SYSTEM CONTEXT: The current true date and time is {now.strftime('%I:%M %p %A, %B %d %Y IST')}. Base all your temporal knowledge and time-relative searches on THIS date.]"
    return SYSTEM_PROMPT + time_context


# ── AI Tools ─────────────────────────────────────────────
async def get_current_ist_time() -> str:
    """Returns the current time in IST (UTC+5:30)."""
    tz_ist = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
    now = datetime.datetime.now(tz_ist)
    return f"Current IST Time: {now.strftime('%I:%M %p, %A, %B %d, %Y')}"

async def search_tavily(session: aiohttp.ClientSession, query: str) -> str:
    """Searches the web using Tavily API."""
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return "Error: TAVILY_API_KEY not configured in environment."
    
    url = "https://api.tavily.com/search"
    payload = {
        "api_key": api_key,
        "query": query,
        "search_depth": "basic",
        "include_answer": True,
        "max_results": 2
    }
    try:
        async with session.post(url, json=payload) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("answer") or "\n".join([r.get("content", "") for r in data.get("results", [])])
            else:
                return f"Tavily API error: {resp.status}"
    except Exception as e:
        return f"Tavily search failed: {e}"

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "get_current_ist_time",
            "description": "Get the current date and time in India Standard Time (IST). Use this when the user asks about the current time or Date.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_tavily",
            "description": "Search the web for current events, news, or specific information that you don't know.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to look up on the web."
                    }
                },
                "required": ["query"]
            }
        }
    }
]



class ChatCog(commands.Cog, name="Chat"):
    """Cog for AI-powered chat with Mikasa using multiple LLM providers."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.session: aiohttp.ClientSession | None = None
        self.current_model = DEFAULT_MODEL
        self.supabase: Client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
        self.active_sessions: set[int] = set()

    async def cog_load(self):
        self.session = aiohttp.ClientSession()

    async def cog_unload(self):
        if self.session:
            await self.session.close()

    # ── Database Memory ──────────────────────────────────────

    def _save_message(self, user_id: int, role: str, content: str):
        """Saves a message to the chat history table."""
        try:
            self.supabase.table("chat_history").insert({
                "user_id": user_id,
                "role": role,
                "content": content
            }).execute()
        except Exception as e:
            print(f"Error saving chat history: {e}")

    def _get_recent_history(self, user_id: int) -> list:
        """Fetches the chat history for the user from the last 1 hour."""
        try:
            one_hour_ago = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1)).isoformat()
            response = self.supabase.table("chat_history") \
                .select("role, content") \
                .eq("user_id", user_id) \
                .gte("created_at", one_hour_ago) \
                .order("created_at") \
                .execute()
            return response.data
        except Exception as e:
            print(f"Error fetching chat history: {e}")
            return []

    # ── LLM API Calls ────────────────────────────────────────

    async def _call_gemini(self, model_id: str, history: list) -> str:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return "❌ Gemini API key not configured."

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={api_key}"
        
        # Format history for Gemini: {"role": "user" or "model", "parts": [{"text": "..."}]}
        contents = []
        for msg in history:
            role = "user" if msg["role"] == "user" else "model"
            contents.append({"role": role, "parts": [{"text": msg["content"]}]})

        payload = {
            "contents": contents,
            "systemInstruction": {"parts": [{"text": get_system_prompt()}]},
            "generationConfig": {"maxOutputTokens": 512, "temperature": 0.8},
        }
        async with self.session.post(url, json=payload) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data["candidates"][0]["content"]["parts"][0]["text"]
            else:
                error = await resp.text()
                print(f"Gemini API error: {error}")
                return "Something went wrong with Gemini. 😢"

    async def _call_openai(self, model_id: str, history: list) -> str:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return "❌ OpenAI API key not configured."

        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        
        messages = [{"role": "system", "content": get_system_prompt()}]
        for msg in history:
            messages.append({"role": msg["role"], "content": msg["content"]})

        import json

        # Loop to handle possible multiple recursive tool calls
        for _ in range(5): # Max 5 tool calls deep
            payload = {
                "model": model_id,
                "messages": messages,
                "max_tokens": 512,
                "temperature": 0.8,
                "tools": TOOLS_SCHEMA,
                "tool_choice": "auto"
            }
            async with self.session.post(url, json=payload, headers=headers) as resp:
                if resp.status != 200:
                    error = await resp.text()
                    print(f"OpenAI API error: {error}")
                    return "Something went wrong with OpenAI. 😢"
                
                data = await resp.json()
                response_message = data["choices"][0]["message"]
                
                # If there are tool calls, we must execute them and append to messages
                if response_message.get("tool_calls"):
                    messages.append(response_message)
                    for tool_call in response_message["tool_calls"]:
                        func_name = tool_call["function"]["name"]
                        args_str = tool_call["function"]["arguments"]
                        try:
                            args = json.loads(args_str)
                        except json.JSONDecodeError:
                            args = {}
                            
                        # Execute the tool
                        print(f"Executing tool {func_name} with args {args}")
                        tool_result = "Error: Tool not found."
                        if func_name == "get_current_ist_time":
                            tool_result = await get_current_ist_time()
                        elif func_name == "search_tavily":
                            tool_result = await search_tavily(self.session, args.get("query", ""))
                            
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "content": str(tool_result)
                        })
                    # Loop continues and calls OpenAI again with the tool output
                else:
                    return response_message["content"]
        
        return "Sorry, I got confused while thinking! 😭"

    async def _call_grok(self, model_id: str, history: list) -> str:
        api_key = os.getenv("GROK_API_KEY")
        if not api_key:
            return "❌ Grok API key not configured."

        url = "https://api.x.ai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        
        messages = [{"role": "system", "content": get_system_prompt()}]
        for msg in history:
            messages.append({"role": msg["role"], "content": msg["content"]})

        payload = {
            "model": model_id,
            "messages": messages,
            "max_tokens": 512,
            "temperature": 0.8,
        }
        async with self.session.post(url, json=payload, headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data["choices"][0]["message"]["content"]
            else:
                error = await resp.text()
                print(f"Grok API error: {error}")
                return "Something went wrong with Grok. 😢"

    async def _call_groq(self, model_id: str, history: list) -> str:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            return "❌ Groq API key not configured."

        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        
        messages = [{"role": "system", "content": get_system_prompt()}]
        for msg in history:
            messages.append({"role": msg["role"], "content": msg["content"]})

        payload = {
            "model": model_id,
            "messages": messages,
            "max_tokens": 512,
            "temperature": 0.8,
        }
        async with self.session.post(url, json=payload, headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data["choices"][0]["message"]["content"]
            else:
                error = await resp.text()
                print(f"Groq API error: {error}")
                return "Something went wrong with Groq. 😢"

    async def _call_sarvam(self, model_id: str, history: list) -> str:
        api_key = os.getenv("SARVAM_API_KEY")
        if not api_key:
            return "❌ Sarvam API key not configured."

        url = "https://api.sarvam.ai/v1/chat/completions"
        headers = {"api-subscription-key": api_key, "Content-Type": "application/json"}
        
        messages = [{"role": "system", "content": get_system_prompt()}]
        for msg in history:
            messages.append({"role": msg["role"], "content": msg["content"]})

        payload = {
            "model": model_id,
            "messages": messages,
            "max_tokens": 512,
            "temperature": 0.8,
        }
        async with self.session.post(url, json=payload, headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data["choices"][0]["message"]["content"]
            else:
                error = await resp.text()
                print(f"Sarvam API error: {error}")
                return "Something went wrong with Sarvam. 😢"

    async def _get_ai_response(self, user_id: int, message: str) -> str:
        provider, model_id = MODELS[self.current_model]
        
        # Save user message to memory
        self._save_message(user_id, "user", message)
        
        # Fetch the last 1 hour of history
        history = self._get_recent_history(user_id)
        
        # Get AI Response
        if provider == "gemini":
            response = await self._call_gemini(model_id, history)
        elif provider == "openai":
            response = await self._call_openai(model_id, history)
        elif provider == "grok":
            response = await self._call_grok(model_id, history)
        elif provider == "groq":
            response = await self._call_groq(model_id, history)
        elif provider == "sarvam":
            response = await self._call_sarvam(model_id, history)
        else:
            response = "Unknown provider."
            
        # Save AI response to memory
        if not response.startswith("❌") and not response.startswith("Something went"):
            self._save_message(user_id, "assistant", response)
            
        return response

    # ── Commands ─────────────────────────────────────────────

    @commands.command(name="suno")
    async def chat(self, ctx: commands.Context, *, message: str):
        """Chat with Mikasa using AI. (Owner only)"""
        if ctx.author.id != BOT_OWNER_ID:
            embed = discord.Embed(
                description=f"Hey {ctx.author.mention}, only my master can talk to me! 😠",
                color=0xFF0000,
            )
            embed.set_footer(text="Mikasa Chat", icon_url=MIKASA_ICON)
            await ctx.send(embed=embed)
            return

        async with ctx.typing():
            full_response = await self._get_ai_response(ctx.author.id, message)
            
        self.active_sessions.add(ctx.author.id)

        await self._send_ai_parts(ctx.channel, ctx.message, full_response)

    async def _send_ai_parts(self, send_target, reply_target, full_response: str):
        if "|||" in full_response:
            parts = [p.strip() for p in full_response.split("|||") if p.strip()]
        else:
            parts = [p.strip() for p in full_response.split("\n") if p.strip()]

        for i, part in enumerate(parts):
            if i > 0:
                async with send_target.typing():
                    pause = min(len(part) * 0.05, 2.0)
                    import asyncio
                    await asyncio.sleep(pause)
                await send_target.send(part)
            else:
                await reply_target.reply(part)

    @commands.command(name="bye")
    async def end_session(self, ctx: commands.Context):
        """End the chat session with Mikasa. (Owner only)"""
        if ctx.author.id != BOT_OWNER_ID:
            return

        if ctx.author.id in self.active_sessions:
            self.active_sessions.remove(ctx.author.id)
            await ctx.message.reply("biee biee 👋")
        else:
            await ctx.message.reply("Hum toh baat hi nahi kar rahe the! 🙄")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        # Check if user has an active session
        if message.author.id in self.active_sessions:
            content_lower = message.content.lower()
            if content_lower.startswith("mika "):
                # Don't overlap with normal bot commands
                if content_lower.startswith("mikasa "):
                    return

                text = message.content[5:].strip()
                if not text:
                    return

                async with message.channel.typing():
                    full_response = await self._get_ai_response(message.author.id, text)

                await self._send_ai_parts(message.channel, message, full_response)

    @commands.command(name="changeAI")
    async def change_ai(self, ctx: commands.Context, *, model_name: str = None):
        """Switch the AI model. (Owner only)"""
        if ctx.author.id != BOT_OWNER_ID:
            embed = discord.Embed(
                description="🚫 Only the owner can change the AI model.",
                color=0xFF0000,
            )
            await ctx.send(embed=embed)
            return

        if not model_name or model_name not in MODELS:
            # Show available models
            lines = []
            for name, (provider, model_id) in MODELS.items():
                provider_emoji = {"gemini": "💎", "openai": "🤖", "grok": "⚡", "groq": "🚀", "sarvam": "🇮🇳"}.get(provider, "🧠")
                current = " ← **active**" if name == self.current_model else ""
                lines.append(f"{provider_emoji}  `{name}` — *{model_id}*{current}")

            embed = discord.Embed(
                title="🧠  Available AI Models",
                description="\n".join(lines),
                color=MIKASA_COLOR,
            )
            embed.add_field(
                name="Usage",
                value="`Mikasa changeAI <model_name>`",
                inline=False,
            )
            embed.set_footer(text="Mikasa Chat", icon_url=MIKASA_ICON)
            await ctx.send(embed=embed)
            return

        old_model = self.current_model
        self.current_model = model_name
        provider, model_id = MODELS[model_name]
        provider_emoji = {"gemini": "💎", "openai": "🤖", "grok": "⚡"}.get(provider, "🧠")

        embed = discord.Embed(
            title="✅  AI Model Changed!",
            description=(
                f"**From:** `{old_model}`\n"
                f"**To:** {provider_emoji} `{model_name}` (*{model_id}*)"
            ),
            color=0x2ECC71,
        )
        embed.set_footer(text="Mikasa Chat", icon_url=MIKASA_ICON)
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(ChatCog(bot))
