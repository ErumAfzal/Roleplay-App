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
✅ Reply “NEXT” to receive PART 2 (Roleplay definitions)




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
  (what could happen, what you fear or hope). 

• Context: Often power difference  
• Goal: Achieve your desired outcome strategically
"""

FRAMEWORK_STRATEGIC_DE = """
**Kommunikationsrahmen – Strategische Kommunikation**

• Gesprächsabsicht: Beziehungsziel im Vordergrund  
• Sachziel: Menge/Qualität/Relevanz/Klarheit dürfen bewusst verletzt werden,
  wenn es dem strategischen Ziel dient  
• Beziehungsziel: Häufig zukunftsorientierte Selbstoffenbarung  

• Kontext: Häufig Machtunterschied  
• Ziel: Gewünschtes Ergebnis strategisch erreichen
"""

FRAMEWORK_UNDERSTANDING_EN = """
**Communication framework – Understanding-oriented communication**

• Content goal in the foreground  
• Clear, honest, relevant communication  
• Use authentic self-disclosure  
• Aim: mutual understanding & stable relationship
"""

FRAMEWORK_UNDERSTANDING_DE = """
**Kommunikationsrahmen – Verstehensorientierte Kommunikation**

• Sachziel im Vordergrund  
• Klar, ehrlich, relevant kommunizieren  
• Authentische Selbstoffenbarung  
• Ziel: gegenseitiges Verstehen & tragfähige Beziehung
"""

# ---------------------------------------------------------
#  ROLEPLAYS 1–10
# ---------------------------------------------------------

ROLEPLAYS = {

    # ---------- 1 ----------
    1: {
        "phase": 1,
        "communication_type": "strategic",
        "title_en": "1. Convincing supervisor to approve a training course",
        "title_de": "1. Vorgesetzte/n überzeugen, eine Fortbildung zu genehmigen",
        "user_en": COMMON_USER_HEADER_EN + """
You want to attend a PD course on self-directed learning. The principal is sceptical.

**Your task:**
• Explain benefits for you AND the school  
• Address concerns (budget/organisation)  
• Maintain professional relationship
""" + FRAMEWORK_STRATEGIC_EN,
        "partner_en": """
You are the PRINCIPAL.

- Ask for school benefit  
- Worry about costs & substitution  
- Agree only with clear link to school development
""",
        "user_de": COMMON_USER_HEADER_DE + """
Sie möchten eine Fortbildung besuchen. Die Schulleitung ist skeptisch.

**Ihre Aufgabe:**
• Nutzen für Schule & Person erklären  
• Bedenken ansprechen  
• Professionelle Beziehung erhalten
""" + FRAMEWORK_STRATEGIC_DE,
        "partner_de": """
Sie sind die SCHULLEITUNG.

- Fragen nach schulischem Nutzen  
- Sorgen um Kosten & Organisation  
- Zustimmung nur bei klarer Relevanz
""",
    },

    # ---------- 2 ----------
    2: {
        "phase": 1,
        "communication_type": "strategic",
        "title_en": "2. Convincing a student to join a group",
        "title_de": "2. Schüler/in überzeugen, eine AG zu wählen",
        "user_en": COMMON_USER_HEADER_EN + """
The student prefers judo over theatre despite talent.

**Your task:**
• Encourage theatre AG  
• Emphasise talent and development  
• Maintain trust
""" + FRAMEWORK_STRATEGIC_EN,
        "partner_en": """
You are the STUDENT.

- Prefer judo  
- Open but sceptical  
- May accept theatre with support
""",
        "user_de": COMMON_USER_HEADER_DE + """
Schüler/in will lieber Judo als Theater.

**Ihre Aufgabe:**
• Für Theater argumentieren  
• Talent betonen  
• Vertrauensvolle Beziehung halten
""" + FRAMEWORK_STRATEGIC_DE,
        "partner_de": """
Sie sind der/die SCHÜLER/IN.

- Möchte Judo  
- Offen für Argumente  
- Theater bei guter Unterstützung möglich
""",
    },

    # ---------- 3 ----------
    3: {
        "phase": 1,
        "communication_type": "strategic",
        "title_en": "3. Talking to a colleague who misses deadlines",
        "title_de": "3. Kolleg/in auf verpasste Termine ansprechen",
        "user_en": COMMON_USER_HEADER_EN + """
A colleague frequently misses deadlines.

**Your task:**
• Address behaviour clearly  
• Maintain cooperation  
• Work toward change
""" + FRAMEWORK_STRATEGIC_EN,
        "partner_en": """
