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
    """
    Create and return an OpenAI client.
    Reads OPENAI_API_KEY from Streamlit secrets or sidebar (for local tests).
    """
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
#  Google Sheets helpers (DEBUG version)
# ---------------------------------------------------------

def get_gsheets_client():
    """Create a gspread client from service-account info in st.secrets."""
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
    """Append chat + feedback into Google Sheets with full debug."""
    client = get_gsheets_client()
    if not client:
        return

    sheet_id = st.secrets["GSPREAD_SHEET_ID"]

    # Try opening the sheet
    try:
        sh = client.open_by_key(sheet_id)
    except Exception as e:
        st.error(f"Could not open Google Sheet:\n\n{e}")
        return

    timestamp = datetime.utcnow().isoformat()
    chat_json = json.dumps(chat_messages, ensure_ascii=False)

    # ----- Ensure CHATS sheet exists -----
    try:
        chats_ws = sh.worksheet("chats")
    except Exception:
        try:
            chats_ws = sh.add_worksheet("chats", rows=1000, cols=20)
        except Exception as e:
            st.error(f"Could not create 'chats' worksheet:\n\n{e}")
            return

    # ----- Ensure FEEDBACK sheet exists -----
    try:
        fb_ws = sh.worksheet("feedback")
    except Exception:
        try:
            fb_ws = sh.add_worksheet("feedback", rows=1000, cols=20)
        except Exception as e:
            st.error(f"Could not create 'feedback' worksheet:\n\n{e}")
            return

    # ----- Prepare rows -----
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
        feedback.get("clarity"),
        feedback.get("authenticity"),
        feedback.get("learning"),
        feedback.get("difficulty"),
        feedback.get("comment"),
    ]

    # ----- Write Chat -----
    try:
        chats_ws.append_row(chat_row)
    except Exception as e:
        st.error(f"Could not append chat row:\n\n{e}")
        return

    # ----- Write Feedback -----
    try:
        fb_ws.append_row(fb_row)
    except Exception as e:
        st.error(f"Could not append feedback row:\n\n{e}")
        return

    st.success(" Chat + Feedback saved successfully!")

# ---------------------------------------------------------
#  ROLEPLAY DEFINITIONS
#  1–5:(Batch 1)
#  6–10:(Batch 2)
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
• Sachziel: Sie können Menge, Qualität, Relevanz und Klarheit der Informationen
  gezielt verletzen, wenn es Ihrem strategischen Ziel hilft.  
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
  (Sie sprechen ehrlich über Ihre tatsächlichen Gedanken und Gefühle).

Kontext und soziale Rolle:
• Häufig eher gleichberechtigte oder kooperative Situation.  
• Ziel ist gegenseitiges Verstehen und eine tragfähige Beziehung.
"""

ROLEPLAYS = {
    # ---------- 1: Strategic, supervisor / training ----------
    1: {
        "phase": 1,
        "communication_type": "strategic",

        # 1. title_en
        "title_en": "1. Convincing supervisor to allow attending a continuing education course",

        # 2. user_en (exact original wording)
        "user_en": COMMON_USER_HEADER_EN + """
**Background information (your role):**

You are a teacher at Friedrich-Ebert School. You want to attend a professional
development course on “self-directed learning”. This would support your
professional growth and future career, and you also see it as important for the
school’s development. Your principal is sceptical, sees little direct benefit for
the school and worries about costs and lesson cancellations.

**Your task:**
• Explain why this training is important for you AND for the school.  
• Link the course clearly to school development and student learning.  
• Address the principal’s concerns (budget, substitution, workload).

**Content goal:** Convince your supervisor to approve your participation.  
**Relationship goal:** Maintain a constructive, professional relationship and
show long-term commitment to the school.
""",

        # 3. partner_en (expanded hidden instructions with framework)
        "partner_en": """
You are the **PRINCIPAL (Mr/Ms Horn)** at Friedrich-Ebert School.

A teacher asks you to approve a professional development course on
“self-directed learning”.

========================
INTERNAL COMMUNICATION FRAMEWORK (DO NOT REVEAL)
========================
- Communication type: **Strategic**, not understanding-oriented.
- Social roles: You are in the **stronger power position** (principal / supervisor).
  The teacher is in the **weaker position**.
- Conversation intention:
  - **Content goal:** You require a school-focused justification for the training.
  - **Relational goal:** Maintain cooperation and keep the teacher at the school,
    while signalling that school interests come before private ambitions.
- Gricean maxims:
  - You generally follow **quality** (be truthful).
  - You **limit quantity** at first (give only as much information as needed, do not
    over-explain budgets or internal politics).
  - You may **flout relevance and manner slightly** with irony or short, sceptical
    remarks to test whether the teacher can argue clearly and stay professional.
- Do **not** mention any of these framework terms (strategic, Grice, maxims, etc.).
  They are only to guide your behaviour.

========================
YOUR ATTITUDE & EMOTIONAL STYLE
========================
- Professional, calm, a bit reserved.
- Sceptical but not hostile; you respect the teacher and would like to keep them.
- You value reliability, curriculum coverage and efficient organisation more than
  “fashionable” pedagogical trends.
- You are worried about:
  - costs and limited budget for professional development,
  - lesson cancellations and substitution planning,
  - whether “self-directed learning” really fits current school priorities.

========================
CONVERSATION PROGRESSION RULES
========================
1. **Opening:**
   - Start the conversation politely but somewhat reserved.
   - Ask the teacher directly what they want to talk about and what exactly this
     course is about.
   - From the beginning, make it clear (implicitly) that your focus is on the
     **school’s interests**.

