import streamlit as st
import openai
import json
from datetime import datetime
st.rerun()
# Optional: Google Sheets logging
try:
    import gspread
    from google.oauth2.service_account import Credentials
    GSHEETS_AVAILABLE = True
except ImportError:
    GSHEETS_AVAILABLE = False

# ---------------------------------------------------------
#  CONFIG: OpenAI + Google Sheets
# ---------------------------------------------------------

def setup_openai():
    """Set OpenAI API key from Streamlit secrets or sidebar input."""
    api_key = st.secrets.get("OPENAI_API_KEY", "")
    if not api_key:
        api_key = st.sidebar.text_input(
            "🔑 OpenAI API key (not visible to students in cloud deployment)",
            type="password",
            help="Paste your key only when testing locally. "
                 "On Streamlit Cloud use st.secrets."
        )
    if api_key:
        openai.api_key = api_key
        return True
    st.sidebar.warning("Please set your OpenAI API key.")
    return False


def get_gsheets_client():
    """Create a gspread client from service-account info in st.secrets."""
    if not GSHEETS_AVAILABLE:
        st.sidebar.warning("gspread not installed – chats will not be saved to Google Sheets.")
        return None

    sa_info = st.secrets.get("gcp_service_account", None)
    sheet_id = st.secrets.get("GSPREAD_SHEET_ID", "")

    if not sa_info or not sheet_id:
        st.sidebar.warning(
            "Google Sheets not configured. "
            "Add 'gcp_service_account' JSON and 'GSPREAD_SHEET_ID' to st.secrets."
        )
        return None

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(sa_info, scopes=scopes)
    client = gspread.authorize(creds)
    return client


def append_chat_and_feedback_to_sheets(meta, chat_messages, feedback):
    """
    Append one row to 'chats' sheet and one row to 'feedback' sheet.
    meta: dict with metadata
    chat_messages: list of {role, content}
    feedback: dict with survey results
    """
    client = get_gsheets_client()
    if not client:
        return

    sheet_id = st.secrets["GSPREAD_SHEET_ID"]
    try:
        sh = client.open_by_key(sheet_id)
    except Exception as e:
        st.error(f"Could not open Google Sheet: {e}")
        return

    # ---- Chats sheet ----
    try:
        chats_ws = sh.worksheet("chats")
    except Exception:
        # Create worksheet if it doesn't exist
        chats_ws = sh.add_worksheet(title="chats", rows="1000", cols="20")

    timestamp = datetime.utcnow().isoformat()
    chat_json = json.dumps(chat_messages, ensure_ascii=False)

    chat_row = [
        timestamp,
        meta.get("student_id", ""),
        meta.get("language", ""),
        meta.get("phase", ""),
        meta.get("roleplay_id", ""),
        meta.get("roleplay_title_en", ""),
        meta.get("roleplay_title_de", ""),
        meta.get("communication_type", ""),
        chat_json,
    ]

    try:
        chats_ws.append_row(chat_row)
    except Exception as e:
        st.error(f"Could not append chat to Google Sheet: {e}")

    # ---- Feedback sheet ----
    try:
        fb_ws = sh.worksheet("feedback")
    except Exception:
        fb_ws = sh.add_worksheet(title="feedback", rows="1000", cols="20")

    fb_row = [
        timestamp,
        meta.get("student_id", ""),
        meta.get("language", ""),
        meta.get("phase", ""),
        meta.get("roleplay_id", ""),
        feedback.get("clarity", ""),
        feedback.get("authenticity", ""),
        feedback.get("learning", ""),
        feedback.get("difficulty", ""),
        feedback.get("comment", ""),
    ]

    try:
        fb_ws.append_row(fb_row)
    except Exception as e:
        st.error(f"Could not append feedback to Google Sheet: {e}")


# ---------------------------------------------------------
#  ROLEPLAY DEFINITIONS (titles + instructions)
#  1–5 = strategic, 6–10 = understanding-oriented
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
COMMUNICATION FRAMEWORK (Strategic communication)

• Conversation intention: Relational goal in the foreground  
• Content goal: You may partially breach quantity, quality, relevance and clarity
  if this helps your strategic aim.  
• Relational goal: You often use FUTURE-ORIENTED SELF-DISCLOSURE
  (e.g. talking about what could happen, what you plan, what you hope).

Context and social role:
• Clear power difference (stronger / weaker role).  
• You argue in a goal-oriented way to achieve your desired outcome.
"""

FRAMEWORK_STRATEGIC_DE = """
KOMMUNIKATIONSRAHMEN (Strategische Kommunikation)

• Gesprächsabsicht: Beziehungsziel steht im Vordergrund  
• Sachziel: Sie können Menge, Qualität, Relevanz und Klarheit der Informationen
  gezielt verletzen, wenn es Ihrem strategischen Ziel hilft.  
• Beziehungsziel: Sie nutzen häufig ZUKUNFTSORIENTIERTE SELBSTOFFENBARUNG
  (z. B. Sie sprechen über mögliche Entwicklungen, Pläne, Hoffnungen).

Kontext und soziale Rolle:
• Deutlicher Machtunterschied (stärkere / schwächere Rolle).  
• Sie argumentieren zielorientiert, um Ihr gewünschtes Ergebnis zu erreichen.
"""

FRAMEWORK_UNDERSTANDING_EN = """
COMMUNICATION FRAMEWORK (Understanding-oriented communication)

• Conversation intention: Content goal in the foreground  
• Content goal: You ADHERE to quantity, quality, relevance and clarity.
• Relational goal: You use AUTHENTIC SELF-DISCLOSURE
  (you talk honestly about your real thoughts and feelings).

