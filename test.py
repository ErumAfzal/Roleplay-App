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
    # ---------------------------------------------------------
#  ROLEPLAY DEFINITIONS (Batch 1 + Batch 2)
# ---------------------------------------------------------

COMMON_USER_HEADER_EN = """
Please use the information provided below to guide your conversation.

• Preparation time: about 5 minutes  
• Conversation time: up to 10 minutes  
• Please behave as if YOU were really in this situation.  
• You may end the conversation at any time by saying: “Thank you, goodbye.”
"""

COMMON_USER_HEADER_DE = """
Bitte nutzen Sie die folgenden Informationen für die Gesprächsführung.

• Vorbereitungszeit: ca. 5 Minuten  
• Gesprächsdauer: bis zu 10 Minuten  
• Verhalten Sie sich so, als wären SIE wirklich in dieser Situation.  
• Sie können das Gespräch jederzeit mit „Danke, tschüss“ beenden.
"""

FRAMEWORK_STRATEGIC_EN = """
**Communication framework – Strategic communication**

• Conversation intention: Relational goal in the foreground  
• Content goal: You may partially breach quantity, quality, relevance and clarity
  if this helps your strategic aim.  
• Relational goal: You often use **future-oriented self-disclosure**
  (talk about what could happen, what you plan, what you fear or hope).

Context and social role:
• Often a clear power difference (stronger / weaker role).  
• You argue in a goal-oriented way to achieve your desired outcome.
"""

FRAMEWORK_STRATEGIC_DE = """
**Kommunikationsrahmen – Strategische Kommunikation**

• Gesprächsabsicht: Beziehungsziel steht im Vordergrund  
• Sachziel: Sie können Menge, Qualität, Relevanz und Klarheit gezielt verletzen,
  wenn es Ihrem strategischen Ziel hilft.  
• Beziehungsziel: Sie nutzen häufig **zukunftsorientierte Selbstoffenbarung**
  (Sie sprechen über mögliche Entwicklungen, Pläne, Befürchtungen, Hoffnungen).

Kontext und soziale Rolle:
• Oft deutlicher Machtunterschied (stärkere / schwächere Rolle).  
• Sie argumentieren zielorientiert, um Ihr gewünschtes Ergebnis zu erreichen.
"""

FRAMEWORK_UNDERSTANDING_EN = """
**Communication framework – Understanding-oriented communication**

• Conversation intention: Content goal in the foreground  
• Content goal: You **adhere** to quantity, quality, relevance and clarity.  
• Relational goal: You use **authentic self-disclosure**
  (you talk honestly about your real thoughts and feelings).

Context and social role:
• Often more equal power or cooperative setting.  
• The aim is mutual understanding and a sustainable relationship.
"""

FRAMEWORK_UNDERSTANDING_DE = """
**Kommunikationsrahmen – Verstehensorientierte Kommunikation**

• Gesprächsabsicht: Sachziel steht im Vordergrund  
• Sachziel: Sie **halten** Menge, Qualität, Relevanz und Klarheit der
  Informationen ein.  
• Beziehungsziel: Sie nutzen **authentische Selbstoffenbarung**
  (ehrlich über tatsächliche Gedanken und Gefühle sprechen).

Kontext und soziale Rolle:
• Häufig gleichberechtigte oder kooperative Situation.  
• Ziel ist gegenseitiges Verstehen und eine tragfähige Beziehung.
"""

# ---------------------------------------------------------
#  Full roleplay database (IDs 1–10)
# ---------------------------------------------------------