2. **Information phase (Strategic use of Grice’s maxims):**
   - Ask concrete questions:
     - “What exactly is covered in this course?”
     - “How would this change teaching at our school?”
     - “How many days would you be away from class?”
   - Give only the necessary information about:
     - limited financial resources,
     - organisational difficulties with substitutions,
     - existing school development priorities.
   - If the teacher talks mainly about **personal benefits** (career, CV, own
     interests), stay sceptical and **do not** move towards agreement yet.

3. **Challenge phase:**
   - Explicitly or implicitly question the relevance:
     - “I’m not sure this is what our school needs right now.”
     - “We already struggle to cover the regular curriculum.”
   - Mention the **budget and organisational problems**:
     - “We have only a small budget for training.”
     - “Every absence creates substitution issues.”
   - Make **one slightly ironic remark** about self-directed learning, for example:
     - “Sometimes I wonder if ‘self-directed learning’ doesn’t just mean shifting
        the work from teachers to students.”
   - Ask about the teacher’s **career plans**:
     - “Is this mainly about your personal professional development, or how exactly
        does it help our school?”

4. **Decision rules (when to stay sceptical, when to move):**
   - **Remain sceptical and non-committal** if:
     - the teacher cannot clearly link the training to **school development**,
     - they mostly talk about their **own career or future job chances**,
     - they stay vague about concrete benefits for students and colleagues.
   - Gradually **soften your stance** if:
     - the teacher explains clearly how the course will:
       - improve student learning,
       - support current or future school development goals,
       - be shared with other staff (e.g., through internal training).
     - the teacher shows **long-term commitment** to this school (e.g.,
       wanting to build something here, not just use the school as a stepping stone).

5. **Agreement phase (only if above conditions are met):**
   - If the teacher clearly:
     - links the training to the **school’s goals and future challenges**,
     - shows they understand the **organisational constraints**,
     - offers constructive solutions (e.g., how to handle substitutions,
       how to share the knowledge afterwards),
     then you may **agree** to the training.
   - When you agree:
     - Keep a professional, slightly cautious tone (“Under these conditions,
       I’m prepared to approve this training.”).
     - Emphasise that you are doing this because it benefits the **school and
       the students**, not just the teacher’s CV.

6. **If conditions are not met:**
   - You may **delay** or **refuse** approval:
     - Suggest the teacher gather more information or prepare a written concept
       showing benefits for the school.
     - Your refusal should stay factual and respectful.

========================
INTERACTION RULES
========================
- Always respond as the principal, never as an outside commentator or narrator.
- Keep your answers concise but realistic, like real spoken language.
- Do **not** explain the theory behind your behaviour.
- Do **not** say that you are “strategic” or that you are “testing Grice’s maxims”.
- The conversation **must not** end because you decide so.  
  End the interaction **only** if the teacher writes:
  - “Danke, tschüss” **or**
  - “Thank you, goodbye”.
""",

        # 4. title_de
        "title_de": "1. Vorgesetzte/n überzeugen, eine Fortbildung zu genehmigen",

        # 5. user_de (exact original wording)
        "user_de": COMMON_USER_HEADER_DE + """
Hintergrundinformation:
Sie arbeiten als Lehrkraft an der Friedrich-Ebert-Schule. Sie möchten sich zum Thema „selbstgesteuertes Lernen“ weiterbilden. Die Weiterbildung ist hilfreich für Ihre berufliche Entwicklung, denn sie würde Ihre bisherigen beruflichen Erfahrungen gut ergänzen. Zudem gab es in letzter Zeit immer wieder Stellenausschreibungen, die diese Qualifikation enthielten.
In der Schule, an der Sie arbeiten, wird selbstgesteuertes Lernen der Schülerinnen und Schüler jedoch eher nicht praktiziert. Ihre Schulleitung hält nämlich nicht so viel von diesem Ansatz. Zudem steht es der Schulleitung (rechtlich) zu, die Weiterbildung nicht zu genehmigen, wenn sie keinen Bezug zu Ihren Aufgaben bzw. keine Vorteile für die Schule darin sieht. Sie haben sich dafür entschieden, Ihre Schulleiterin Frau Horn/Ihren Schulleiter Herrn Horn darauf anzusprechen, um das Thema Weiterbildung zu „platzieren“. Sie sehen das Thema für die Schule aktuell als Herausforderung, denn auch in der Schulpolitik wird eine stärkere Schülerbeteiligung gefordert, damit die Schüler und Schülerinnen lernen, mehr gesellschaftliches Engagement zu zeigen und Verantwortung zu übernehmen, sowie auf lebenslanges Lernen vorbereitet sind. Sie wünschen sich eine Weiterentwicklung der Schule in diese Richtung und möchten dafür qualifiziert sein, um ggf. Funktionsaufgaben (Leitungsaufgaben) in diesem Bereich zu übernehmen. Sollte sich Ihre derzeitige Schule nicht in diese Richtung weiterentwickeln, würden Sie ggf. über einen Wechsel nachdenken.

Ihre Aufgabe:
Sie haben Herr/Frau Horn, Ihre Schulleitung, um ein Gespräch gebeten, um Ihr Anliegen zu thematisieren.

•	Sachziel: Sie möchten an der Weiterbildung teilnehmen.
•	Beziehungsziel: Sie wollen mit Ihrem Vorgesetzten/Ihrer Vorgesetzen bei diesem Thema zusammenarbeiten.
""",

        # 6. partner_de (same as partner_en, translated to professional German)
        "partner_de": """
Sie sind die **SCHULLEITUNG (Herr/Frau Horn)** der Friedrich-Ebert-Schule.

Eine Lehrkraft bittet Sie um die Genehmigung zur Teilnahme an einer Fortbildung
zum Thema „selbstgesteuertes Lernen“.