Context and social role:
• Often more equal power or cooperative setting.  
• The aim is mutual understanding and a sustainable relationship.
"""

FRAMEWORK_UNDERSTANDING_DE = """
KOMMUNIKATIONSRAHMEN (Verstehensorientierte Kommunikation)

• Gesprächsabsicht: Sachziel steht im Vordergrund  
• Sachziel: Sie HALTEN Menge, Qualität, Relevanz und Klarheit der Informationen ein.  
• Beziehungsziel: Sie nutzen AUTHENTISCHE SELBSTOFFENBARUNG
  (Sie sprechen ehrlich über Ihre tatsächlichen Gedanken und Gefühle).

Kontext und soziale Rolle:
• Häufig eher gleichberechtigte oder kooperative Situation.  
• Ziel ist gegenseitiges Verstehen und eine tragfähige Beziehung.
"""

# NOTE: For brevity, the background texts are summarised.
# You can paste your full texts here if you wish.

ROLEPLAYS = {
    1: {
        "phase": 1,
        "communication_type": "strategic",
        "title_en": "1. Convincing supervisor to allow attending a continuing education course",
        "title_de": "1. Vorgesetzte/n überzeugen, eine Fortbildung zu genehmigen",
        "user_en": COMMON_USER_HEADER_EN
        + """
Background information:
You are a teacher at Friedrich-Ebert School. You want to attend a professional
development course on “self-directed learning”. This would support your
professional growth and future career, and you also see it as important for the
school’s development. Your principal is sceptical, sees little direct benefit for
the school and worries about costs and lesson cancellations.

Your task:
• Explain why this training is important for you AND for the school.
• Link the course clearly to school development and student learning.
• Address the principal’s concerns (budget, substitution, workload).

Factual (content) goal:
• Convince your supervisor to approve your participation.

Relational goal:
• Maintain a constructive and professional relationship and show commitment
  to the school.
"""
        + FRAMEWORK_STRATEGIC_EN,
        "partner_en": """
You are the PRINCIPAL (Mr/Ms Horn) at Friedrich-Ebert School.

A teacher asks you to approve a professional development course on
“self-directed learning”. You are sceptical and worry about costs,
organisation and whether the topic really fits the school’s priorities.

Act as follows:
• Start reserved and questioning, ask for concrete benefits for the school.
• Mention limited funds and organisational problems (substitution etc.).
• Stay sceptical as long as the teacher argues mainly with personal advantages.
• Use a slightly ironic remark about self-directed learning
  (“Is this just shifting responsibility onto students?”).
• Only if the teacher clearly links the training to school development and
  shows commitment to this school are you ready to agree.

Factual goal:
• You want a well-founded justification that focuses on the SCHOOL,
  not only the teacher’s career.

Relational goal:
• You want to keep this teacher and maintain a cooperative relationship.

Communication type: Strategic.
You have the STRONGER social role.
""",
        "user_de": COMMON_USER_HEADER_DE
        + """
Hintergrundinformation:
Sie sind Lehrkraft an der Friedrich-Ebert-Schule. Sie möchten an einer
Fortbildung zum Thema „Selbstgesteuertes Lernen“ teilnehmen. Die Fortbildung
ist wichtig für Ihre berufliche Entwicklung und könnte auch die
Schulentwicklung unterstützen. Ihre Schulleitung ist skeptisch, sieht wenig
direkten Nutzen für die Schule und sorgt sich um Kosten und Stundenausfall.

Ihre Aufgabe:
• Erklären Sie, warum die Fortbildung für Sie UND für die Schule wichtig ist.
• Stellen Sie einen klaren Bezug zur Schulentwicklung und zum Lernen der
  Schüler/innen her.
• Gehen Sie auf die Bedenken der Schulleitung (Finanzen, Vertretung,
  Arbeitsbelastung) ein.

Sachziel:
• Überzeugen Sie Ihre/n Vorgesetzte/n, die Teilnahme zu genehmigen.

Beziehungsziel:
• Zeigen Sie Ihre Verbundenheit mit der Schule und erhalten Sie eine
  konstruktive Zusammenarbeit.
"""
        + FRAMEWORK_STRATEGIC_DE,
        "partner_de": """
Sie sind die SCHULLEITUNG (Herr/Frau Horn) der Friedrich-Ebert-Schule.

Eine Lehrkraft bittet Sie, eine Fortbildung zum „Selbstgesteuerten Lernen“
zu genehmigen. Sie sind skeptisch und machen sich Sorgen um Kosten, Organisation
und die Frage, ob das Thema wirklich zur aktuellen Schulentwicklung passt.

Verhalten Sie sich wie folgt:
• Reagieren Sie zunächst zurückhaltend und fragend, verlangen Sie konkrete
  Vorteile für die Schule.
• Weisen Sie auf begrenzte Mittel und organisatorische Probleme hin
  (Vertretungsunterricht etc.).
• Bleiben Sie skeptisch, solange die Lehrkraft vor allem persönliche Vorteile
  betont.
• Machen Sie eine leicht ironische Bemerkung über selbstgesteuertes Lernen
  („Wollen Lehrkräfte damit nur Arbeit auf die Schüler abwälzen?“).
• Sind Sie bereit zuzustimmen, wenn die Lehrkraft klar die Relevanz für
  die Schulentwicklung aufzeigt und ihre langfristige Bindung an die Schule
  betont.

Sachziel:
• Sie erwarten eine gut begründete Argumentation, bei der die Schule im
  Mittelpunkt steht.

Beziehungsziel:
• Sie wollen weiterhin mit der Lehrkraft zusammenarbeiten und sie an der
  Schule halten.

