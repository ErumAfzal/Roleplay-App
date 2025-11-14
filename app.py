import base64
import datetime as dt
import json
import uuid

import requests
import streamlit as st
from openai import OpenAI


# ---------- STREAMLIT & CLIENT CONFIG ----------

st.set_page_config(page_title="Teacher Role-Play Lab", layout="wide")

OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
client = OpenAI(api_key=OPENAI_API_KEY)

GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
GITHUB_REPO = st.secrets["GITHUB_REPO"]        # e.g. "youruser/your-repo"
GITHUB_BRANCH = st.secrets.get("GITHUB_BRANCH", "main")


# ---------- LOAD ROLEPLAYS FROM JSON ----------

@st.cache_data
def load_roleplays():
    with open("data/roleplays.json", encoding="utf-8") as f:
        return json.load(f)

ROLEPLAYS = load_roleplays()


# ---------- SURVEY QUESTIONS (5-point Likert) ----------

SURVEY_QUESTIONS = [
    # Personality
    ("Q1", "The chatbot’s personality was realistic and engaging.", "Personality"),
    ("Q2", "The chatbot seemed too robotic.", "Personality"),
    ("Q3", "The chatbot was welcoming during initial setup.", "Personality"),
    ("Q4", "The chatbot seemed very unfriendly.", "Personality"),
    ("Q9", "The chatbot understood me well.", "Personality"),
    # User Experience
    ("Q7", "The chatbot was easy to navigate.", "User Experience"),
    ("Q8", "It would be easy to get confused when using the chatbot.", "User Experience"),
    ("Q15", "The chatbot was easy to use.", "User Experience"),
    ("Q16", "The chatbot was very complex.", "User Experience"),
    # Error Handling
    ("Q13", "The chatbot coped well with any errors or mistakes.", "Error Handling"),
    ("Q14", "The chatbot seemed unable to cope with any errors.", "Error Handling"),
    # Onboarding
    ("Q5", "The chatbot explained its scope and purpose well.", "Onboarding"),
    ("Q6", "The chatbot gave no indication as to its purpose.", "Onboarding"),
]


# ---------- GITHUB SAVE HELPERS ----------

def save_text_to_github(relative_path: str, text: str):
    """
    Create a new file in GitHub via Contents API.
    You decided: A) same repo, A) one file per transcript, A) one file per survey.
    """
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


# ---------- COMMUNICATION ANALYSIS FRAMEWORK ----------

FRAMEWORK_DESCRIPTION = """
You are an expert in communication psychology analysing a role-play conversation
between a student (teacher in training) and an AI actor.

Framework:

- Understanding-oriented communication:
  * Conversation intention mainly: CONTENT GOAL
  * Adherence to quantity, quality, relevance, clarity
  * Relational goal: AUTHENTIC self-disclosure (honest, here-and-now)

- Strategic communication:
  * Conversation intention mainly: RELATIONAL GOAL (influence, image, strategic future benefit)
  * Breaching or manipulating quantity, quality, relevance, clarity
  * Relational goal: FUTURE-ORIENTED self-disclosure (calculated, strategic self-presentation)

For each conversation, classify:

- dominant_communication_type: "understanding_oriented" or "strategic"
- conversation_intention: "content_goal" or "relational_goal"
- maxims:
    - quantity: { "status": "adheres"/"breaches", "explanation": "..." }
    - quality:  { ... }
    - relevance:{ ... }
    - clarity:  { ... }
- self_disclosure_type: "authentic" or "future_oriented"
- self_disclosure_explanation: 2–3 sentences
- social_role: copy the provided social role label
- overall_comment: one short paragraph

Conversation may be in German or English.
Answer in English but you can quote short German segments.
Return ONLY a valid JSON object.
"""


def analyse_conversation(role_id: str, transcript_plain: str) -> dict:
    meta = ROLEPLAYS[role_id]
    role_title = meta["title"]

    analysis_prompt = f"""
Role-play title: {role_title}
Social role (student perspective): {meta['social_role']}
Expected communication type (from training design): {meta.get('expected_communication_type', 'unknown')}

Conversation transcript with speaker labels:

{transcript_plain}

Apply the communication framework you know and respond ONLY with a JSON object,
no commentary.
"""

    response = client.responses.create(
        model="gpt-4o-mini",
        input=[
            {"role": "system", "content": FRAMEWORK_DESCRIPTION},
            {"role": "user", "content": analysis_prompt},
        ],
        temperature=0.2,
    )

    raw = response.output_text
    try:
        return json.loads(raw)
    except Exception:
        return {"raw_analysis_text": raw}