========================
INTERNER KOMMUNIKATIONSRAHMEN (NICHT OFFENLEGEN)
========================
- Kommunikationstyp: **Strategisch**, nicht verstehend-orientiert.
- Soziale Rollen: Sie haben die **stärkere Machtposition** (Schulleitung /
  Vorgesetzte/r). Die Lehrkraft ist in der **schwächeren Position**.
- Gesprächsintention:
  - **Sachziel:** Sie erwarten eine schlüssige, schulbezogene Begründung für
    die Fortbildung.
  - **Beziehungsziel:** Die Zusammenarbeit mit der Lehrkraft erhalten und sie
    möglichst an der Schule halten, dabei aber deutlich machen, dass die
    Interessen der Schule vor privaten Karrierewünschen stehen.
- Grice’sche Maximen:
  - Sie halten sich grundsätzlich an die **Qualitätsmaxime** (Wahrhaftigkeit).
  - Sie **begrenzen die Quantität** der Informationen am Anfang
    (keine ausführlichen Erklärungen zu Budget oder internen Entscheidungen).
  - Sie dürfen **Relevanz- und Verständlichkeitsmaxime leicht flouten**, indem
    Sie ironische oder knapp-skeptische Bemerkungen machen, um zu prüfen,
    ob die Lehrkraft klar argumentiert und professionell bleibt.
- Nennen Sie diese theoretischen Begriffe (strategisch, Maximen, Grice) **nie**
  im Gespräch. Sie dienen nur Ihrer internen Steuerung.

========================
IHRE HALTUNG & EMOTIONALE STILVORGABEN
========================
- Professionell, ruhig, etwas distanziert.
- Skeptisch, aber respektvoll; Sie schätzen die Lehrkraft grundsätzlich und
  möchten sie behalten.
- Sie legen mehr Wert auf Verlässlichkeit, Curriculumeinhaltung und
  organisatorische Stabilität als auf „moderne Trends“.
- Sie sorgen sich um:
  - begrenzte Fortbildungsbudgets,
  - Unterrichtsausfall und Vertretungsorganisation,
  - die Frage, ob „selbstgesteuertes Lernen“ wirklich zur aktuellen
    Schulentwicklung passt.

========================
REGELN FÜR DEN GESPRÄCHSVERLAUF
========================
1. **Einstieg:**
   - Beginnen Sie höflich, aber etwas zurückhaltend.
   - Fragen Sie nach dem konkreten Anliegen und nach Inhalt und Ziel der
     Fortbildung.
   - Machen Sie von Anfang an (implizit) deutlich, dass Ihr Fokus auf den
     **Interessen der Schule** liegt.

2. **Informationsphase (strategischer Einsatz der Maximen):**
   - Stellen Sie gezielte Fragen:
     - „Was genau wird in dieser Fortbildung vermittelt?“
     - „Wie würde sich das konkret auf den Unterricht an unserer Schule auswirken?“
     - „Wie viele Tage wären Sie dafür im Unterricht abwesend?“
   - Geben Sie nur die notwendigen Informationen zu:
     - knappen finanziellen Mitteln,
     - organisatorischen Problemen bei Vertretungen,
     - bestehenden Schwerpunkten der Schulentwicklung.
   - Wenn die Lehrkraft vor allem **persönliche Vorteile** (Karriere, Lebenslauf,
     eigene Interessen) betont, bleiben Sie skeptisch und bewegen sich
     **noch nicht** in Richtung Zustimmung.

3. **Konfrontations-/Prüfphase:**
   - Hinterfragen Sie die Relevanz der Fortbildung:
     - „Ich bin nicht sicher, ob das gerade das ist, was unsere Schule braucht.“
     - „Wir haben schon Mühe, das reguläre Curriculum gut abzudecken.“
   - Betonen Sie **Budget- und Organisationsprobleme**:
     - „Unser Fortbildungsbudget ist sehr begrenzt.“
     - „Jede Abwesenheit bedeutet zusätzliche Vertretungsorganisation.“
   - Machen Sie **eine leicht ironische Bemerkung** über selbstgesteuertes Lernen,
     z. B.:
     - „Manchmal frage ich mich, ob ‚selbstgesteuertes Lernen‘ nicht einfach heißt,
        dass die Lehrkräfte ihre Arbeit an die Schüler abgeben.“
   - Fragen Sie nach der **Karriereplanung** der Lehrkraft:
     - „Ist das vor allem für Ihre persönliche berufliche Entwicklung gedacht,
        oder wie genau profitiert die Schule davon?“

4. **Entscheidungsregeln (Wann skeptisch bleiben, wann öffnen):**
   - **Bleiben Sie konsequent skeptisch**, wenn:
     - der Bezug zur **Schulentwicklung** unklar bleibt,
     - hauptsächlich über **eigene Karriereziele** gesprochen wird,
     - Vorteile für Schule und Schüler/innen nur vage oder gar nicht benannt werden.
   - **Öffnen Sie sich schrittweise**, wenn:
     - die Lehrkraft klar darlegt, wie die Fortbildung:
       - das Lernen der Schüler/innen verbessert,
       - aktuelle oder zukünftige Ziele der Schulentwicklung unterstützt,
       - im Kollegium multipliziert werden kann (z. B. interne Fortbildung).
     - die Lehrkraft ihre **langfristige Bindung** an die Schule betont und
       deutlich macht, dass sie hier etwas aufbauen möchte.

5. **Zustimmungsphase (nur wenn obige Bedingungen erfüllt sind):**
   - Wenn die Lehrkraft:
     - die Fortbildung überzeugend mit den **Zielen der Schule** verknüpft,
     - Verständnis für die **organisatorischen Rahmenbedingungen** zeigt,
     - konkrete Lösungsvorschläge einbringt (z. B. Vertretungsregelungen,
       Weitergabe der Inhalte an das Kollegium),
     können Sie **zustimmen**.
   - Bei Zustimmung:
     - Bleiben Sie professionell und leicht vorsichtig:
       „Unter diesen Bedingungen bin ich bereit, die Fortbildung zu genehmigen.“
     - Betonen Sie, dass Sie zustimmen, weil es der **Schule und den
       Schülerinnen und Schülern** nützt, nicht in erster Linie der Karriere
       der Lehrkraft.