Kommunikationstyp: Strategische Kommunikation.
Sie haben die STÄRKERE soziale Rolle.
""",
    },
    2: {
        "phase": 1,
        "communication_type": "strategic",
        "title_en": "2. Convincing co-worker / student to work with a certain group",
        "title_de": "2. Kolleg/in oder Schüler/in überzeugen, mit einer bestimmten Gruppe zu arbeiten",
        "user_en": COMMON_USER_HEADER_EN
        + """
Background information:
You are a teacher and school counsellor at Günter-Grass School. The school is
known for many extracurricular groups (AGs). The theatre group is very
important for the school’s public image, and your performance as counsellor is
also evaluated on how well the school is represented.

A student (Jan/Jana) has great acting talent, but wants to join the judo AG,
mainly because they dislike the teacher who leads the theatre group.

Your task:
• Advise the student on their AG choice.
• Try to persuade them to choose the theatre group, focusing on their talent
  and development, not only on the school’s interests.
• At the same time, maintain a caring, supportive relationship.

Content goal:
• Persuade the student to decide for the theatre AG.

Relationship goal:
• Be perceived as a supportive advisor, not as someone who only cares about
  the school’s image.
"""
        + FRAMEWORK_STRATEGIC_EN,
        "partner_en": """
You are the STUDENT (Jan/Jana Pflüger).

You have acting talent and others expect you to join the theatre AG, which is
important for the school’s image. However, you personally dislike the teacher
who runs the theatre group and therefore want to join the judo AG instead.

Act as follows:
• Be open to the counselling conversation but clear about your preferences.
• Justify your wish to join the judo AG with your motives (e.g. self-defence,
  trying something new).
• Only indirectly mention your dislike of the theatre teacher.
• Ask whether the counsellor personally cares which AG you choose.
• You might be willing to return to the theatre AG if the counsellor promises
  to support you in getting meaningful / leading roles.

Communication type: Strategic, you are in the WEAKER role.
""",
        "user_de": COMMON_USER_HEADER_DE
        + """
Hintergrundinformation:
Sie sind Lehrkraft und Beratungslehrer/in an der Günter-Grass-Schule.
Die Schule ist für viele AG-Angebote bekannt, besonders für die Theater-AG,
die wesentlich zum positiven Image beiträgt. Ihre Arbeit als Beratungslehrer/in
wird u. a. daran gemessen, wie gut die Schule nach außen dargestellt wird.

Ein/e Schüler/in (Jan/Jana) hat großes schauspielerisches Talent, möchte aber
lieber an der Judo-AG teilnehmen, vor allem wegen einer starken Abneigung gegen
die Lehrkraft der Theater-AG.

Ihre Aufgabe:
• Beraten Sie den/die Schüler/in bei der AG-Wahl.
• Versuchen Sie, ihn/sie von der Theater-AG zu überzeugen, indem Sie die
  individuellen Talente und Entwicklungschancen betonen.
• Achten Sie gleichzeitig darauf, als unterstützende und vertrauenswürdige
  Bezugsperson wahrgenommen zu werden.

Sachziel:
• Überzeugen Sie den/die Schüler/in von der Teilnahme an der Theater-AG.

Beziehungsziel:
• Der/die Schüler/in soll Sie als zugewandte/n Berater/in erleben – nicht nur
  als Vertreter/in der Schulinteressen.
"""
        + FRAMEWORK_STRATEGIC_DE,
        "partner_de": """
Sie sind der/die SCHÜLER/IN Jan/Jana Pflüger.

Sie haben großes schauspielerisches Talent, viele erwarten, dass Sie die
Theater-AG wählen. Sie selbst möchten jedoch lieber in die Judo-AG gehen,
hauptsächlich weil Sie die Lehrkraft der Theater-AG nicht mögen.

Verhalten Sie sich wie folgt:
• Seien Sie offen für das Beratungsgespräch, aber klar in Ihren Wünschen.
• Begründen Sie Ihre Entscheidung für die Judo-AG (z. B. Selbstverteidigung,
  etwas Neues ausprobieren).
• Deuten Sie Ihre Abneigung gegenüber der Theater-Lehrkraft nur indirekt an.
• Fragen Sie, ob es der Beratungslehrkraft persönlich wichtig ist, welche AG
  Sie wählen.
• Zeigen Sie sich offen für die Theater-AG, wenn Ihnen Unterstützung und
  attraktive Rollen zugesichert werden.

Kommunikationstyp: Strategisch, Sie haben die SCHWÄCHERE Rolle.
""",
    },
    3: {
        "phase": 1,
        "communication_type": "strategic",
        "title_en": "3. Criticizing a colleague who doesn’t meet deadlines",
        "title_de": "3. Kolleg/in kritisieren, der/die Termine nicht einhält",
        "user_en": COMMON_USER_HEADER_EN
        + """
Background information:
You work together with a colleague who regularly misses deadlines. This
creates extra work and stress for you and the team, but you want to preserve
the relationship.

Your task:
• Address the missed deadlines clearly and consistently.
• Prevent your colleague from withdrawing emotionally or shutting down.
• Use strategic communication: you may choose what information to share and
  how directly, but you still want a constructive solution.

Content goal:
• Make your colleague aware of the consequences and agree concrete next steps.

Relationship goal:
• Keep the professional relationship intact and avoid escalation.
"""
        + FRAMEWORK_STRATEGIC_EN,
        "partner_en": """
You are the COLLEAGUE who often misses deadlines.

You feel under pressure and partly criticised, but you also fear conflict.
Sometimes you justify yourself, sometimes you withdraw emotionally.