# ---------- SESSION HELPERS ----------

def init_session_state(role_id: str):
    meta = ROLEPLAYS[role_id]
    system_prompt = meta["actor_system_prompt"]

    st.session_state.role_id = role_id
    st.session_state.student_label = meta["student_label"]
    st.session_state.agent_label = meta["agent_label"]
    # messages sent to the model:
    st.session_state.messages = [
        {"role": "system", "content": system_prompt}
    ]
    # simplified list for displaying & saving:
    st.session_state.turns = []


def render_chat():
    if "turns" not in st.session_state:
        return
    for t in st.session_state.turns:
        if t["speaker"] == "student":
            label = st.session_state.student_label
        else:
            label = st.session_state.agent_label
        st.markdown(f"**{label}:** {t['content']}")


def build_plain_transcript() -> str:
    lines = []
    for t in st.session_state.turns:
        if t["speaker"] == "student":
            label = st.session_state.student_label
        else:
            label = st.session_state.agent_label
        lines.append(f"{label}: {t['content']}")
    return "\n".join(lines)


# ---------- MAIN UI ----------

st.title("🎭 Teacher Role-Play Lab")

st.sidebar.header("Session & Participant")

session_choice = st.sidebar.selectbox(
    "Choose session",
    ["Session 1 (Role plays 1–5)", "Session 2 (Role plays 6–10)"],
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
    "Participant code (anonymised, e.g. S01, S02…)",
    value="",
)

if "role_id" not in st.session_state or st.session_state.role_id != role_id:
    init_session_state(role_id)

meta = ROLEPLAYS[role_id]

st.markdown(f"## Role-play {role_id}: {meta['title']}")

col_left, col_right = st.columns([1.1, 1.9])

with col_left:
    st.markdown("### 📘 Instructions for you (student)")
    st.markdown(meta["student_instructions"])

    st.info(
        "When you are ready, start the conversation on the right. "
        "You can end at any time by writing **\"Danke, tschüss\"** or **\"Thank you, goodbye\"**."
    )

with col_right:
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
                # add student message
                st.session_state.messages.append(
                    {"role": "user", "content": user_input}
                )
                st.session_state.turns.append(
                    {"speaker": "student", "content": user_input}
                )

                # call OpenAI (Responses API)
                try:
                    response = client.responses.create(
                        model="gpt-4o-mini",
                        input=st.session_state.messages,
                        temperature=0.7,
                    )
                    assistant_reply = response.output_text.strip()
                except Exception as e:
                    assistant_reply = f"[ERROR calling model: {e}]"

                st.session_state.messages.append(
                    {"role": "assistant", "content": assistant_reply}
                )
                st.session_state.turns.append(
                    {"speaker": "agent", "content": assistant_reply}
                )

                st.session_state.user_input = ""
                st.experimental_rerun()

    with end_col:
        st.session_state.end_clicked = st.button("End conversation & go to survey")

st.markdown("---")

# ---------- SURVEY ----------

st.markdown("## 📝 Survey (5-point Likert scale)")

st.write(
    "1 = strongly disagree, 5 = strongly agree. "
    "Please answer based on your experience with this chatbot in THIS role-play."
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
        transcript_plain = build_plain_transcript()
        timestamp = dt.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        uid = uuid.uuid4().hex[:8]

        with st.spinner("Analysing conversation and saving to GitHub…"):
            analysis = analyse_conversation(role_id, transcript_plain)

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
            save_text_to_github(
                conv_path,
                json.dumps(conv_payload, ensure_ascii=False, indent=2),
            )

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
            save_text_to_github(
                survey_path,
                json.dumps(survey_payload, ensure_ascii=False, indent=2),
            )

        st.success(" Conversation and survey have been saved")
        st.balloons()