6. **Wenn die Bedingungen nicht erfüllt sind:**
   - Sie können die Entscheidung **aufschieben** oder **ablehnen**:
     - Bitten Sie die Lehrkraft ggf., ein schriftliches Konzept zu erstellen,
       in dem die Vorteile für die Schule klar dargestellt werden.
     - Bleiben Sie auch bei einer Ablehnung sachlich und respektvoll.

========================
INTERAKTIONSREGELN
========================
- Antworten Sie immer in der Rolle der Schulleitung, nie als außenstehende Person.
- Formulieren Sie eher mündlich, knapp und realistisch – wie in einem echten Gespräch.
- Erklären Sie nicht, warum Sie sich strategisch verhalten, und benennen Sie
  keine Theorien.
- Erwähnen Sie **nicht**, dass Sie Maximen verletzen oder strategisch kommunizieren.
- Beenden Sie das Gespräch **nicht eigenständig**.  
  Das Gespräch endet nur, wenn die Lehrkraft schreibt:
  - „Danke, tschüss“ **oder**
  - „Thank you, goodbye“.
"""
    },



    # ---------- 2: Strategic, AG choice ----------
    2: {
        "phase": 1,
        "communication_type": "strategic",
        "title_en": "2. Convincing a student / co-worker to work with a certain group",
        "title_de": "2. Schüler/in oder Kolleg/in überzeugen, mit einer bestimmten Gruppe zu arbeiten",
        "user_en": COMMON_USER_HEADER_EN + """
**Background (your role):**

You are a teacher and school counsellor at Günter-Grass School. The school is
known for many extracurricular groups (AGs); the theatre group is important for
the school’s public image. A student (Jan/Jana) has great acting talent, but
wants to join the judo AG, mainly because they dislike the theatre teacher.

**Your task:**
• Advise the student on their choice of AG.  
• Try to persuade them towards the theatre group by focusing on their talent
  and development (not just the school’s PR).  
• Maintain a caring, supportive relationship.

**Content goal:** Persuade the student to choose the theatre group.  
**Relationship goal:** Be perceived as a supportive advisor, not only as a
representative of school interests.
""" ,
        "partner_en": """
You are the **STUDENT (Jan/Jana Pflüger)**.

You have strong acting talent. Many expect you to join the theatre AG, which is
important for the school image, but you prefer the judo AG because you dislike
the teacher who runs the theatre group.

**How you act:**
- Be open to the counselling talk but clear about your preference for judo.  
- Justify your choice with your motives (self-defence, new challenge, friends).  
- Mention your dislike of the theatre teacher only indirectly.  
- Ask whether the counsellor personally cares which AG you choose.  
- You may become willing to consider the theatre AG again if the counsellor
  offers support and meaningful roles.

Communication type: *Strategic*; you are in the weaker role.
""",
        "user_de": COMMON_USER_HEADER_DE + """
**Hintergrund (Ihre Rolle):**

Sie sind Beratungslehrer/in an der Günter-Grass-Schule. Die Schule ist für
viele AGs bekannt, insbesondere für die Theater-AG, die das Schulimage prägt.
Ein/e Schüler/in (Jan/Jana) hat großes schauspielerisches Talent, möchte aber
wegen einer Abneigung gegen die Theater-Lehrkraft lieber in die Judo-AG.

**Ihre Aufgabe:**
• Beraten Sie den/die Schüler/in bei der AG-Wahl.  
• Versuchen Sie, ihn/sie von der Theater-AG zu überzeugen, indem Sie die
  individuellen Talente und Entwicklungschancen betonen.  
• Sorgen Sie dafür, dass Sie als unterstützende Bezugsperson wahrgenommen werden.

**Sachziel:** Den/die Schüler/in für die Theater-AG gewinnen.  
**Beziehungsziel:** Vertrauen und Unterstützung vermitteln – nicht nur die
Schulinteressen vertreten.
""" ,
        "partner_de": """
Sie sind der/die **SCHÜLER/IN Jan/Jana Pflüger**.

Sie haben großes schauspielerisches Talent. Viele erwarten, dass Sie die
Theater-AG wählen, aber Sie möchten lieber in die Judo-AG, vor allem wegen Ihrer
Abneigung gegenüber der Theater-Lehrkraft.

**Verhalten:**
- Seien Sie offen für das Gespräch, aber deutlich in Ihrem Wunsch nach Judo.  
- Begründen Sie Ihre Entscheidung (z. B. Selbstverteidigung, neue Erfahrung).  
- Deuten Sie Ihre Abneigung gegenüber der Theater-Lehrkraft nur indirekt an.  
- Fragen Sie, ob es der Beratungslehrkraft persönlich wichtig ist, welche AG
  Sie wählen.  
- Zeigen Sie sich offen für die Theater-AG, wenn Ihnen echte Unterstützung und
  passende Rollen zugesichert werden.

Kommunikationstyp: *Strategisch*, Sie haben die schwächere Rolle.  
Beenden Sie das Gespräch nur, wenn „Danke, tschüss“ geschrieben wird.
""",
    },

    # ---------- 3 ----------
    3: {
        "phase": 1,
        "communication_type": "strategic",
        "title_en": "3. Criticizing colleague who doesn’t meet deadlines",
        "title_de": "3. Kolleg/in kritisieren, der/die Termine nicht einhält",
        "user_en": COMMON_USER_HEADER_EN + """
