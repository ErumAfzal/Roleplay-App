import streamlit as st
import json
from datetime import datetime
from openai import OpenAI

# Optional: Google Sheets logging
try:
    import gspread
    from google.oauth2.service_account import Credentials
    GSHEETS_AVAILABLE = True
except ImportError:
    GSHEETS_AVAILABLE = False


# ---------------------------------------------------------
#  OpenAI setup (2025 API)
# ---------------------------------------------------------

def setup_openai_client():
    api_key = st.secrets.get("OPENAI_API_KEY", "")
    if not api_key:
        api_key = st.sidebar.text_input(
            "🔑 OpenAI API key (local testing)",
            type="password",
            help="On Streamlit Cloud, configure OPENAI_API_KEY in Secrets."
        )

    if not api_key:
        st.sidebar.error("Please provide an OpenAI API key.")
        return None

    try:
        client = OpenAI(api_key=api_key)
        return client
    except Exception as e:
        st.sidebar.error(f"Could not create OpenAI client: {e}")
        return None


# ---------------------------------------------------------
#  Google Sheets helpers
# ---------------------------------------------------------

def get_gsheets_client():
    if not GSHEETS_AVAILABLE:
        st.sidebar.error("gspread is not installed. Cannot save data.")
        return None

    sa_info = st.secrets.get("gcp_service_account")
    sheet_id = st.secrets.get("GSPREAD_SHEET_ID")

    if not sa_info:
        st.sidebar.error("Missing gcp_service_account in secrets.toml")
        return None
    if not sheet_id:
        st.sidebar.error("Missing GSPREAD_SHEET_ID in secrets.toml")
        return None

    try:
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = Credentials.from_service_account_info(sa_info, scopes=scopes)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"Could not create Google Sheets client: {e}")
        return None


def append_chat_and_feedback_to_sheets(meta, chat_messages, feedback):
    client = get_gsheets_client()
    if not client:
        return

    sheet_id = st.secrets["GSPREAD_SHEET_ID"]

    try:
        sh = client.open_by_key(sheet_id)
    except Exception as e:
        st.error(f"Could not open Google Sheet:\n\n{e}")
        return

    timestamp = datetime.utcnow().isoformat()
    chat_json = json.dumps(chat_messages, ensure_ascii=False)

    # Ensure CHATS sheet
    try:
        chats_ws = sh.worksheet("chats")
    except Exception:
        chats_ws = sh.add_worksheet("chats", rows=1000, cols=20)

    # Ensure FEEDBACK sheet
    try:
        fb_ws = sh.worksheet("feedback")
    except Exception:
        fb_ws = sh.add_worksheet("feedback", rows=1000, cols=20)

    chat_row = [
        timestamp,
        meta.get("student_id", ""),
        meta.get("language", ""),
        meta.get("batch_step", ""),
        meta.get("roleplay_id", ""),
        meta.get("roleplay_title_en", ""),
        meta.get("roleplay_title_de", ""),
        meta.get("communication_type", ""),
        chat_json,
    ]

    fb_row = [
        timestamp,
        meta.get("student_id", ""),
        meta.get("language", ""),
        meta.get("batch_step", ""),
        meta.get("roleplay_id", ""),
        feedback.get("Q1"),
        feedback.get("Q2"),
        feedback.get("Q3"),
        feedback.get("Q4"),
        feedback.get("Q5"),
        feedback.get("Q6"),
        feedback.get("Q7"),
        feedback.get("Q8"),
        feedback.get("Q9"),
        feedback.get("Q10"),
        feedback.get("Q11"),
        feedback.get("Q12"),
        feedback.get("comment"),
    ]

    chats_ws.append_row(chat_row)
    fb_ws.append_row(fb_row)

    st.success(" Chat + Feedback saved successfully!")