You are the COLLEAGUE.

- Downplays issues  
- Avoids discomfort  
- Becomes cooperative with respectful clarity
""",
        "user_de": COMMON_USER_HEADER_DE + """
Kolleg/in hält Termine nicht ein.

**Ihre Aufgabe:**
• Klar ansprechen  
• Beziehung erhalten  
• Veränderung vereinbaren
""" + FRAMEWORK_STRATEGIC_DE,
        "partner_de": """
Sie sind die KOLLEGIN/der KOLLEGE.

- Spielt Problem herunter  
- Weicht aus  
- Wird einsichtig bei klarer, respektvoller Ansprache
""",
    },

    # ---------- 4 ----------
    4: {
        "phase": 1,
        "communication_type": "strategic",
        "title_en": "4. Getting a colleague to be punctual",
        "title_de": "4. Kolleg/in zu Pünktlichkeit bewegen",
        "user_en": COMMON_USER_HEADER_EN + """
Colleague arrives late regularly.

**Task:**  
• Focus on behaviour  
• Explain consequences  
• Aim for clear agreement
""" + FRAMEWORK_STRATEGIC_EN,
        "partner_en": """
You are the COLLEAGUE.

- Minimises lateness  
- Provides excuses  
- Accepts clear expectations
""",
        "user_de": COMMON_USER_HEADER_DE + """
Kolleg/in kommt oft zu spät.

**Aufgabe:**  
• Verhalten ansprechen  
• Folgen erklären  
• Vereinbarung treffen
""" + FRAMEWORK_STRATEGIC_DE,
        "partner_de": """
Sie sind die KOLLEGIN/der KOLLEGE.

- Hält es für „nicht schlimm“  
- Bringt Ausreden  
- Einsichtig bei klaren Erwartungen
""",
    },

    # ---------- 5 ----------
    5: {
        "phase": 1,
        "communication_type": "strategic",
        "title_en": "5. Convincing supervisor to reduce my hours",
        "title_de": "5. Stundenreduzierung beantragen",
        "user_en": COMMON_USER_HEADER_EN + """
You need reduced hours for personal reasons.

**Task:**  
• Explain carefully  
• Show commitment  
• Understand organisational limits
""" + FRAMEWORK_STRATEGIC_EN,
        "partner_en": """
You are the SUPERVISOR.

- Worry about staffing  
- Ask for reasoning  
- May accept compromise
""",
        "user_de": COMMON_USER_HEADER_DE + """
Sie wollen Stunden reduzieren.

**Aufgabe:**  
• Gründe vorsichtig erklären  
• Engagement zeigen  
• Zwänge verstehen
""" + FRAMEWORK_STRATEGIC_DE,
        "partner_de": """
Sie sind die SCHULLEITUNG.

- Sorgen um Versorgung  
- Fragen nach Gründen  
- Kompromisse möglich
""",
    },

    # ---------- 6 ----------
    6: {
        "phase": 2,
        "communication_type": "understanding",
        "title_en": "6. Explaining the reason for a poor evaluation",
        "title_de": "6. Schlechte Bewertung erklären",
        "user_en": COMMON_USER_HEADER_EN + """
Explain criteria clearly.

• Listen to feelings  
• Aim for understanding
""" + FRAMEWORK_UNDERSTANDING_EN,
        "partner_en": """
You are the PERSON with the poor evaluation.

- Hurt  
- Wants explanation  
- Accepts fairness
""",
        "user_de": COMMON_USER_HEADER_DE + """
Schlechte Bewertung erklären.

• Kriterien erläutern  
• Zuhören  
• Verständnis erreichen
""" + FRAMEWORK_UNDERSTANDING_DE,
        "partner_de": """
Sie sind die PERSON.

- Enttäuscht  
- Will Klarheit  
- Akzeptiert bei Transparenz
""",
    },

    # ---------- 7 ----------
    7: {
        "phase": 2,
        "communication_type": "understanding",
        "title_en": "7. Explaining neutrality in a conflict",
        "title_de": "7. Neutralität erklären",
        "user_en": COMMON_USER_HEADER_EN + """
A person accuses you of taking sides.

• Explain neutrality  
• Clarify role  
• Show empathy
""" + FRAMEWORK_UNDERSTANDING_EN,
        "partner_en": """
You are the CONFLICTING PARTY.

- Feels unsupported  
- Questions neutrality  
- Accepts role explanation
""",
        "user_de": COMMON_USER_HEADER_DE + """
Ihnen wird Parteilichkeit vorgeworfen.