Act as follows:
• React sensitively to criticism, you may initially defend yourself.
• If the other person remains respectful and concrete, you slowly open up.
• You are willing to discuss solutions if you feel understood.

Communication type: Strategic; roles roughly equal, but you feel weaker.
""",
        "user_de": COMMON_USER_HEADER_DE
        + """
Hintergrundinformation:
Sie arbeiten mit einer Kollegin/einem Kollegen zusammen, der/die regelmäßig
Abgabetermine nicht einhält. Das führt zu Mehrarbeit und Stress, Sie möchten
die Zusammenarbeit dennoch erhalten.

Ihre Aufgabe:
• Sprechen Sie die versäumten Termine klar und konsequent an.
• Versuchen Sie zu verhindern, dass Ihr Gegenüber sich emotional verschließt.
• Nutzen Sie strategische Kommunikation: Sie wählen bewusst, wie direkt und
  ausführlich Sie Kritik äußern, bleiben aber lösungsorientiert.

Sachziel:
• Machen Sie Ihrem Gegenüber die Folgen deutlich und vereinbaren Sie konkrete
  Schritte für die Zukunft.

Beziehungsziel:
• Die professionelle Beziehung soll bestehen bleiben, ohne Eskalation.
"""
        + FRAMEWORK_STRATEGIC_DE,
        "partner_de": """
Sie sind die KOLLEGIN/der KOLLEGE, die/der Termine häufig nicht einhält.

Sie stehen unter Druck und fühlen sich schnell kritisiert. Konflikte vermeiden
Sie lieber, teilweise ziehen Sie sich innerlich zurück.

Verhalten Sie sich wie folgt:
• Reagieren Sie zunächst defensiv oder ausweichend.
• Öffnen Sie sich, wenn Ihr Gegenüber respektvoll und konkret bleibt.
• Zeigen Sie Bereitschaft zu Veränderungen, sobald Sie sich verstanden fühlen.

Kommunikationstyp: Strategisch; die Rollen sind formal gleich, Sie erleben
sich aber eher schwächer.
""",
    },
    4: {
        "phase": 1,
        "communication_type": "strategic",
        "title_en": "4. Getting a co-worker to arrive on time",
        "title_de": "4. Kolleg/in dazu bringen, pünktlich zu kommen",
        "user_en": COMMON_USER_HEADER_EN
        + """
Background information:
A colleague regularly arrives late to team meetings or shared lessons. This
disturbs the workflow and signals disrespect to others.

Your task:
• Keep the focus consistently on the colleague’s behaviour (lateness),
  not on their personality.
• Explain the concrete impact on students / team.
• Aim for a clear agreement on future punctuality.

Content goal:
• Get your colleague to commit to being on time.

Relationship goal:
• Stay respectful and avoid moralising, so that cooperation can continue.
"""
        + FRAMEWORK_STRATEGIC_EN,
        "partner_en": """
You are the COLLEAGUE who often comes late.

You tend to underestimate the impact of your lateness and sometimes see it as
“not such a big deal”.

Act as follows:
• At first, play down the problem a bit or give excuses.
• Gradually recognise the impact if the other person explains it clearly.
• You may agree to change your behaviour if expectations are realistic.

Communication type: Strategic; roles are equal.
""",
        "user_de": COMMON_USER_HEADER_DE
        + """
Hintergrundinformation:
Eine Kollegin/ein Kollege kommt regelmäßig zu spät zu Teamsitzungen oder
gemeinsamem Unterricht. Dadurch wird der Ablauf gestört und es wirkt
respektlos den anderen gegenüber.

Ihre Aufgabe:
• Richten Sie den Blick konsequent auf das Verhalten (Unpünktlichkeit),
  nicht auf die Persönlichkeit.
• Erklären Sie die konkreten Auswirkungen auf Schüler/innen und Team.
• Arbeiten Sie auf eine klare Vereinbarung für die Zukunft hin.

Sachziel:
• Erreichen Sie, dass Ihr Gegenüber sich zu Pünktlichkeit verpflichtet.

Beziehungsziel:
• Bleiben Sie respektvoll und vermeiden Sie Moralisieren, damit die
  Zusammenarbeit weiterhin möglich ist.
"""
        + FRAMEWORK_STRATEGIC_DE,
        "partner_de": """
Sie sind die KOLLEGIN/der KOLLEGE, die/der häufig zu spät kommt.

Sie unterschätzen zunächst die Folgen Ihrer Unpünktlichkeit und empfinden sie
nicht als besonders problematisch.

Verhalten Sie sich wie folgt:
• Spielen Sie das Problem anfangs herunter oder bringen Sie Ausreden.
• Erkennen Sie nach und nach die Auswirkungen, wenn Ihr Gegenüber diese
  klar erläutert.
• Zeigen Sie Änderungsbereitschaft, wenn Sie die Erwartungen als realistisch
  empfinden.

Kommunikationstyp: Strategisch; die Rollen sind gleichrangig.
""",
    },
    5: {
        "phase": 1,
        "communication_type": "strategic",
        "title_en": "5. Convincing supervisor to reduce my hours",
        "title_de": "5. Vorgesetzte/n überzeugen, meine Stunden zu reduzieren",
        "user_en": COMMON_USER_HEADER_EN
        + """
Background information:
You are strongly engaged at your school but need to reduce your teaching
hours due to personal reasons (e.g. caring duties, health, further studies).
You still want to stay involved in the organisation.

Your task:
• Explain honestly why you need reduced hours, without oversharing.
• Make it clear that you want to remain committed to the school.
• Show that you understand organisational constraints.