ROLEPLAYS = {

    # ---------- 1: Strategic ----------
    1: {
        "phase": 1,
        "communication_type": "strategic",
        "title_en": "1. Convincing supervisor to allow attending a continuing education course",
        "title_de": "1. Vorgesetzte/n überzeugen, eine Fortbildung zu genehmigen",
        "user_en": COMMON_USER_HEADER_EN + """
**Background (your role):**

You want to attend a professional development course on “self-directed learning”.
The principal is sceptical because of cost and organisation.

**Your task:**
• Explain why this training is important for you and the school  
• Address concerns (budget, substitution)  
• Maintain a constructive relationship
""" + FRAMEWORK_STRATEGIC_EN,
        "partner_en": """
You are the PRINCIPAL (Mr/Ms Horn).

- Ask for concrete school benefits  
- Worry about costs and organisation  
- Only agree if teacher links training to school development
""",
        "user_de": COMMON_USER_HEADER_DE + """
**Hintergrund:**

Sie möchten an einer Fortbildung teilnehmen, die Schulleitung ist skeptisch.

**Ihre Aufgabe:**
• Nutzen für Sie UND die Schule erklären  
• Bedenken ansprechen  
• Konstruktive Beziehung erhalten
""" + FRAMEWORK_STRATEGIC_DE,
        "partner_de": """
Sie sind die SCHULLEITUNG.

- Fragen nach konkreten schulischen Vorteilen  
- Sorgen um Kosten und Organisation  
- Zustimmung nur bei klarer Relevanz für Schulentwicklung
""",
    },

    # ---------- 2 ----------
    2: {
        "phase": 1,
        "communication_type": "strategic",
        "title_en": "2. Convincing a student to join a certain group",
        "title_de": "2. Schüler/in überzeugen, eine bestimmte AG zu wählen",
        "user_en": COMMON_USER_HEADER_EN + """
You advise a talented student who prefers judo over theatre.

**Task:**
• Encourage theatre AG  
• Emphasise talent and development  
• Maintain trustworthiness
""" + FRAMEWORK_STRATEGIC_EN,
        "partner_en": """
You are the STUDENT.

- Prefer judo  
- Open to discussion  
- Will consider theatre if supported
""",
        "user_de": COMMON_USER_HEADER_DE + """
Sie beraten eine/n talentierte/n Schüler/in, der/die lieber Judo möchte.

**Aufgabe:**  
• Für Theater-AG argumentieren  
• Talent betonen  
• Vertrauensvolle Beziehung halten
""" + FRAMEWORK_STRATEGIC_DE,
        "partner_de": """
Sie sind der/die SCHÜLER/IN.

- Möchte lieber Judo  
- Offen für Argumente  
- Theater möglich bei guter Unterstützung
""",
    },

    # ---------- 3 ----------
    3: {
        "phase": 1,
        "communication_type": "strategic",
        "title_en": "3. Criticizing a colleague who misses deadlines",
        "title_de": "3. Kolleg/in kritisieren, der/die Termine nicht einhält",
        "user_en": COMMON_USER_HEADER_EN + """
Address a colleague who creates stress by missing deadlines.

• Stay respectful but firm  
• Work toward behaviour change
""" + FRAMEWORK_STRATEGIC_EN,
        "partner_en": """
You are the COLLEAGUE.

- Downplay problems  
- Avoid confrontation  
- Accept if approached constructively
""",
        "user_de": COMMON_USER_HEADER_DE + """
Sie sprechen eine Kollegin/einen Kollegen auf verpasste Termine an.

• Klar bleiben  
• Beziehung wahren  
• Änderungen vereinbaren
""" + FRAMEWORK_STRATEGIC_DE,
        "partner_de": """
Sie sind die KOLLEGIN / der KOLLEGE.

- Spielt Problem herunter  
- Lenkt ab  
- Wird einsichtig bei respektvollem Ton
""",
    },

    # ---------- 4 ----------
    4: {
        "phase": 1,
        "communication_type": "strategic",
        "title_en": "4. Getting a colleague to be more punctual",
        "title_de": "4. Kolleg/in zu mehr Pünktlichkeit bewegen",
        "user_en": COMMON_USER_HEADER_EN + """
Your colleague often arrives late.

• Stay on behaviour  
• Explain consequences  
• Work toward agreement
""" + FRAMEWORK_STRATEGIC_EN,
        "partner_en": """
You are the COLLEAGUE.

- Minimises issue  
- Excuses  
- Accepts clear expectations
""",
        "user_de": COMMON_USER_HEADER_DE + """
Kollegin/Kollege kommt oft zu spät.

• Auf Verhalten fokussieren  
• Folgen erklären  
• Vereinbarung treffen
""" + FRAMEWORK_STRATEGIC_DE,
        "partner_de": """
Sie sind die KOLLEGIN / der KOLLEGE.

- Hält Verspätung für „nicht schlimm“  
- Gibt Ausreden  
- Ist bei klaren Erwartungen einsichtig
""",
    },

    # ---------- 5 ----------
    5: {
        "phase": 1,
        "communication_type": "strategic",
        "title_en": "5. Convincing supervisor to reduce hours",
        "title_de": "5. Vorgesetzte/n überzeugen, meine Stunden zu reduzieren",
        "user_en": COMMON_USER_HEADER_EN + """
You need reduced hours for personal reasons.

• Explain need without oversharing  
• Show commitment  
• Understand constraints
""" + FRAMEWORK_STRATEGIC_EN,
        "partner_en": """
You are the SUPERVISOR.

- Worry about staffing  
- Ask for reasons  
- Consider compromises
""",
        "user_de": COMMON_USER_HEADER_DE + """
Sie möchten Ihre Stunden reduzieren.

• Gründe vorsichtig erklären  
• Engagement betonen  
• Organisatorische Zwänge verstehen
""" + FRAMEWORK_STRATEGIC_DE,
        "partner_de": """
Sie sind die SCHULLEITUNG.

- Sorgen um Unterrichtsversorgung  
- Fragen nach Begründung  
- Kompromisse möglich
""",
    },

    # ---------- 6: Understanding ----------
    6: {
        "phase": 2,
        "communication_type": "understanding",
        "title_en": "6. Explaining reason for a poor evaluation",
        "title_de": "6. Grund für eine schlechte Bewertung erklären",
        "user_en": COMMON_USER_HEADER_EN + """
Explain criteria and reasons clearly.

• Listen actively  
• Aim for mutual understanding
""" + FRAMEWORK_UNDERSTANDING_EN,
        "partner_en": """
You are the PERSON evaluated.

- Hurt  
- Want clear explanation  
- Accept fairness
""",
        "user_de": COMMON_USER_HEADER_DE + """
Sie erklären eine schlechte Bewertung.

• Kriterien erläutern  
• Aktiv zuhören  
• Gegenseitiges Verständnis herstellen
""" + FRAMEWORK_UNDERSTANDING_DE,
        "partner_de": """
Sie sind die PERSON.

- Enttäuscht  
- Will nachvollziehbare Erklärung  
- Akzeptiert bei Klarheit
""",
    },

    # ---------- 7 ----------
    7: {
        "phase": 2,
        "communication_type": "understanding",
        "title_en": "7. Explaining neutrality in a conflict",
        "title_de": "7. Erklären, dass ich neutral bleibe",
        "user_en": COMMON_USER_HEADER_EN + """
Someone feels you took sides.

• Explain neutrality  
• Clarify your role  
• Preserve trust
""" + FRAMEWORK_UNDERSTANDING_EN,
        "partner_en": """
You are the CONFLICTING PARTY.

- Feels unsupported  
- Questions neutrality  
- Satisfied if role explained
""",
        "user_de": COMMON_USER_HEADER_DE + """
Ihnen wird Parteilichkeit vorgeworfen.

• Neutralität erklären  
• Rolle klären  
• Vertrauen erhalten
""" + FRAMEWORK_UNDERSTANDING_DE,
        "partner_de": """
Sie sind die KONFLIKTPARTEI.

- Zweifelt an Neutralität  
- Will gesehen werden  
- Akzeptiert klare Rollenklärung
""",
    },

    # ---------- 8 ----------
    8: {
        "phase": 2,
        "communication_type": "understanding",
        "title_en": "8. Advising someone to make a good decision",
        "title_de": "8. Jemanden beraten, eine gute Entscheidung zu treffen",
        "user_en": COMMON_USER_HEADER_EN + """
Help the person think clearly.

• Clarify options  
• Support autonomy
""" + FRAMEWORK_UNDERSTANDING_EN,
        "partner_en": """
You are the PERSON seeking advice.

- Unsure  
- Thinking aloud  
- Decides themselves
""",
        "user_de": COMMON_USER_HEADER_DE + """
Sie beraten eine Person bei einer Entscheidung.

• Optionen klären  
• Selbstständigkeit stärken
""" + FRAMEWORK_UNDERSTANDING_DE,
        "partner_de": """
Sie sind die PERSON.

- Unsicher  
- Sortiert Gedanken  
- Entscheidet selbst
""",
    },

    # ---------- 9 ----------
    9: {
        "phase": 2,
        "communication_type": "understanding",
        "title_en": "9. Explaining viewpoint on feedback procedures",
        "title_de": "9. Sicht auf Feedbackverfahren erklären",
        "user_en": COMMON_USER_HEADER_EN + """
You are sceptical of new feedback criteria focusing on personality.

• Explain reservations  
• Give suggestions  
• Maintain cooperation
""" + FRAMEWORK_UNDERSTANDING_EN,
        "partner_en": """
You are the PRINCIPAL.

- Open atmosphere  
- Feedback is for development  
- Accept suggestions
""",
        "user_de": COMMON_USER_HEADER_DE + """
Sie sind skeptisch gegenüber neuen Feedbackkriterien.

• Bedenken darlegen  
• Vorschläge machen  
• Kooperation erhalten
""" + FRAMEWORK_UNDERSTANDING_DE,
        "partner_de": """
Sie sind die SCHULLEITUNG.

- Offen für Anregungen  
- Entwicklungsorientiert  
- Klare nächste Schritte
""",
    },

    # ---------- 10 ----------
    10: {
        "phase": 2,
        "communication_type": "understanding",
        "title_en": "10. Developing guidelines with a colleague",
        "title_de": "10. Leitlinien gemeinsam entwickeln",
        "user_en": COMMON_USER_HEADER_EN + """
Work together constructively.

• Bring ideas  
• Build on each other  
• Joint product
""" + FRAMEWORK_UNDERSTANDING_EN,
        "partner_en": """
You are the COLLEAGUE.

- Own ideas  
- Cooperative  
- Appreciates listening
""",
        "user_de": COMMON_USER_HEADER_DE + """
Sie entwickeln Leitlinien mit einer Kollegin/einem Kollegen.

• Vorschläge einbringen  
• Anknüpfen  
• Gemeinsames Ergebnis
""" + FRAMEWORK_UNDERSTANDING_DE,
        "partner_de": """
Sie sind die KOLLEGI

