from supabase import create_client, Client
import os
import warnings

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client | None = None

if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        warnings.warn(f"Failed to initialize Supabase client: {e!r}")
else:
    warnings.warn("SUPABASE_URL or SUPABASE_KEY not set; Supabase client disabled.")
