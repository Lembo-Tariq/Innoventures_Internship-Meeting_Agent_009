# config.py

import os
from dotenv import load_dotenv
import streamlit as st

load_dotenv()

def get_secret(key):
    try:
        return st.secrets[key]
    except Exception:
        return os.getenv(key)

OPENROUTER_API_KEY = get_secret("OPENROUTER_API_KEY")
RESEND_API_KEY = get_secret("RESEND_API_KEY")