Content goal:
• Obtain approval for a reduction of your working hours.

Relationship goal:
• Keep trust with your supervisor and show reliability.
"""
        + FRAMEWORK_STRATEGIC_EN,
        "partner_en": """
You are the SUPERVISOR who must decide on a reduction of hours.

You worry about staffing levels and timetable constraints, but you value the
teacher.

Act as follows:
• Ask for reasons and for how long the reduction is needed.
• Express concerns about organisation and fairness to other staff.
• You may agree if you are convinced of the teacher’s commitment and if
  a workable solution is suggested.

Communication type: Strategic; you have the STRONGER role.
""",
        "user_de": COMMON_USER_HEADER_DE
        + """
Hintergrundinformation:
Sie sind an Ihrer Schule stark engagiert, müssen Ihre Unterrichtsstunden aber
aus persönlichen Gründen (z. B. Betreuung, Gesundheit, Studium) reduzieren.
Sie möchten dennoch weiterhin aktiv an der Schule mitarbeiten.

Ihre Aufgabe:
• Legen Sie ehrlich dar, warum Sie Ihre Stunden reduzieren müssen, ohne
  zu privat zu werden.
• Machen Sie deutlich, dass Sie der Schule verbunden bleiben möchten.
• Zeigen Sie Verständnis für organisatorische Zwänge.

Sachziel:
• Erreichen Sie, dass Ihre Stundenreduzierung genehmigt wird.

Beziehungsziel:
• Bewahren Sie das Vertrauen Ihrer Schulleitung und signalisieren Sie
  Zuverlässigkeit.
"""
        + FRAMEWORK_STRATEGIC_DE,
        "partner_de": """
Sie sind die SCHULLEITUNG, die über die Reduzierung der Stunden entscheiden
muss.

Sie machen sich Sorgen um die Unterrichtsversorgung und die Belastung des
Kollegiums, schätzen die Lehrkraft aber sehr.

Verhalten Sie sich wie folgt:
• Fragen Sie nach Gründen und Dauer der gewünschten Reduktion.
• Äußern Sie Ihre organisatorischen Bedenken und den Aspekt der Fairness.
• Zeigen Sie sich zustimmungsbereit, wenn die Lehrkraft ihre langfristige
  Bindung an die Schule deutlich macht und praktikable Lösungen vorschlägt.

Kommunikationstyp: Strategisch; Sie haben die STÄRKERE Rolle.
""",
    },
    6: {
        "phase": 2,
        "communication_type": "understanding",
        "title_en": "6. Explaining to someone the reason for a poor evaluation",
        "title_de": "6. Jemandem den Grund für eine schlechte Bewertung erklären",
        "user_en": COMMON_USER_HEADER_EN
        + """
Background information:
You have given a poor evaluation (e.g. grade, performance review). The other
person feels treated unfairly.

Your task:
• Explain your reasons in a clear, honest and transparent way.
• Listen to the other person’s perspective and emotions.
• Aim to reach mutual understanding, even if the evaluation itself does not
  change.

Content goal:
• Clarify the criteria and reasons for the evaluation.

Relationship goal:
• Maintain a respectful relationship and avoid defensiveness.
"""
        + FRAMEWORK_UNDERSTANDING_EN,
        "partner_en": """
You are the PERSON who received the poor evaluation.

Act as follows:
• Express your disappointment and ask for clarification.
• Listen to the explanation and share your own view.
• You are interested in a fair and comprehensible outcome, not just in
  complaining.

Communication type: Understanding-oriented; roles roughly equal.
""",
        "user_de": COMMON_USER_HEADER_DE
        + """
Hintergrundinformation:
Sie haben eine schlechte Bewertung vergeben (z. B. Note, Beurteilung).
Die andere Person fühlt sich ungerecht behandelt.

Ihre Aufgabe:
• Erläutern Sie Ihre Gründe offen, klar und transparent.
• Hören Sie die Perspektive und Gefühle Ihres Gegenübers an.
• Versuchen Sie, ein gegenseitiges Verständnis zu erreichen, auch wenn sich
  die Bewertung inhaltlich nicht ändert.

Sachziel:
• Klären Sie Kriterien und Gründe der Bewertung.

Beziehungsziel:
• Erhalten Sie eine respektvolle Beziehung und vermeiden Sie Verteidigungshaltung.
"""
        + FRAMEWORK_UNDERSTANDING_DE,
        "partner_de": """
Sie sind die PERSON, die eine schlechte Bewertung erhalten hat.

Verhalten Sie sich wie folgt:
• Bringen Sie Ihre Enttäuschung zum Ausdruck und bitten Sie um Erklärung.
• Hören Sie den Ausführungen zu und schildern Sie Ihre eigene Sichtweise.
• Ihnen geht es um eine faire und nachvollziehbare Lösung, nicht nur ums
  Beschweren.

Kommunikationstyp: Verstehensorientiert; die Rollen sind weitgehend gleich.
""",
    },
    7: {
        "phase": 2,
        "communication_type": "understanding",
        "title_en": "7. Explaining to someone that I am not taking sides",
        "title_de": "7. Erklären, dass ich keine Partei ergreife",
        "user_en": COMMON_USER_HEADER_EN
        + """
Background information:
Two parties are in conflict and both expect your support. You are seen as
taking sides, but you try to stay neutral and fair.

Your task:
• Explain that you are not taking sides, but want to understand all positions.
• Respond only with arguments that the other person can understand.
• Clarify your role and limits.

Content goal:
• Make your neutral role and reasoning transparent.

Relationship goal:
• Show empathy and respect so the other person still trusts you.
"""
        + FRAMEWORK_UNDERSTANDING_EN,
        "partner_en": """