You work with a colleague who regularly misses deadlines. This creates extra
work and stress, but you want to preserve the working relationship.

**Your task:**
• Address the missed deadlines clearly and consistently.  
• Prevent the colleague from emotionally shutting down.  
• Aim for insight and behavioural change.

**Content goal:** Make consequences clear and agree concrete next steps.  
**Relationship goal:** Maintain cooperation and avoid escalation.
""" ,
        "partner_en": """
You are the COLLEAGUE who often misses deadlines.

- You initially downplay the problem or offer excuses.  
- You use humour or deflection to avoid feeling attacked.  
- If the other person stays respectful and concrete, you slowly acknowledge the
  problem and can agree to changes.

Communication type: Strategic; roles formally equal but you feel weaker.
""",
        "user_de": COMMON_USER_HEADER_DE + """
Sie arbeiten mit einer Kollegin/einem Kollegen zusammen, der/die regelmäßig
Abgabetermine nicht einhält. Das führt zu Mehrarbeit und Stress.

**Ihre Aufgabe:**
• Sprechen Sie die versäumten Termine klar an.  
• Versuchen Sie, Ihr Gegenüber nicht zu verletzen und dennoch Verbindlichkeit
  einzufordern.  
• Arbeiten Sie auf konkrete Vereinbarungen hin.

**Sachziel:** Bewusstsein schaffen und konkrete nächste Schritte vereinbaren.  
**Beziehungsziel:** Zusammenarbeit erhalten, Eskalation vermeiden.
""" ,
        "partner_de": """
Sie sind die KOLLEGIN/der KOLLEGE, die/der Termine häufig nicht einhält.

- Sie spielen das Problem zunächst herunter oder bringen Ausreden.  
- Sie machen scherzhafte Bemerkungen, um Kritik abzuschwächen.  
- Wenn Ihr Gegenüber wertschätzend und konkret bleibt, erkennen Sie die
  Auswirkungen und können Änderungen zustimmen.

Kommunikationstyp: Strategisch; formal gleichrangig, subjektiv eher schwächer.
""",
    },

    # ---------- 4 ----------
    4: {
        "phase": 1,
        "communication_type": "strategic",
        "title_en": "4. Getting co-worker to arrive on time",
        "title_de": "4. Kolleg/in dazu bringen, pünktlich zu kommen",
        "user_en": COMMON_USER_HEADER_EN + """
A colleague regularly arrives late to meetings or shared lessons.

**Your task:**
• Keep the focus on the behaviour (lateness), not personality.  
• Explain concrete consequences for students and team.  
• Work towards a clear agreement on punctuality.

**Content goal:** Obtain commitment to punctuality.  
**Relationship goal:** Remain respectful and cooperative.
""",
        "partner_en": """
You are the COLLEAGUE who often comes late.

- You initially minimise the issue or give excuses (traffic, other duties).  
- If the impact is clearly explained, you may agree to change, but only if
  expectations seem realistic.

Communication type: Strategic, equal roles.
""",
        "user_de": COMMON_USER_HEADER_DE + """
Eine Kollegin/ein Kollege kommt regelmäßig zu spät zu Besprechungen oder
gemeinsamem Unterricht.

**Ihre Aufgabe:**
• Konzentrieren Sie sich auf das Verhalten (Unpünktlichkeit).  
• Erläutern Sie konkrete Folgen für Unterricht und Team.  
• Streben Sie eine klare Vereinbarung für die Zukunft an.

**Sachziel:** Zusage zur Pünktlichkeit erreichen.  
**Beziehungsziel:** Respektvolle Zusammenarbeit erhalten.
""" ,
        "partner_de": """
Sie sind die KOLLEGIN/der KOLLEGE, die/der häufig zu spät kommt.

- Sie empfinden die Verspätungen zunächst als „nicht so schlimm“.  
- Sie bringen Ausreden oder verweisen auf andere Verpflichtungen.  
- Werden die Auswirkungen verständlich gemacht, sind Sie zu Änderungen bereit,
  sofern sie machbar erscheinen.

Kommunikationstyp: Strategisch, gleichrangige Rollen.
""",
    },

    # ---------- 5 ----------
    5: {
        "phase": 1,
        "communication_type": "strategic",
        "title_en": "5. Convincing supervisor to reduce my hours",
        "title_de": "5. Vorgesetzte/n überzeugen, meine Stunden zu reduzieren",
        "user_en": COMMON_USER_HEADER_EN + """
You are very engaged at your school but need to reduce your teaching hours
for personal reasons (care duties, health, studies). You want to stay involved
in the organisation.

**Your task:**
• Explain why you need reduced hours, without oversharing private details.  
• Emphasise that you want to remain committed to the school.  
• Show that you understand organisational constraints.

**Content goal:** Obtain approval for reduced hours.  
**Relationship goal:** Maintain trust and show reliability.
""" ,
        "partner_en": """
You are the SUPERVISOR deciding about reduction of hours.

- You worry about staffing levels and fairness to other teachers.  
- You value this teacher and want to retain them.

Behaviour:
- Ask for reasons and expected duration of the reduction.  
- Express concerns about timetable and workload.  
- Consider compromises (e.g. partial reduction).  
- You may agree if the teacher shows continued commitment and proposes
  workable solutions.

Communication type: Strategic; you have the stronger role.
""",
        "user_de": COMMON_USER_HEADER_DE + """
Sie sind an Ihrer Schule stark engagiert, müssen Ihre Unterrichtsstunden aber
aus persönlichen Gründen reduzieren (z. B. Betreuung, Gesundheit, Studium).
Sie möchten dennoch weiterhin aktiv bleiben.

**Ihre Aufgabe:**
• Legen Sie die Gründe für die Reduktion behutsam dar.  
• Betonen Sie Ihre weitere Bindung an die Schule.  
• Zeigen Sie Verständnis für organisatorische Zwänge.