• Neutralität erklären  
• Rolle klären  
• Empathie zeigen
""" + FRAMEWORK_UNDERSTANDING_DE,
        "partner_de": """
Sie sind die KONFLIKTPARTEI.

- Zweifel an Neutralität  
- Will verstanden werden  
- Akzeptiert klare Rollenklärung
""",
    },

    # ---------- 8 ----------
    8: {
        "phase": 2,
        "communication_type": "understanding",
        "title_en": "8. Advising someone to make a good decision",
        "title_de": "8. Entscheidung beraten",
        "user_en": COMMON_USER_HEADER_EN + """
Help structure thinking.

• Clarify options  
• Strengthen autonomy
""" + FRAMEWORK_UNDERSTANDING_EN,
        "partner_en": """
You are the PERSON seeking advice.

- Unsure  
- Thinking aloud  
- Decides independently
""",
        "user_de": COMMON_USER_HEADER_DE + """
Sie beraten eine Person.

• Optionen klären  
• Autonomie stärken
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
You are sceptical about new feedback criteria.

• Explain reservations  
• Suggest criteria  
• Maintain cooperation
""" + FRAMEWORK_UNDERSTANDING_EN,
        "partner_en": """
You are the PRINCIPAL.

- Supportive  
- Feedback for development  
- Open to suggestions
""",
        "user_de": COMMON_USER_HEADER_DE + """
Sie sind skeptisch gegenüber neuen Feedbackkriterien.

• Bedenken darlegen  
• Vorschläge machen  
• Zusammenarbeit sichern
""" + FRAMEWORK_UNDERSTANDING_DE,
        "partner_de": """
Sie sind die SCHULLEITUNG.

- Unterstützend  
- Entwicklungsorientiert  
- Offen für Vorschläge
""",
    },

    # ---------- 10 ----------
    10: {
        "phase": 2,
        "communication_type": "understanding",
        "title_en": "10. Developing guidelines with a colleague",
        "title_de": "10. Leitlinien mit Kolleg/in entwickeln",
        "user_en": COMMON_USER_HEADER_EN + """
Develop guidelines together.

• Offer ideas  
• Build on suggestions  
• Aim for shared outcome
""" + FRAMEWORK_UNDERSTANDING_EN,
        "partner_en": """
You are the COLLEAGUE.

- Has ideas  
- Cooperative  
- Appreciates listening
""",
        "user_de": COMMON_USER_HEADER_DE + """
Sie entwickeln gemeinsam einen Leitfaden.

• Ideen einbringen  
• Anknüpfen  
• Gemeinsames Ergebnis
""" + FRAMEWORK_UNDERSTANDING_DE,
        "partner_de": """
Sie sind die KOLLEGIN/der KOLLEGE.

