import os
from supabase import create_client
from dotenv import load_dotenv

# Load .env so SUPABASE_URL and SUPABASE_KEY are available
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Supabase URL or Key is missing. Check your .env file.")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