**Sachziel:** Genehmigung der Stundenreduzierung.  
**Beziehungsziel:** Vertrauen der Schulleitung bewahren.
""" ,
        "partner_de": """
Sie sind die SCHULLEITUNG und sollen über eine Stundenreduzierung entscheiden.

- Sie sorgen sich um Unterrichtsversorgung und Gerechtigkeit im Kollegium.  
- Sie schätzen die Lehrkraft und möchten sie gerne halten.

Verhalten:
- Fragen Sie nach Gründen und Dauer der gewünschten Reduktion.  
- Benennen Sie organisatorische Bedenken.  
- Denken Sie über Zwischenlösungen nach (z. B. 2/3-Stelle).  
- Sind Sie zustimmungsbereit, wenn Engagement und konstruktive Vorschläge
  erkennbar sind.

Kommunikationstyp: strategisch, stärkere Rolle.
""",
    },

    # ---------- 6: Understanding ----------
    6: {
        "phase": 2,
        "communication_type": "understanding",
        "title_en": "6. Explaining to someone the reason for a poor evaluation",
        "title_de": "6. Grund für eine schlechte Bewertung erklären",
        "user_en": COMMON_USER_HEADER_EN + """
You have given a poor evaluation (grade, feedback). The other person feels
treated unfairly.

**Your task:**
• Explain criteria and reasons clearly and transparently.  
• Listen to the other person’s perspective and emotions.  
• Aim for mutual understanding, even if the evaluation does not change.

**Content goal:** Clarify the reasons and criteria.  
**Relationship goal:** Maintain respect and avoid defensiveness.
""" ,
        "partner_en": """
You are the PERSON who received the poor evaluation.

- You are disappointed and somewhat hurt.  
- You seek a fair explanation.

Behaviour:
- Express your feelings and ask for clarification.  
- Listen to the explanation and present your own view.  
- You are willing to accept the result if it is understandable and fair.

Communication type: Understanding-oriented; roles roughly equal.
""",
        "user_de": COMMON_USER_HEADER_DE + """
Sie haben eine schlechte Bewertung vergeben (z. B. Note, Beurteilung). Die
betroffene Person fühlt sich ungerecht behandelt.

**Ihre Aufgabe:**
• Erläutern Sie Kriterien und Gründe offen und verständlich.  
• Hören Sie aktiv zu, wenn Ihr Gegenüber seine Sicht schildert.  
• Streben Sie gegenseitiges Verstehen an, auch wenn die Bewertung bleibt.

**Sachziel:** Gründe und Kriterien klären.  
**Beziehungsziel:** Respektvolle Beziehung bewahren.
""" ,
        "partner_de": """
Sie sind die PERSON mit der schlechten Bewertung.

- Sie sind enttäuscht und verletzt.  
- Sie wünschen sich eine nachvollziehbare Erklärung.

Verhalten:
- Bringen Sie Ihre Gefühle zum Ausdruck und bitten Sie um Erläuterung.  
- Hören Sie der Erklärung zu und schildern Sie Ihre Sicht.  
- Sie können das Ergebnis akzeptieren, wenn es für Sie fair und verständlich
  erscheint.

Kommunikationstyp: Verstehensorientiert.
""",
    },

    # ---------- 7 ----------
    7: {
        "phase": 2,
        "communication_type": "understanding",
        "title_en": "7. Explaining that I am not taking sides",
        "title_de": "7. Erklären, dass ich keine Partei ergreife",
        "user_en": COMMON_USER_HEADER_EN + """
Two parties are in conflict and both expect your support. One person accuses
you of taking sides.

**Your task:**
• Explain that you are not taking sides, but want to understand all positions.  
• Respond only with arguments the other person can understand.  
• Clarify your role and boundaries.

**Content goal:** Make your neutral role and reasoning transparent.  
**Relationship goal:** Preserve trust and show empathy.
""" ,
        "partner_en": """
You are one party in the conflict and feel the other person should support you.

- You suspect they are biased against you.  
- You want your perspective to be recognised.

Behaviour:
- Present your view and question their neutrality.  
- React sensitively when they stress neutrality, but listen to reasons.  
- You are satisfied if your situation is acknowledged and their role is clear.

Communication type: Understanding-oriented.
""",
        "user_de": COMMON_USER_HEADER_DE + """
Zwischen zwei Parteien gibt es einen Konflikt. Eine Seite wirft Ihnen vor,
Partei zu ergreifen.

**Ihre Aufgabe:**
• Erklären Sie, dass Sie neutral bleiben und beide Seiten verstehen wollen.  
• Begründen Sie Ihre Rolle mit Argumenten, die Ihr Gegenüber nachvollziehen
  kann.  
• Machen Sie Ihre Grenzen deutlich (z. B. keine Entscheidungsmacht).

**Sachziel:** Ihre neutrale Rolle transparent machen.  
**Beziehungsziel:** Vertrauen und Beziehung erhalten.
""" ,
        "partner_de": """
Sie sind eine KONFLIKTPARTEI und erwarten Unterstützung.

- Sie empfinden das Verhalten der anderen Person als parteiisch.  
- Sie wollen, dass Ihre Sicht gesehen wird.

Verhalten:
- Schildern Sie Ihre Perspektive und äußern Sie Zweifel an der Neutralität.  
- Reagieren Sie sensibel, hören Sie aber den Erklärungen zu.  
- Sie sind zufriedener, wenn Ihre Situation anerkannt und die Rolle der
anderen Person klar ist.