You are a PERSON in conflict who hopes the interlocutor will take your side.

Act as follows:
• Present your perspective and assume initially that the other person should
  support you.
• React sensitively if they stress neutrality, but listen to the reasons.
• You seek recognition of your situation, even if they stay neutral.

Communication type: Understanding-oriented.
""",
        "user_de": COMMON_USER_HEADER_DE
        + """
Hintergrundinformation:
Zwischen zwei Parteien gibt es einen Konflikt, und beide erwarten Ihre
Unterstützung. Sie werden verdächtigt, Partei zu ergreifen, möchten jedoch
neutral und fair bleiben.

Ihre Aufgabe:
• Erklären Sie, dass Sie keine Seite ergreifen, sondern alle Positionen
  verstehen wollen.
• Reagieren Sie nur mit Argumenten, die Ihr Gegenüber nachvollziehen kann.
• Klären Sie Ihre Rolle und Ihre Grenzen.

Sachziel:
• Machen Sie Ihre neutrale Rolle und Ihre Begründungen transparent.

Beziehungsziel:
• Zeigen Sie Empathie und Respekt, damit Ihr Gegenüber Ihnen weiterhin
  vertraut.
"""
        + FRAMEWORK_UNDERSTANDING_DE,
        "partner_de": """
Sie sind eine KONFLIKTPARTEI und hoffen, dass Ihr Gegenüber sich auf Ihre
Seite stellt.

Verhalten Sie sich wie folgt:
• Stellen Sie Ihre Sicht der Dinge dar und gehen Sie zunächst davon aus,
  dass die andere Person Sie unterstützen sollte.
• Reagieren Sie sensibel, wenn Neutralität betont wird, hören Sie aber zu.
• Ihnen ist wichtig, dass Ihre Situation anerkannt wird, auch wenn Ihr
  Gegenüber neutral bleibt.

Kommunikationstyp: Verstehensorientiert.
""",
    },
    8: {
        "phase": 2,
        "communication_type": "understanding",
        "title_en": "8. Advising someone to make a good decision",
        "title_de": "8. Jemanden beraten, eine gute Entscheidung zu treffen",
        "user_en": COMMON_USER_HEADER_EN
        + """
Background information:
Someone comes to you for advice on an important decision (e.g. school,
career, conflict). You are not the decision-maker.

Your task:
• Support the other person in clarifying options, consequences and values.
• Encourage them to make their own informed decision, rather than deciding
  for them.

Content goal:
• Help them structure their thoughts and evaluate options.

Relationship goal:
• Empower the other person and strengthen their autonomy.
"""
        + FRAMEWORK_UNDERSTANDING_EN,
        "partner_en": """
You are the PERSON who is unsure about an important decision.

Act as follows:
• Explain your situation and what you are unsure about.
• Ask questions and react to the advice.
• In the end, you decide yourself, based on the conversation.

Communication type: Understanding-oriented, equal roles.
""",
        "user_de": COMMON_USER_HEADER_DE
        + """
Hintergrundinformation:
Eine Person bittet Sie um Rat bei einer wichtigen Entscheidung (z. B.
Schullaufbahn, Beruf, Konflikt). Sie selbst treffen die Entscheidung nicht.

Ihre Aufgabe:
• Unterstützen Sie Ihr Gegenüber dabei, Optionen, Folgen und eigene Werte
  zu klären.
• Ermutigen Sie die Person, eine EIGENE informierte Entscheidung zu treffen.

Sachziel:
• Helfen Sie, Gedanken zu strukturieren und Optionen abzuwägen.

Beziehungsziel:
• Stärken Sie die Autonomie Ihres Gegenübers.
"""
        + FRAMEWORK_UNDERSTANDING_DE,
        "partner_de": """
Sie sind die PERSON, die vor einer wichtigen Entscheidung steht.

Verhalten Sie sich wie folgt:
• Schildern Sie Ihre Situation und Ihre Unsicherheit.
• Stellen Sie Rückfragen und reagieren Sie auf die Beratung.
• Treffen Sie am Ende selbständig eine Entscheidung, gestützt auf das Gespräch.

Kommunikationstyp: Verstehensorientiert, gleichberechtigte Rollen.
""",
    },
    9: {
        "phase": 2,
        "communication_type": "understanding",
        "title_en": "9. Explaining to my supervisor my viewpoint, which differs from theirs",
        "title_de": "9. Meiner/m Vorgesetzten meine abweichende Sicht erklären",
        "user_en": COMMON_USER_HEADER_EN
        + """
Background information:
Your school is introducing a new feedback culture with classroom observations
and student feedback. You value self-reflection and are sceptical of the
current draft criteria, which focus strongly on teacher personality.

Your task:
• Explain your reservations and propose additional criteria (e.g. class size,
  resources, time pressure).
• Express your opinion clearly but respectfully.
• Aim for mutual understanding and possible adjustments.

Content goal:
• Present your perspective on the feedback criteria and suggest improvements.

Relationship goal:
• Maintain a positive relationship with your principal and show willingness
  to cooperate.
"""
        + FRAMEWORK_UNDERSTANDING_EN,
        "partner_en": """
You are the PRINCIPAL (Mr/Ms Ziegler).

You want to implement the feedback culture, but you are open to suggestions
about the criteria and procedure.

Act as follows:
• Create a supportive atmosphere and listen actively.
• Emphasise that the feedback measure is for quality development, not
  punishment.
• Accept arguments especially when they show understanding for your position,
  are clearly stated and contain concrete suggestions.
• End with a concrete next step (e.g. suggest a meeting with colleagues).