- Eigene Vorstellungen  
- Kompromissbereit  
- Schätzt gutes Zuhören
""",
    },
}

# ---------------------------------------------------------
#  Streamlit UI & Flow Logic
# ---------------------------------------------------------

st.set_page_config(page_title="Role-Play Communication Trainer", layout="wide")

st.title("Role-Play Communication Trainer")

st.sidebar.header("Settings")

language = st.sidebar.radio("Language / Sprache", ["English", "Deutsch"])
student_id = st.sidebar.text_input(
    "Student ID or nickname",
    help="Used only to identify your sessions in the dataset.",
)

# Batch flow control:
# batch_step: "batch1", "batch2", "finished"
if "batch_step" not in st.session_state:
    st.session_state.batch_step = "batch1"

# Chat/feedback state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "chat_active" not in st.session_state:
    st.session_state.chat_active = False
if "feedback_done" not in st.session_state:
    st.session_state.feedback_done = False
if "meta" not in st.session_state:
    st.session_state.meta = {}

# OpenAI client
client = setup_openai_client()
if client is None:
    st.stop()

# Determine current batch
if st.session_state.batch_step == "batch1":
    current_phase = 1
    batch_label_en = "Batch 1 – Role-Plays 1–5"
    batch_label_de = "Block 1 – Rollenspiele 1–5"
elif st.session_state.batch_step == "batch2":
    current_phase = 2
    batch_label_en = "Batch 2 – Role-Plays 6–10"
    batch_label_de = "Block 2 – Rollenspiele 6–10"
else:
    current_phase = None

if st.session_state.batch_step == "finished":
    st.success(
        "You have completed one role-play from Batch 1 and one from Batch 2. Thank you!"
        if language == "English"
        else "Sie haben je ein Rollenspiel aus Block 1 und Block 2 abgeschlossen. Vielen Dank!"
    )
    st.stop()

batch_title = batch_label_en if language == "English" else batch_label_de
st.subheader(batch_title)

# Choose roleplays for this batch
available_ids = [rid for rid, r in ROLEPLAYS.items() if r["phase"] == current_phase]

roleplay_id = st.selectbox(
    "Choose a role-play / Wählen Sie ein Rollenspiel",
    available_ids,
    format_func=lambda rid: ROLEPLAYS[rid]["title_en"]
    if language == "English"
    else ROLEPLAYS[rid]["title_de"],
)

current_rp = ROLEPLAYS[roleplay_id]

# Reset conversation if roleplay, language or batch changed
if (
    st.session_state.meta.get("roleplay_id") != roleplay_id
    or st.session_state.meta.get("language") != language
    or st.session_state.meta.get("batch_step") != st.session_state.batch_step
):
    st.session_state.messages = []
    st.session_state.chat_active = False
    st.session_state.feedback_done = False
    st.session_state.meta = {
        "student_id": student_id,
        "language": language,
        "batch_step": st.session_state.batch_step,
        "roleplay_id": roleplay_id,
        "roleplay_title_en": current_rp["title_en"],
        "roleplay_title_de": current_rp["title_de"],
        "communication_type": current_rp["communication_type"],
    }

# ---------------------------------------------------------
#  Instructions
# ---------------------------------------------------------

st.subheader("Instructions for YOU" if language == "English" else "Anweisungen für SIE")

if language == "English":
    st.markdown(current_rp["user_en"])
else:
    st.markdown(current_rp["user_de"])

with st.expander(
    "🤖 Hidden instructions for the AI partner (teacher view)"
    if language == "Eng.

✅ New lish"
    else "🤖 Verdeckte Anweisungen für die KI-Gesprächspartner:in (nur Lehrkraft)"
):
    if language == "English":
        st.markdown(current_rp["partner_en"])
    else:
        st.markdown(current_rp["partner_de"])

st.info(
    "Suggested maximum conversation time: about 10 minutes. "
    "You can end the conversation at any time by writing "
    "“Thank you, goodbye” / „Danke, tschüss“."
)

# ---------------------------------------------------------
#  Start/restart conversation
# ---------------------------------------------------------

if st.button("Start / Restart conversation"):
    st.session_state.messages = []
    st.session_state.feedback_done = False
    st.session_state.chat_active = True

    system_prompt = current_rp["partner_en"] if language == "English" else current_rp["partner_de"]

    st.session_state.messages.append(
        {
            "role": "system",
            "content": (
                "You are the simulated conversation partner in a role-play.\n"
                "Follow these instructions carefully and stay in character.\n\n"
                + system_prompt
            ),
        }
    )

# ---------------------------------------------------------
#  Chat interface
# ---------------------------------------------------------

st.subheader("Conversation" if language == "English" else "Gespräch")

chat_container = st.container()

with chat_container:
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.markdown(f"**You:** {msg['content']}")
        elif msg["role"] == "assistant":
            label = "AI Partner" if language == "English" else "Gesprächspartner:in (KI)"
            st.markdown(f"**{label}:** {msg['content']}")

if st.session_state.chat_active and not st.session_state.feedback_done:
    prompt_label = (
        "Write your next message…" if language == "English" else "Schreiben Sie Ihre nächste Nachricht…"
    )
    user_input = st.chat_input(prompt_label)

    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=st.session_state.messages,
                temperature=0.7,
                max_tokens=400,
            )
            reply = response.choices[0].message.content
        except Exception as e:
            reply = f"[Error from OpenAI API: {e}]"

        st.session_state.messages.append({"role": "assistant", "content": reply})
        st.rerun()

if st.session_state.chat_active and not st.session_state.feedback_done:
    if st.button("⏹ End conversation / Gespräch beenden"):
        st.session_state.chat_active = False


# ---------------------------------------------------------
#  Feedback after each batch role-play (Q1–Q12 Version)
# ---------------------------------------------------------

if not st.session_state.chat_active and st.session_state.messages and not st.session_state.feedback_done:
    st.subheader("Short feedback / Kurzes Feedback")

    if language == "English":
        # Personality
        q1 = st.radio("The chatbot’s personality was realistic and engaging", [1, 2, 3, 4, 5], horizontal=True)
        q2 = st.radio("The chatbot seemed too robotic", [1, 2, 3, 4, 5], horizontal=True)

        # Onboarding
        q3 = st.radio("The chatbot was welcoming during initial setup", [1, 2, 3, 4, 5], horizontal=True)
        q4 = st.radio("The chatbot seemed very unfriendly", [1, 2, 3, 4, 5], horizontal=True)
        q5 = st.radio("The chatbot explained its scope and purpose well", [1, 2, 3, 4, 5], horizontal=True)
        q6 = st.radio("The chatbot gave no indication as to its purpose", [1, 2, 3, 4, 5], horizontal=True)

        # User Experience
        q7 = st.radio("The chatbot was easy to navigate", [1, 2, 3, 4, 5], horizontal=True)
        q8 = st.radio("It would be easy to get confused when using the chatbot", [1, 2, 3, 4, 5], horizontal=True)
        q11 = st.radio("The chatbot was easy to use", [1, 2, 3, 4, 5], horizontal=True)
        q12 = st.radio("The chatbot was very complex", [1, 2, 3, 4, 5], horizontal=True)

        # Error Management
        q9 = st.radio("The chatbot coped well with any errors or mistakes", [1, 2, 3, 4, 5], horizontal=True)
        q10 = st.radio("The chatbot seemed unable to cope with any errors", [1, 2, 3, 4, 5], horizontal=True)

        comment = st.text_area("Optional comment")
        submit_label = "Save feedback & chat"

    else:
        # Personality (German)
        q1 = st.radio("Die Persönlichkeit des Chatbots war realistisch und ansprechend", [1, 2, 3, 4, 5], horizontal=True)
        q2 = st.radio("Der Chatbot wirkte zu robotisch", [1, 2, 3, 4, 5], horizontal=True)

        # Onboarding
        q3 = st.radio("Der Chatbot war beim ersten Setup einladend", [1, 2, 3, 4, 5], horizontal=True)
        q4 = st.radio("Der Chatbot wirkte sehr unfreundlich", [1, 2, 3, 4, 5], horizontal=True)
        q5 = st.radio("Der Chatbot erklärte seinen Zweck und Umfang gut", [1, 2, 3, 4, 5], horizontal=True)
        q6 = st.radio("Der Chatbot gab keinen Hinweis auf seinen Zweck", [1, 2, 3, 4, 5], horizontal=True)

        # User Experience
        q7 = st.radio("Der Chatbot war leicht zu navigieren", [1, 2, 3, 4, 5], horizontal=True)
        q8 = st.radio("Die Nutzung des Chatbots wäre leicht verwirrend", [1, 2, 3, 4, 5], horizontal=True)
        q11 = st.radio("Der Chatbot war leicht zu bedienen", [1, 2, 3, 4, 5], horizontal=True)
        q12 = st.radio("Der Chatbot war sehr komplex", [1, 2, 3, 4, 5], horizontal=True)

        # Error Management
        q9 = st.radio("Der Chatbot ging gut mit Fehlern oder Missverständnissen um", [1, 2, 3, 4, 5], horizontal=True)
        q10 = st.radio("Der Chatbot konnte nicht gut mit Fehlern umgehen", [1, 2, 3, 4, 5], horizontal=True)

        comment = st.text_area("Optionaler Kommentar")
        submit_label = "Feedback & Chat speichern"

    # Submit Button
    if st.button(submit_label):

        feedback_data = {
            "Q1": q1,
            "Q2": q2,
            "Q3": q3,
            "Q4": q4,
            "Q5": q5,
            "Q6": q6,
            "Q7": q7,
            "Q8": q8,
            "Q9": q9,
            "Q10": q10,
            "Q11": q11,
            "Q12": q12,
            "comment": comment,
        }

        append_chat_and_feedback_to_sheets(
            st.session_state.meta,
            st.session_state.messages,
            feedback_data,
        )

        st.session_state.feedback_done = True

        # Move from batch1 -> batch2 -> finished
        if st.session_state.batch_step == "batch1":
            st.session_state.batch_step = "batch2"
            msg = (
                "Thank you! Batch 1 is completed. Please continue with Batch 2 (Role-Plays 6–10)."
                if language == "English"
                else "Danke! Block 1 ist abgeschlossen. Bitte machen Sie mit Block 2 (Rollenspiele 6–10) weiter."
            )
            st.success(msg)
        else:
            st.session_state.batch_step = "finished"
            msg = (
                "Thank you! You completed both batches."
                if language == "English"
                else "Vielen Dank! Sie haben beide Blöcke abgeschlossen."
            )
            st.success(msg)

        # Clear chat for next step
        st.session_state.messages = []

