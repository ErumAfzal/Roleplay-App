import base64
import datetime as dt
import json
import uuid

import requests
import streamlit as st
from openai import OpenAI


# ---------- CONFIG / CLIENTS ----------

st.set_page_config(page_title="Teacher Role-Play Lab", layout="wide")

# OpenAI client from Streamlit secrets
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
client = OpenAI(api_key=OPENAI_API_KEY)

# GitHub config from secrets
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
GITHUB_REPO = st.secrets["GITHUB_REPO"]       # e.g. "youruser/your-repo"
GITHUB_BRANCH = st.secrets.get("GITHUB_BRANCH", "main")


# ---------- LOAD ROLEPLAYS ----------

@st.cache_data
def load_roleplays():
    with open("data/roleplays.json", encoding="utf-8") as f:
        return json.load(f)

ROLEPLAYS = load_roleplays()


# ---------- SURVEY QUESTIONS ----------

SURVEY_QUESTIONS = [
    # Personality
    ("Q1", "The chatbot’s personality was realistic and engaging.", "Personality"),
    ("Q2", "The chatbot seemed too robotic.", "Personality"),
    ("Q3", "The chatbot was welcoming during initial setup.", "Personality"),
    ("Q4", "The chatbot seemed very unfriendly.", "Personality"),
    ("Q9", "The chatbot understood me well.", "Personality"),
    # UX
    ("Q7", "The chatbot was easy to navigate.", "User Experience"),
    ("Q8", "It would be easy to get confused when using the chatbot.", "User Experience"),
    ("Q15", "The chatbot was easy to use.", "User Experience"),
    ("Q16", "The chatbot was very complex.", "User Experience"),
    # Error handling
    ("Q13", "The chatbot coped well with any errors or mistakes.", "Error Handling"),
    ("Q14", "The chatbot seemed unable to cope with any errors.", "Error Handling"),
    # Onboarding
    ("Q5", "The chatbot explained its scope and purpose well.", "Onboarding"),
    ("Q6", "The chatbot gave no indication as to its purpose.", "Onboarding"),
]


# ---------- GITHUB SAVE HELPERS ----------

def save_text_to_github(relative_path: str, text: str):
    """Create a new file in the GitHub repo via the Contents API."""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{relative_path}"

    encoded = base64.b64encode(text.encode("utf-8")).decode("utf-8")
    payload = {
        "message": f"Add {relative_path}",
        "content": encoded,
        "branch": GITHUB_BRANCH,
    }
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
    }

    r = requests.put(url, json=payload, headers=headers)
    if r.status_code not in (200, 201):
        raise RuntimeError(f"GitHub save failed ({r.status_code}): {r.text}")
    return r.json()


# ---------- ANALYSIS LOGIC ----------

FRAMEWORK_DESCRIPTION = """
You are an expert in communication psychology analysing a role-play conversation
between a student (teacher in training) and an AI actor.

There are two types of communication in the framework:

1) Understanding-oriented communication
   - Conversation intention mainly: CONTENT GOAL
   - Adherence to Grice's maxims of quantity, quality, relevance, and clarity
   - Relational goal: AUTHENTIC self-disclosure (talking honestly about here-and-now)

2) Strategic communication
   - Conversation intention mainly: RELATIONAL GOAL (influence, image, future benefits)
   - Breaching or manipulating the maxims of quantity, quality, relevance, clarity
   - Relational goal: FUTURE-ORIENTED self-disclosure (talking about self in a calculated,
     strategically useful way)

For each conversation, classify:

- dominant_communication_type: "understanding_oriented" or "strategic"
- conversation_intention: "content_goal" or "relational_goal"
- maxims:
    - quantity: "adheres" or "breaches"
    - quality: "adheres" or "breaches"
    - relevance: "adheres" or "breaches"
    - clarity: "adheres" or "breaches"
- self_disclosure: "authentic" or "future_oriented"

Also provide a short explanation (2–3 sentences) per category.

The conversation may be in German or English.
Always answer in English but preserve short quotes in the original language if useful.
Return ONLY valid JSON.
"""