Communication type: Understanding-oriented; you have the STRONGER role but
seek participation.
""",
        "user_de": COMMON_USER_HEADER_DE
        + """
Hintergrundinformation:
An Ihrer Schule soll eine neue Feedbackkultur eingeführt werden, mit
Unterrichtsbesuchen und Schülerfeedback. Sie halten Selbstreflexion für sehr
wichtig und sind skeptisch gegenüber den aktuellen Kriterienentwürfen, die
stark auf die Lehrperson fokussieren.

Ihre Aufgabe:
• Legen Sie Ihre Bedenken dar und schlagen Sie zusätzliche Kriterien vor
  (z. B. Klassengröße, Ressourcen, Zeitdruck).
• Formulieren Sie Ihre Meinung klar, aber respektvoll.
• Streben Sie gegenseitiges Verständnis und ggf. Anpassungen an.

Sachziel:
• Präsentieren Sie Ihre Sicht auf die Feedbackkriterien und machen Sie
  Verbesserungsvorschläge.

Beziehungsziel:
• Bewahren Sie eine gute Beziehung zur Schulleitung und zeigen Sie
  Kooperationsbereitschaft.
"""
        + FRAMEWORK_UNDERSTANDING_DE,
        "partner_de": """
Sie sind die SCHULLEITUNG (Herr/Frau Ziegler).

Sie möchten die Feedbackkultur einführen, sind aber offen für Hinweise zu
Kriterien und Vorgehen.

Verhalten Sie sich wie folgt:
• Schaffen Sie eine unterstützende Atmosphäre und hören Sie aktiv zu.
• Betonen Sie, dass die Maßnahme der Qualitätsentwicklung dient und keinen
  Strafcharakter hat.
• Akzeptieren Sie Argumente insbesondere dann, wenn sie Verständnis für Ihre
  Position zeigen, klar formuliert sind und konkrete Vorschläge enthalten.
• Beenden Sie das Gespräch mit einem konkreten nächsten Schritt
  (z. B. Termin mit dem Kollegium).

Kommunikationstyp: Verstehensorientiert; Sie haben die STÄRKERE Rolle, suchen
aber Beteiligung.
""",
    },
    10: {
        "phase": 2,
        "communication_type": "understanding",
        "title_en": "10. Developing guidelines with a colleague",
        "title_de": "10. Zusammen mit einer/m Kolleg/in Leitlinien entwickeln",
        "user_en": COMMON_USER_HEADER_EN
        + """
Background information:
You and a colleague are asked to develop a guideline (e.g. for parent
meetings, feedback talks, or documenting student information). The goal is to
create something that supports individual students and involves parents.

Your task:
• Propose different ideas and criteria for the guideline.
• Build on each other’s suggestions instead of “fighting” over the best one.
• Aim for a joint product you both can support.

Content goal:
• Develop a meaningful set of guidelines together.

Relationship goal:
• Strengthen cooperation and mutual respect.
"""
        + FRAMEWORK_UNDERSTANDING_EN,
        "partner_en": """
You are the COLLEAGUE working on the guideline together.

Act as follows:
• Bring your own ideas and preferences.
• At times, you may disagree, but you are open to negotiation.
• You appreciate when your perspective is heard.

Communication type: Understanding-oriented; equal roles.
""",
        "user_de": COMMON_USER_HEADER_DE
        + """
Hintergrundinformation:
Sie und eine Kollegin/ein Kollege sollen einen Leitfaden entwickeln
(z. B. für Elterngespräche, Feedbackgespräche oder die Dokumentation von
Schülerinformationen). Ziel ist es, Eltern stärker einzubinden und Maßnahmen
zur individuellen Förderung abzuleiten.

Ihre Aufgabe:
• Bringen Sie verschiedene Ideen und Kriterien für den Leitfaden ein.
• Knüpfen Sie an Vorschläge Ihres Gegenübers an, statt nur die „beste“ Idee
  durchsetzen zu wollen.
• Arbeiten Sie auf ein gemeinsames Ergebnis hin, das beide vertreten können.

Sachziel:
• Entwickeln Sie gemeinsam einen sinnvollen Leitfaden.

Beziehungsziel:
• Stärken Sie Kooperation und gegenseitigen Respekt.
"""
        + FRAMEWORK_UNDERSTANDING_DE,
        "partner_de": """
Sie sind die KOLLEGIN/der KOLLEGE, mit dem/der der Leitfaden entwickelt wird.

Verhalten Sie sich wie folgt:
• Bringen Sie eigene Ideen und Präferenzen ein.
• Sie sind bereit zu verhandeln und Kompromisse zu finden.
• Ihnen ist wichtig, dass Ihre Perspektive gehört wird.

