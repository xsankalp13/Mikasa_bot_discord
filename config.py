"""
Startup configuration validator.
Loads and validates all required environment variables before the bot starts.
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

REQUIRED_KEYS = [
    "DISCORD_TOKEN",
    "SUPABASE_URL",
    "SUPABASE_KEY",
]


def _validate():
    missing = [k for k in REQUIRED_KEYS if not os.getenv(k)]
    if missing:
        print("❌  Missing required environment variables:")
        for k in missing:
            print(f"   • {k}")
        print("\nPlease set them in your .env file and try again.")
        sys.exit(1)


_validate()

# Export validated values as constants
DISCORD_TOKEN: str = os.environ["DISCORD_TOKEN"]
SUPABASE_URL: str = os.environ["SUPABASE_URL"]
SUPABASE_KEY: str = os.environ["SUPABASE_KEY"]