def analyse_conversation(role_id: str, transcript_plain: str) -> dict:
    """Call the model once more to classify the communication."""
    meta = ROLEPLAYS[role_id]
    role_title = meta["title"]

    analysis_prompt = f"""
Role-play title: {role_title}
Social role (student perspective): {meta['social_role']}
Expected communication type (from training design): {meta.get('expected_communication_type', 'unknown')}

Conversation transcript (speaker labels already added):

{transcript_plain}

Now apply the framework description you received earlier.
Respond ONLY with a compact JSON object with the following keys:
- role_title
- detected_language
- dominant_communication_type
- conversation_intention
- maxims: object with keys quantity, quality, relevance, clarity and their explanation
- self_disclosure_type
- self_disclosure_explanation
- social_role
- overall_comment (1 short paragraph)
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": FRAMEWORK_DESCRIPTION},
            {"role": "user", "content": analysis_prompt},
        ],
        temperature=0.2,
    )

    raw = response.choices[0].message.content
    try:
        return json.loads(raw)
    except Exception:
        # fall back: wrap text
        return {"raw_analysis_text": raw}


# ---------- UI HELPERS ----------

def init_session_state(role_id: str):
    meta = ROLEPLAYS[role_id]
    system_prompt = meta["actor_system_prompt"]

    st.session_state.role_id = role_id
    st.session_state.student_label = meta["student_label"]
    st.session_state.agent_label = meta["agent_label"]
    st.session_state.messages = [
        {"role": "system", "content": system_prompt}
    ]  # full history sent to OpenAI
    st.session_state.turns = []  # for display + saving


def render_chat():
    """Render existing conversation turns."""
    if "turns" not in st.session_state:
        return

    for t in st.session_state.turns:
        speaker = t["speaker"]
        content = t["content"]
        if speaker == "student":
            label = st.session_state.student_label
            st.markdown(f"**{label}:** {content}")
        else:
            label = st.session_state.agent_label
            st.markdown(f"**{label}:** {content}")


def build_plain_transcript() -> str:
    """Build a text transcript with speaker labels for saving & analysis."""
    lines = []
    for t in st.session_state.turns:
        if t["speaker"] == "student":
            label = st.session_state.student_label
        else:
            label = st.session_state.agent_label
        lines.append(f"{label}: {t['content']}")
    return "\n".join(lines)


# ---------- MAIN APP LAYOUT ----------

st.title("🎭 Teacher Role-Play Lab")

st.sidebar.header("Session & Participant")

session_choice = st.sidebar.selectbox(
    "Choose session",
    options=["Session 1 (Role plays 1–5)", "Session 2 (Role plays 6–10)"],
)

session_number = 1 if session_choice.startswith("Session 1") else 2

# Filter roleplays by session
choices = {
    rid: meta["title"]
    for rid, meta in ROLEPLAYS.items()
    if meta["session"] == session_number
}

role_id = st.sidebar.selectbox(
    "Choose role-play",
    options=list(choices.keys()),
    format_func=lambda rid: f"{rid}: {choices[rid]}",
)

participant_id = st.sidebar.text_input(
    "Participant code (anonymised, e.g. S01, S02…)", value=""
)

if "role_id" not in st.session_state or st.session_state.role_id != role_id:
    init_session_state(role_id)

meta = ROLEPLAYS[role_id]

st.markdown(f"## Role-play {role_id}: {meta['title']}")

col_instr, col_chat = st.columns([1.1, 1.9])

with col_instr:
    st.markdown("### 📘 Instructions for you (student)")
    st.markdown(meta["student_instructions"])

    st.info(
        "When you are ready, start the conversation in the chat area on the right. "
        "You can end at any time by writing **\"Danke, tschüss\"** or **\"Thank you, goodbye\"**."
    )

with col_chat:
    st.markdown("### 💬 Conversation")

    render_chat()

    user_input = st.text_input(
        f"Your message as **{meta['student_label']}**",
        key="user_input",
    )

    send_col, end_col = st.columns([1, 1])

    with send_col:
        if st.button("Send message", type="primary"):
            if not user_input.strip():
                st.warning("Please type something before sending.")
            else:
                # append user message
                st.session_state.messages.append(
                    {"role": "user", "content": user_input}
                )
                st.session_state.turns.append(
                    {"speaker": "student", "content": user_input}
                )

                # call OpenAI with NEW SDK syntax
                try:
                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=st.session_state.messages,
                        temperature=0.7,
                        max_tokens=512,
                    )
                    assistant_reply = response.choices[0].message.content.strip()
                except Exception as e:
                    assistant_reply = f"[ERROR calling model: {e}]"

                st.session_state.messages.append(
                    {"role": "assistant", "content": assistant_reply}
                )
                st.session_state.turns.append(
                    {"speaker": "agent", "content": assistant_reply}
                )

                # clear input
                st.session_state.user_input = ""
                st.experimental_rerun()

    with end_col:
        st.session_state.end_clicked = st.button("End conversation & go to survey")

st.markdown("---")

# ---------- SURVEY SECTION ----------

st.markdown("## 📝 Survey (5-point Likert scale)")

st.write(
    "1 = strongly disagree, 5 = strongly agree. "
    "Please answer based on your experience with this role-play chatbot."
)

survey_answers = {}
for qid, text, group in SURVEY_QUESTIONS:
    survey_answers[qid] = st.slider(
        f"{qid} ({group}) – {text}",
        min_value=1,
        max_value=5,
        value=3,
    )

additional_comments = st.text_area("Any additional comments (optional):", "")

submit = st.button("Save chat + survey to GitHub", type="primary")

if submit or st.session_state.get("end_clicked"):
    if not participant_id.strip():
        st.error("Please enter a participant code in the sidebar before saving.")
    else:
        # Build transcript and analysis
        transcript_plain = build_plain_transcript()
        timestamp = dt.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        uid = uuid.uuid4().hex[:8]

        with st.spinner("Analysing conversation and saving to GitHub…"):
            analysis = analyse_conversation(role_id, transcript_plain)

            # Conversation JSON
            conv_payload = {
                "participant_id": participant_id.strip(),
                "timestamp_utc": timestamp,
                "role_id": role_id,
                "role_title": meta["title"],
                "session": meta["session"],
                "social_role": meta["social_role"],
                "student_label": meta["student_label"],
                "agent_label": meta["agent_label"],
                "messages": st.session_state.turns,
                "transcript": transcript_plain,
                "analysis": analysis,
            }

            conv_path = f"data/transcripts/{timestamp}_{participant_id}_role{role_id}_{uid}.json"
            save_text_to_github(conv_path, json.dumps(conv_payload, ensure_ascii=False, indent=2))

            # Survey JSON
            survey_payload = {
                "participant_id": participant_id.strip(),
                "timestamp_utc": timestamp,
                "role_id": role_id,
                "role_title": meta["title"],
                "session": meta["session"],
                "answers": survey_answers,
                "comments": additional_comments,
            }

            survey_path = f"data/surveys/{timestamp}_{participant_id}_role{role_id}_{uid}.json"
            save_text_to_github(survey_path, json.dumps(survey_payload, ensure_ascii=False, indent=2))

        st.success("Conversation and survey has been saved")
        st.balloons()