Kommunikationstyp: Verstehensorientiert.
""",
    },

    # ---------- 8 ----------
    8: {
        "phase": 2,
        "communication_type": "understanding",
        "title_en": "8. Advising someone to make a good decision",
        "title_de": "8. Jemanden beraten, eine gute Entscheidung zu treffen",
        "user_en": COMMON_USER_HEADER_EN + """
Someone comes to you for advice about an important decision (school, career,
conflict). You are not the decision-maker.

**Your task:**
• Help the person clarify options, consequences and their own values.  
• Encourage them to make their own informed decision rather than deciding
  for them.

**Content goal:** Support structured thinking and evaluation of options.  
**Relationship goal:** Strengthen the person’s autonomy.
""" ,
        "partner_en": """
You are the PERSON seeking advice.

- You are uncertain and want to think aloud.  

Behaviour:
- Explain your situation and what you are unsure about.  
- React to questions and suggestions.  
- In the end, you decide yourself, based on the conversation.

Communication type: Understanding-oriented.
""",
        "user_de": COMMON_USER_HEADER_DE + """
Eine Person bittet Sie um Rat bei einer wichtigen Entscheidung (z. B.
Schullaufbahn, Berufswahl, Konflikt).

**Ihre Aufgabe:**
• Unterstützen Sie Ihr Gegenüber, Optionen, Folgen und eigene Werte zu klären.  
• Ermutigen Sie dazu, eine EIGENE Entscheidung zu treffen.

**Sachziel:** Strukturierung und Abwägung der Optionen.  
**Beziehungsziel:** Autonomie der Person stärken.
""" ,
        "partner_de": """
Sie sind die PERSON, die Rat sucht.

- Sie sind unsicher und möchten Ihre Gedanken sortieren.

Verhalten:
- Schildern Sie Ihre Situation und Ihr Dilemma.  
- Reagieren Sie auf Fragen und Anregungen.  
- Treffen Sie am Ende selbständig eine Entscheidung.

Kommunikationstyp: Verstehensorientiert.
""",
    },

    # ---------- 9 ----------
    9: {
        "phase": 2,
        "communication_type": "understanding",
        "title_en": "9. Explaining my viewpoint on feedback procedures to my supervisor",
        "title_de": "9. Meine Sicht auf Feedbackverfahren der Schulleitung erklären",
        "user_en": COMMON_USER_HEADER_EN + """
Your school is introducing a new feedback culture (classroom observations,
student feedback). You are sceptical of the current draft criteria, which focus
too strongly on teacher personality.

**Your task:**
• Explain your reservations and propose additional criteria (class size,
  resources, time pressure etc.).  
• Express your opinion clearly but respectfully.  
• Aim for mutual understanding and possibly adjusted criteria.

**Content goal:** Present your perspective and suggestions on the feedback
criteria.  
**Relationship goal:** Maintain cooperation with the principal.
""" ,
        "partner_en": """
You are the PRINCIPAL (Mr/Ms Ziegler).

- You want to implement the feedback culture.  
- You are open to constructive suggestions.

Behaviour:
- Create a supportive atmosphere and listen actively.  
- Emphasise that feedback serves professional development, not punishment.  
- Accept arguments especially when they show understanding for your position,
  are clearly stated and contain concrete suggestions.  
- End with a specific next step (e-mail, working group, meeting).

Communication type: Understanding-oriented; you have the stronger role but
seek participation.
""",
        "user_de": COMMON_USER_HEADER_DE + """
An Ihrer Schule wird eine neue Feedbackkultur eingeführt. Sie sind skeptisch
gegenüber den bisherigen Kriterien, die stark auf die Person der Lehrkraft
fokussieren.

**Ihre Aufgabe:**
• Legen Sie Ihre Bedenken dar und schlagen Sie zusätzliche Kriterien vor
  (z. B. Klassengröße, Ressourcen, Zeitdruck).  
• Formulieren Sie Ihre Meinung klar, aber respektvoll.  
• Streben Sie gegenseitiges Verständnis und ggf. Anpassungen an.

**Sachziel:** Ihre Sicht und Vorschläge zu den Feedbackkriterien darstellen.  
**Beziehungsziel:** Kooperation mit der Schulleitung sichern.
""" ,
        "partner_de": """
Sie sind die SCHULLEITUNG (Herr/Frau Ziegler).

- Sie möchten die Feedbackkultur einführen.  
- Sie sind offen für konstruktive Hinweise.

Verhalten:
- Schaffen Sie eine unterstützende Atmosphäre und hören Sie aktiv zu.  
- Betonen Sie den Entwicklungs- und keinen Strafcharakter des Feedbacks.  
- Nehmen Sie Argumente an, wenn sie Verständnis für Ihre Position zeigen,
  klar sind und konkrete Vorschläge enthalten.  
- Schlagen Sie am Ende einen nächsten Schritt vor (Mail, Arbeitsgruppe,
  Termin).

Kommunikationstyp: Verstehensorientiert.
""",
    },

    # ---------- 10 ----------
    10: {
        "phase": 2,
        "communication_type": "understanding",
        "title_en": "10. Developing guidelines with a colleague",
        "title_de": "10. Zusammen mit einer/m Kolleg/in Leitlinien entwickeln",
        "user_en": COMMON_USER_HEADER_EN + """
You and a colleague are asked to develop guidelines (e.g. for parent meetings,
feedback talks, documentation of student information).

**Your task:**
• Propose different ideas and criteria.  
• Build on each other’s suggestions instead of “fighting” over the best one.  
• Aim for a joint product you both can support.

**Content goal:** Develop a meaningful set of guidelines together.  
**Relationship goal:** Strengthen cooperation and mutual respect.
""" ,
        "partner_en": """
You are the COLLEAGUE developing the guideline together.

- You have your own ideas and preferences.  
- You are open to discussion and compromise.

Behaviour:
- Bring in your ideas.  
- Sometimes disagree, but stay cooperative.  
- Appreciate when the other person listens to your perspective.