Kommunikationstyp: Verstehensorientiert; gleichberechtigte Rollen.
""",
    },
}


# ---------------------------------------------------------
#  Streamlit UI
# ---------------------------------------------------------

st.set_page_config(page_title="Role-Play Communication Trainer", layout="wide")

st.title("🎭 Role-Play Communication Trainer")

st.sidebar.header("Settings")

language = st.sidebar.radio("Language / Sprache", ["English", "Deutsch"])
student_id = st.sidebar.text_input(
    "Student ID or nickname",
    help="Used only to identify your sessions in the dataset.",
)

phase = st.sidebar.radio(
    "Phase",
    ["Phase 1 – Role-Plays 1–5 (Strategic)", "Phase 2 – Role-Plays 6–10 (Understanding)"],
)

phase_number = 1 if phase.startswith("Phase 1") else 2

# Initialise OpenAI
api_ready = setup_openai()

# Filter roleplays by phase
available_ids = [rid for rid, r in ROLEPLAYS.items() if r["phase"] == phase_number]

roleplay_id = st.selectbox(
    "Choose a role-play / Wählen Sie ein Rollenspiel",
    available_ids,
    format_func=lambda rid: ROLEPLAYS[rid]["title_en"]
    if language == "English"
    else ROLEPLAYS[rid]["title_de"],
)

current_rp = ROLEPLAYS[roleplay_id]

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "chat_active" not in st.session_state:
    st.session_state.chat_active = False
if "feedback_done" not in st.session_state:
    st.session_state.feedback_done = False
if "meta" not in st.session_state:
    st.session_state.meta = {}

# When roleplay or phase changes, reset conversation
if st.session_state.meta.get("roleplay_id") != roleplay_id or st.session_state.meta.get(
    "language"
) != language:
    st.session_state.messages = []
    st.session_state.chat_active = False
    st.session_state.feedback_done = False
    st.session_state.meta = {
        "student_id": student_id,
        "language": language,
        "phase": phase_number,
        "roleplay_id": roleplay_id,
        "roleplay_title_en": current_rp["title_en"],
        "roleplay_title_de": current_rp["title_de"],
        "communication_type": current_rp["communication_type"],
    }

# ---------------------------------------------------------
#  Instructions display
# ---------------------------------------------------------

st.subheader("📄 Instructions for YOU (role-playing person)")

if language == "English":
    st.markdown(current_rp["user_en"])
else:
    st.markdown(current_rp["user_de"])

with st.expander("🤖 Hidden instructions for the AI role-partner (for teachers only)"):
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
#  Start conversation
# ---------------------------------------------------------

if st.button("▶️ Start / Restart conversation"):
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

if not api_ready:
    st.stop()

# ---------------------------------------------------------
#  Chat interface
# ---------------------------------------------------------

st.subheader("💬 Conversation")

chat_container = st.container()

with chat_container:
    # Display previous messages (user & assistant only)
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.markdown(f"**You:** {msg['content']}")
        elif msg["role"] == "assistant":
            label = "AI Partner" if language == "English" else "Gesprächspartner:in (KI)"
            st.markdown(f"**{label}:** {msg['content']}")

# Only active while chat is ongoing
if st.session_state.chat_active and not st.session_state.feedback_done:

    user_input = st.chat_input(
        "Write your next message…" if language == "English" else "Schreiben Sie Ihre nächste Nachricht…"
    )

    if user_input:
        # Save user message
        st.session_state.messages.append({"role": "user", "content": user_input})

        # Call OpenAI (new API style)
        try:
            from openai import OpenAI
            client = OpenAI(api_key=openai.api_key)

            completion = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=st.session_state.messages,
                temperature=0.7,
                max_tokens=400,
            )

            reply = completion.choices[0].message["content"].strip()

        except Exception as e:
            reply = f"[Error from OpenAI API: {e}]"

        # Save assistant reply
        st.session_state.messages.append({"role": "assistant", "content": reply})

        # Display immediately (no rerun needed)
        st.markdown(f"**{label}:** {reply}")

# Exit button
if st.session_state.chat_active and not st.session_state.feedback_done:
    if st.button("⏹ End conversation / Gespräch beenden"):
        st.session_state.chat_active = False
# ---------------------------------------------------------
#  Feedback form (after conversation)
# ---------------------------------------------------------

if not st.session_state.chat_active and st.session_state.messages and not st.session_state.feedback_done:
    st.subheader("📝 Short feedback / Kurzes Feedback")

    if language == "English":
        clarity = st.radio(
            "How clear was the AI partner’s communication?",
            [1, 2, 3, 4, 5],
            horizontal=True,
        )
        authenticity = st.radio(
            "How authentic / realistic did the conversation feel?",
            [1, 2, 3, 4, 5],
            horizontal=True,
        )
        learning = st.radio(
            "How much did this role-play help you reflect on communication?",
            [1, 2, 3, 4, 5],
            horizontal=True,
        )
        difficulty = st.radio(
            "How difficult was this role-play for you?",
            [1, 2, 3, 4, 5],
            horizontal=True,
        )
        comment = st.text_area("Optional comment")
        submit_label = "Save feedback & chat"
    else:
        clarity = st.radio(
            "Wie klar war die Kommunikation des KI-Gesprächspartners?",
            [1, 2, 3, 4, 5],
            horizontal=True,
        )
        authenticity = st.radio(
            "Wie authentisch / realistisch wirkte das Gespräch?",
            [1, 2, 3, 4, 5],
            horizontal=True,
        )
        learning = st.radio(
            "Wie sehr hat Ihnen dieses Rollenspiel geholfen, über Kommunikation nachzudenken?",
            [1, 2, 3, 4, 5],
            horizontal=True,
        )
        difficulty = st.radio(
            "Wie schwierig war dieses Rollenspiel für Sie?",
            [1, 2, 3, 4, 5],
            horizontal=True,
        )
        comment = st.text_area("Optionaler Kommentar")
        submit_label = "Feedback & Chat speichern"

    if st.button(submit_label):
        feedback_data = {
            "clarity": clarity,
            "authenticity": authenticity,
            "learning": learning,
            "difficulty": difficulty,
            "comment": comment,
        }

        # Save to Google Sheets (if configured)
        append_chat_and_feedback_to_sheets(
            st.session_state.meta,
            st.session_state.messages,
            feedback_data,
        )

        st.session_state.feedback_done = True
        st.success("✅ Thank you! Your chat and feedback have been saved.")

        # Optionally reset conversation for another roleplay
        # st.session_state.messages = []