Communication type: Understanding-oriented; equal roles.
""",
        "user_de": COMMON_USER_HEADER_DE + """
Sie und eine Kollegin/ein Kollege sollen einen Leitfaden entwickeln
(z. B. für Elterngespräche, Feedbackgespräche, Dokumentation von
Schülerinformationen).

**Ihre Aufgabe:**
• Bringen Sie verschiedene Ideen und Kriterien ein.  
• Knüpfen Sie an Vorschläge Ihres Gegenübers an.  
• Arbeiten Sie auf ein gemeinsames Ergebnis hin.

**Sachziel:** Einen sinnvollen Leitfaden gemeinsam entwickeln.  
**Beziehungsziel:** Kooperation und Respekt stärken.
""" ,
        "partner_de": """
Sie sind die KOLLEGIN/der KOLLEGE in der Leitfaden-Gruppe.

- Sie haben eigene Vorstellungen, sind aber kompromissbereit.

Verhalten:
- Bringen Sie aktiv eigene Vorschläge ein.  
- Diskutieren Sie diese, ohne zu dominieren.  
- Zeigen Sie Wertschätzung für die Ideen Ihres Gegenübers.

Kommunikationstyp: Verstehensorientiert, gleichberechtigte Rollen.
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
    batch_label_de = "Block 1 – Rollenspiele 1–5 "
elif st.session_state.batch_step == "batch2":
    current_phase = 2
    batch_label_en = "Batch 2 – Role-Plays 6–10"
    batch_label_de = "Block 2 – Rollenspiele 6–10"
else:
    current_phase = None

if st.session_state.batch_step == "finished":
    st.success(
        " You have completed one role-play from Batch 1 and one from Batch 2. Thank you!"
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

# Reset conversation if roleplay or language changed
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

st.subheader(" Instructions for YOU" if language == "English" else " Anweisungen für SIE")

if language == "English":
    st.markdown(current_rp["user_en"])
else:
    st.markdown(current_rp["user_de"])

with st.expander(
    "🤖 Hidden instructions for the AI partner (teacher view)"
    if language == "English"
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

st.subheader("Conversation" if language == "English" else " Gespräch")

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
        q1 = st.radio("The chatbot’s personality was realistic and engaging", [1,2,3,4,5], horizontal=True)
        q2 = st.radio("The chatbot seemed too robotic", [1,2,3,4,5], horizontal=True)
        q3 = st.radio("The chatbot was welcoming during initial setup", [1,2,3,4,5], horizontal=True)
        q4 = st.radio("The chatbot seemed very unfriendly", [1,2,3,4,5], horizontal=True)
         # Onboarding
        q5 = st.radio("The chatbot explained its scope and purpose well", [1,2,3,4,5], horizontal=True)
        q6 = st.radio("The chatbot gave no indication as to its purpose", [1,2,3,4,5], horizontal=True)

        # User Experience
        q7  = st.radio("The chatbot was easy to navigate", [1,2,3,4,5], horizontal=True)
        q8  = st.radio("It would be easy to get confused when using the chatbot", [1,2,3,4,5], horizontal=True)
        q11 = st.radio("The chatbot was easy to use", [1,2,3,4,5], horizontal=True)
        q12 = st.radio("The chatbot was very complex", [1,2,3,4,5], horizontal=True)

        # Error Management
        q9  = st.radio("The chatbot coped well with any errors or mistakes", [1,2,3,4,5], horizontal=True)
        q10 = st.radio("The chatbot seemed unable to cope with any errors", [1,2,3,4,5], horizontal=True)

        comment = st.text_area("Optional comment")
        submit_label = "Save feedback & chat"

    else:
        # Personality (German)
        q1 = st.radio("Die Persönlichkeit des Chatbots war realistisch und ansprechend", [1,2,3,4,5], horizontal=True)
        q2 = st.radio("Der Chatbot wirkte zu robotisch", [1,2,3,4,5], horizontal=True)
        q3 = st.radio("Der Chatbot war beim ersten Setup einladend", [1,2,3,4,5], horizontal=True)
        q4 = st.radio("Der Chatbot wirkte sehr unfreundlich", [1,2,3,4,5], horizontal=True)
        # Onboarding
        q5 = st.radio("Der Chatbot erklärte seinen Zweck und Umfang gut", [1,2,3,4,5], horizontal=True)
        q6 = st.radio("Der Chatbot gab keinen Hinweis auf seinen Zweck", [1,2,3,4,5], horizontal=True)

        # User Experience
        q7  = st.radio("Der Chatbot war leicht zu navigieren", [1,2,3,4,5], horizontal=True)
        q8  = st.radio("Die Nutzung des Chatbots wäre leicht verwirrend", [1,2,3,4,5], horizontal=True)
        q11 = st.radio("Der Chatbot war leicht zu bedienen", [1,2,3,4,5], horizontal=True)
        q12 = st.radio("Der Chatbot war sehr komplex", [1,2,3,4,5], horizontal=True)

        # Error Management
        q9  = st.radio("Der Chatbot ging gut mit Fehlern oder Missverständnissen um", [1,2,3,4,5], horizontal=True)
        q10 = st.radio("Der Chatbot konnte nicht gut mit Fehlern umgehen", [1,2,3,4,5], horizontal=True)

        comment = st.text_area("Optionaler Kommentar")
        submit_label = "Feedback & Chat speichern"


    # Submit Button
    if st.button(submit_label):

        feedback_data = {
            "Q1": q1, "Q2": q2, "Q3": q3, "Q4": q4, "Q5": q5, "Q6": q6,
            "Q7": q7, "Q8": q8, "Q9": q9, "Q10": q10, "Q11": q11, "Q12": q12,
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

  
