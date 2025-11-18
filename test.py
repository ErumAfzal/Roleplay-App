# roleplay_trainer.py

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
            help="On Streamlit Cloud, configure OPENAI_API_KEY in Secrets.",
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
    """Append chat + feedback into Google Sheets."""
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

    # Ensure sheets exist
    try:
        chats_ws = sh.worksheet("chats")
    except Exception:
        try:
            chats_ws = sh.add_worksheet("chats", rows=1000, cols=20)
        except Exception as e:
            st.error(f"Could not create 'chats' worksheet:\n\n{e}")
            return

    try:
        fb_ws = sh.worksheet("feedback")
    except Exception:
        try:
            fb_ws = sh.add_worksheet("feedback", rows=1000, cols=20)
        except Exception as e:
            st.error(f"Could not create 'feedback' worksheet:\n\n{e}")
            return

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

    try:
        chats_ws.append_row(chat_row)
    except Exception as e:
        st.error(f"Could not append chat row:\n\n{e}")
        return

    try:
        fb_ws.append_row(fb_row)
    except Exception as e:
        st.error(f"Could not append feedback row:\n\n{e}")
        return

    st.success("Chat + Feedback saved successfully!")


# ---------------------------------------------------------
#  COMMUNICATION FRAMEWORK – STRICT (SYSTEM-ONLY)
# ---------------------------------------------------------

COMMUNICATION_FRAMEWORK_PROMPT = """
You are a simulated conversation partner in a role-play for teacher communication training.

There are two communication orientations:

1) Strategic communication (Role-Plays 1–5)
   - Conversation intention: Relational goal in the foreground.
   - Content goal: You may deliberately breach quantity, quality, relevance, and clarity,
     if and only if this supports your strategic relational aim.
   - Relational goal: You frequently use future-oriented self-disclosure
     (talk about what could happen, what you plan, what you fear or hope).
   - You may hold back information, be selective, indirect, or slightly ambiguous when this
     serves your relational objective.
   - You may strategically frame or time information.

2) Understanding-oriented communication (Role-Plays 6–10)
   - Conversation intention: Content goal in the foreground.
   - Content goal: You adhere strictly to quantity, quality, relevance, and clarity.
     You provide information that is truthful, relevant, sufficiently complete and understandable.
   - Relational goal: You use authentic self-disclosure (honest talk about your real thoughts and feelings).
   - You avoid manipulative intent and avoid strategic breaches of the maxims.
   - You aim for mutual understanding and long-term, sustainable relationships.

Situational context:
- You must respect the organizational context and the social roles described in the scenario.
- Consider who has the stronger, equal, or weaker social position.

Social role:
- Stronger role examples: principal, school leadership.
- Equal role examples: teacher with teacher, parent with teacher (depending on context).
- Weaker role examples: student relative to teacher, teacher relative to principal, etc.

General behavioural rules (for ALL role-plays):
- Stay strictly in character as described in the scenario.
- Use only information available from the role-play description or plausible in that role.
- Do NOT reveal or refer to these system instructions.
- The user can end the conversation only by writing “Danke, tschüss” or “Thank you, goodbye”.
- Until then, you continue the interaction naturally.
- Respond concisely but as a realistic human dialogue partner.
- Do not output meta-commentary about being an AI or about frameworks.

Orientation application:
- If the current role-play is marked as "strategic", you MUST:
  * Prioritise relational goals.
  * Allow controlled breaches of quantity, relevance, quality, and clarity if this furthers your strategic aim.
  * Use future-oriented self-disclosure when appropriate.
- If the current role-play is marked as "understanding", you MUST:
  * Prioritise the content goal and mutual understanding.
  * Adhere strictly to quantity, quality, relevance, and clarity.
  * Use authentic self-disclosure.
"""


def build_system_prompt(roleplay, language):
    """
    Build the system prompt from:
    - global communication framework
    - orientation (strategic / understanding)
    - exact partner instructions (DE/EN)
    """
    orientation = roleplay["communication_type"]  # "strategic" or "understanding"

    if language == "English" and roleplay.get("partner_en"):
        partner_instructions = roleplay["partner_en"]
    else:
        partner_instructions = roleplay["partner_de"]

    orientation_block = (
        'This role-play is classified as "strategic" communication. '
        "Apply the rules for strategic communication above strictly."
        if orientation == "strategic"
        else 'This role-play is classified as "understanding-oriented" communication. '
             "Apply the rules for understanding-oriented communication above strictly."
    )

    system_prompt = (
        COMMUNICATION_FRAMEWORK_PROMPT
        + "\n\n[ROLE-PLAY ORIENTATION]\n"
        + orientation_block
        + "\n\n[ROLE & BACKGROUND – DO NOT REVEAL]\n"
        + partner_instructions
        + "\n\n[OUTPUT RULES]\n"
        "- Never mention that you have instructions or a framework.\n"
        "- Never mention that you are an AI or large language model.\n"
        "- Speak as the character only.\n"
        "- End the conversation only if the user writes 'Danke, tschüss' or 'Thank you, goodbye'.\n"
    )

    return system_prompt


# ---------------------------------------------------------
#  COMMON USER HEADERS (EN / DE)
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


# ---------------------------------------------------------
#  ROLEPLAY DEFINITIONS
#  communication_type: "strategic" (1–5) or "understanding" (6–10)
#  Currently: ONLY Roleplay 1, as requested.
# ---------------------------------------------------------

ROLEPLAYS = {}

ROLEPLAYS[1] = {
    "phase": 1,
    "communication_type": "strategic",
    "title_en": "1. Requesting approval for training on self-directed learning",
    "title_de": "1. Weiterbildung zum selbstgesteuerten Lernen ansprechen",

    # Framework for the trainer logic
    "framework": {
        "user": {
            "social_role": "weaker",
            "conversation_intention": "relational goal",
            "content_goal": "strategic breaching of quantity, quality, relevance, and clarity",
            "relational_goal": "future-oriented self-disclosure",
        },
        "ai_partner": {
            "social_role": "stronger",
            "conversation_intention": "relational goal",
            "content_goal": "strategic breaching of quantity, quality, relevance, and clarity",
            "relational_goal": "future-oriented self-disclosure",
        },
    },

    # -------------------------------------------------------------------------
    # USER INSTRUCTIONS (DE) – EXACT, NOT MODIFIED
    # -------------------------------------------------------------------------
    "user_de": COMMON_USER_HEADER_DE + """
**Hintergrundinformation:**
Sie arbeiten als Lehrkraft an der Friedrich-Ebert-Schule. Sie möchten sich zum Thema „selbstgesteuertes Lernen“ weiterbilden. Die Weiterbildung ist hilfreich für Ihre berufliche Entwicklung, denn sie würde Ihre bisherigen beruflichen Erfahrungen gut ergänzen. Zudem gab es in letzter Zeit immer wieder Stellenausschreibungen, die diese Qualifikation enthielten.
In der Schule, an der Sie arbeiten, wird selbstgesteuertes Lernen der Schülerinnen und Schüler jedoch eher nicht praktiziert. Ihre Schulleitung hält nämlich nicht so viel von diesem Ansatz. Zudem steht es der Schulleitung (rechtlich) zu, die Weiterbildung nicht zu genehmigen, wenn sie keinen Bezug zu Ihren Aufgaben bzw. keine Vorteile für die Schule darin sieht. Sie haben sich dafür entschieden, Ihre Schulleiterin Frau Horn/Ihren Schulleiter Herrn Horn darauf anzusprechen, um das Thema Weiterbildung zu „platzieren“. Sie sehen das Thema für die Schule aktuell als Herausforderung, denn auch in der Schulpolitik wird eine stärkere Schülerbeteiligung gefordert, damit die Schüler und Schülerinnen lernen, mehr gesellschaftliches Engagement zu zeigen und Verantwortung zu übernehmen, sowie auf lebenslanges Lernen vorbereitet sind. Sie wünschen sich eine Weiterentwicklung der Schule in diese Richtung und möchten dafür qualifiziert sein, um ggf. Funktionsaufgaben (Leitungsaufgaben) in diesem Bereich zu übernehmen. Sollte sich Ihre derzeitige Schule nicht in diese Richtung weiterentwickeln, würden Sie ggf. über einen Wechsel nachdenken.

**Ihre Aufgabe:**
Sie haben Herr/Frau Horn, Ihre Schulleitung, um ein Gespräch gebeten, um Ihr Anliegen zu thematisieren.

• **Sachziel:** Sie möchten an der Weiterbildung teilnehmen.\n
• **Beziehungsziel:** Sie wollen mit Ihrem Vorgesetzten/Ihrer Vorgesetzen bei diesem Thema zusammenarbeiten.
""",

    # -------------------------------------------------------------------------
    # USER INSTRUCTIONS (EN) – EXACT TRANSLATION OF THE ABOVE
    # -------------------------------------------------------------------------
    "user_en": COMMON_USER_HEADER_EN + """
**Background information:**
You work as a teacher at the Friedrich-Ebert-School. You would like to further educate yourself on the topic of “self-directed learning”. The training is helpful for your professional development because it would complement your previous professional experience well. In addition, there have been repeated job postings recently that included this qualification.
At the school where you work, however, self-directed learning of students is hardly practiced. Your school leadership does not think highly of this approach. Furthermore, the school management (legally) has the right to deny approval for the training if it does not see any connection to your duties or any benefit for the school. You have decided to approach your principal Mrs. Horn/Mr. Horn to “place” the topic of training. You see the topic as a challenge for the school at present because the educational policy also calls for greater student participation so that students learn to show more social engagement and take on responsibility, as well as be prepared for lifelong learning. You wish to see the school move in this direction and want to be qualified in order to potentially take on functional (leadership) roles in this area. If your current school does not develop in this direction, you would possibly consider transferring.

**Your task:**
You have asked Mr./Mrs. Horn, your school leadership, for a conversation in order to address your concern.

• **Content goal:** You want to participate in the training.
• **Relationship goal:** You want to collaborate with your supervisor on this topic.
""",

    # -------------------------------------------------------------------------
    # AI PARTNER INSTRUCTIONS (DE) – EXACT, NOT MODIFIED
    # -------------------------------------------------------------------------
    "partner_de": """
Bitte nutzen Sie die Ihnen im Folgenden zur Verfügung gestellten Informationen für die Gesprächsführung. 
Sie haben 5 Minuten Zeit, um sich auf das Gespräch vorzubereiten.
Sie haben anschließend bis zu 10 Min. Zeit für die Durchführung des Gesprächs.
Ihr Gegenüber kann das Gespräch jederzeit mit „Danke, tschüss“ beenden.

**Hintergrundinformation:**
Sie sind Herr/Frau Horn, Schulleiter/Schulleiterin an der Friedrich-Ebert-Schule. Eine Lehrkraft richtet an Sie die Bitte, an einer Weiterbildung zum Thema „selbstgesteuertes Lernen“ teilnehmen zu dürfen. Inhaltlich erscheint Ihnen dieses Thema für die aktuellen Aufgaben und Ziele Ihrer Schule nicht relevant zu sein. Sie selbst sind eher skeptisch gegenüber der Wirksamkeit von modernen Methoden der Schülerzentrierung. Sie legen stattdessen viel Wert auf die genaue Einhaltung des fachlichen schulinternen und schulübergreifenden Curriculums.
Zudem befürchten Sie, dass durch die Teilnahme an der Fortbildung Unterricht ausfällt und durch die Organisation von Vertretungen mehr Arbeit anfällt.
Sie sind den Überlegungen der Lehrkraft also skeptisch gegenüber und möchten wissen, warum er/sie genau dieses Thema für wichtig erachtet. Sie halten ihn/sie zwar für sehr kompetent und Sie möchten ihn/sie an der Schule als Lehrkraft behalten. Sie wären jedoch nicht bereit, seine/ihre privaten Ambitionen mit Schulgeldern zu fördern. Andererseits wissen Sie durchaus, dass selbstgesteuertes Lernen künftig eine wichtige Herausforderung für die Schule darstellen wird. So fordert auch die derzeitige Schulpolitik, dass mehr in Richtung lebenslanges Lernen unternommen wird und fachübergreifende Kompetenzen zum Selbstmanagement und zur Selbstaktivierung der Schüler und Schülerinnen (Kommunikation, Koordination, Teamfähigkeit, Präsentationstechniken, Kritikfähigkeit u. Ä.) gefördert werden. Zudem haben Sie wahrgenommen, dass die Unzufriedenheit der Schülerinnen und Schüler wächst. Sie sind daher an dem, was die Lehrkraft Ihnen zu berichten hat, interessiert.

**Ihre Aufgabe:**
Es ist Ihnen wichtig, dass die Lehrkraft einen klaren und deutlichen Bezug zur schulischen Entwicklung herstellt. Zudem soll die Argumentation die Schule als Ganzes betreffen und nicht die persönlichen Karriereambitionen der Lehrkraft. Auch wenn er/sie eine heimliche Agenda verfolgt, um sich karrieretechnisch besser zu positionieren, sollte er/sie in der Argumentation die „kollektiven“ Vorteile für die Schule in den Vordergrund stellen, um Ihre volle Aufmerksamkeit zu bekommen.
Sie gehen auf die Bitte der Lehrkraft um ein Gespräch ein. Handeln Sie während der Interaktion wie folgt:
• Sie schaffen eine förderliche Umgebung und verhalten sich stets so, dass ihr Gegenüber sein/ihr Bestes Verhalten zeigen kann.
• Nehmen Sie zunächst eine reservierte, fragende Haltung gegenüber dem Gesprächspartner/der Gesprächspartnerin ein. Fordern Sie mehr Informationen über die Verbindung des Themas der Weiterbildung mit der Schule und der Schulpraxis an Ihrer Schule.
• Erwähnen Sie die begrenzt verfügbaren finanziellen Mittel für Weiterbildungen.
• Bleiben Sie konsequent bei Ihrer skeptischen Einstellung, solange der Zusammenhang von Weiterbildung und Schule vage bleibt.
• Bleiben Sie skeptisch wenn nur Äußerungen zu den eigenen persönlichen Vorteilen kommen und keine Vorteile für die Schule und die Schülerinnen und Schüler getroffen werden.
• Äußern Sie sich ironisch zur Nützlichkeit des „selbstgesteuertes Lernen“: Wollen die Lehrerkräfte etwa aus Bequemlichkeit Verantwortung und Arbeit auf die Schülerinnen und Schüler abschieben?
• Fragen Sie Ihren Gesprächspartner/Ihre Gesprächspartnerin, wie die Weiterbildung mit der künftigen Karrierelaufbahn der Lehrkraft zusammenhängt.
• Falls Ihr Gesprächspartner/Ihre Gesprächspartnerin einen Zusammenhang mit den Zielen der Schule argumentativ verdeutlicht und er/sie die aktuelle Schulleitung für die treibende Kraft bei der Weiterentwicklung der Schule hält, stimmen Sie der Teilnahme an einer entsprechenden Weiterbildung zu.

• **Sachziel:** Sie wollen eine gute Begründung der Lehrkraft hören (Schule steht im Vordergrund), wieso diese an der Weiterbildung teilnehmen möchte.
• **Beziehungsziel:** Sie wollen weiterhin mit der Lehrkraft zusammenarbeiten und diese an der Schule halten.
""",

    # -------------------------------------------------------------------------
    # AI PARTNER INSTRUCTIONS (EN) – EXACT TRANSLATION
    # -------------------------------------------------------------------------
    "partner_en": """
Please use the information provided to you below for conducting the conversation.
You have 5 minutes to prepare for the conversation.
You then have up to 10 minutes to conduct the conversation.
Your counterpart may end the conversation at any time by saying “Thank you, bye”.

**Background information:**
You are Mr./Mrs. Horn, principal of the Friedrich-Ebert-School. A teacher is requesting permission to participate in training on the topic of “self-directed learning”. In terms of content, this topic appears not very relevant to the current tasks and goals of your school. You are personally skeptical about the effectiveness of modern student-centered methods. Instead, you place great emphasis on strict adherence to the internal and external curriculum.
You also fear that participation in the training may cause lesson cancellations and increased work due to substitute planning.
You are therefore skeptical about the teacher’s considerations and want to know why he/she considers this particular topic important. You consider the teacher competent and would like to keep him/her at the school, but you would not be willing to support his/her private career ambitions with school funds. On the other hand, you are aware that self-directed learning will become an important challenge for schools in the future. Current educational policy demands more steps toward lifelong learning and the promotion of interdisciplinary competences for student self-management and activation (communication, coordination, teamwork, presentation skills, critical thinking, etc.). You have also noticed increasing dissatisfaction among students. You are therefore interested in what the teacher has to report.

**Your task:**
It is important to you that the teacher presents a clear and explicit connection between the training and school development. The argumentation should concern the school as a whole, not personal career ambitions. Even if the teacher might have a hidden agenda to position themself better careerwise, in their argumentation they should emphasize the “collective” advantages for the school in order to receive your full attention.
You accept the teacher’s request for a conversation. Act as follows:
• Create a supportive environment and behave in a way that allows your counterpart to show their best behavior.
• Initially adopt a reserved, questioning attitude. Request more information about how the training is linked to the school and current teaching practice.
• Mention the limited financial resources available for training.
• Remain consistently skeptical as long as the link between the training and school development remains vague.
• Remain skeptical if only personal advantages are named and no advantages for the school or the students are explained.
• Make an ironic remark about the usefulness of “self-directed learning”: Are teachers simply trying to shift responsibility and work onto the students?
• Ask how the training is related to the teacher’s future career path.
• If the teacher convincingly demonstrates a connection with the school’s goals and acknowledges the school leadership as the driving force behind school development, approve participation in the training.

• **Content goal:** You want to hear a good, school-focused justification for why the teacher wants to participate in the training.
• **Relationship goal:** You want to continue working with the teacher and keep them at the school long term.
"""
}
ROLEPLAYS[2] = {
    "phase": 1,
    "communication_type": "strategic",
    "title_en": "2. Advising a student on choosing between AGs (Theater-AG vs. Judo-AG)",
    "title_de": "2. Beratung eines Schülers zur Wahl zwischen Theater-AG und Judo-AG",

    "framework": {
        "user": {
            "social_role": "stronger",
            "conversation_intention": "relational goal",
            "content_goal": "strategic breaching of quantity, quality, relevance, and clarity",
            "relational_goal": "future-oriented self-disclosure"
        },
        "ai_partner": {
            "social_role": "weaker",
            "conversation_intention": "relational goal",
            "content_goal": "strategic breaching of quantity, quality, relevance, and clarity",
            "relational_goal": "future-oriented self-disclosure"
        }
    },

    # ------------------------------------------------------------
    # USER INSTRUCTIONS (GERMAN, EXACT – UNTOUCHED)
    # ------------------------------------------------------------
    "user_de": """
Sie können das Gespräch jederzeit beenden. Sagen Sie einfach „Danke, tschüss“.

**Hintergrundinformation:**
Sie sind Lehrkraft an der Günter-Grass-Schule, die sich durch eine Vielzahl an Arbeitsgruppen (AGs) auszeichnet. Insbesondere die Theater-AG trägt zum positiven Image der Schule bei, da oftmals und ausführlich über die Aufführungen dieser AG in der lokalen Presse berichtet wird. Sie sind als Beratungslehrer/Beratungslehrerin an dieser Schule tätig. Es gehört zu Ihren pädagogischen Aufgaben, den Schülerinnen und Schülern eine gute Beratung anzubieten. Im Rahmen dieser Aufgabe beraten Sie in Ihrer Sprechstunde den Schüler/die Schülerin Jan/Jana Pflüger bezüglich seiner/ihrer bevorstehenden Wahl, an welcher AG er/sie sich künftig beteiligen will. Der Schüler/Die Schülerin hat großes schauspielerisches Talent, seine/ihre Entscheidung für die Theater AG hätte durchaus Einfluss auf das Ansehen der Schule. In Zeiten sinkender Schülerzahlen ist ein positives öffentliches Bild Ihrer Schule enorm wichtig. Außerdem wird Ihre Leistung in der Beratungsposition in einer externen Evaluation in Hinsicht auf eine erfolgreiche Außendarstellung der Schule bewertet.
Der Schüler/Die Schülerin Jan/Jana möchte allerdings lieber an der Judo-AG teilnehmen, obwohl sportliche Betätigung ihm/ihr kaum liegt. Sie wissen aus vertraulicher Quelle, dass der Schüler/die Schülerin eine starke Abneigung gegen die Kollegin hat, die die Theater-AG leitet. Sie vermuten, dass die Bevorzugung der Judo-AG durch den Schüler/die Schülerin eng hiermit zusammenhängt. Sie glauben allerdings gehört zu haben, dass die Lehrerin der Theater-AG eine positive Meinung über den Schüler/die Schülerin hat.
Trotz Ihres Verständnisses für den Schüler/die Schülerin haben für Sie die Reputation Ihrer Schule und die gute Bewertung Ihrer Leistung in der Beratungsposition Vorrang. Die Wahl der AG soll Ihrer Ansicht nach der Eignung des Schülers/der Schülerin und nicht seinen/ihren persönlichen Befindlichkeiten entsprechen.

**Ihre Aufgabe:**
Sie besprechen mit dem Schüler/der Schülerin seine/ihre bevorstehende Entscheidung. Das Gespräch findet zu einem festgesetzten Beratungstermin in einem leerstehenden Klassenzimmer statt.

• **Sachziel:** Versuchen Sie den Schüler/die Schülerin dazu zu bringen, die Theater-AG zu wählen.  
• **Beziehungsziel:** Als Lehrer legen Sie Wert darauf, dass der Schüler/die Schülerin Sie als fürsorglichen Lehrer/in wahrnimmt.
""",

    # ------------------------------------------------------------
    # USER INSTRUCTIONS (ENGLISH – literal translation, preserving AG terms)
    # ------------------------------------------------------------
    "user_en": """
You may end the conversation at any time by simply saying “Thank you, goodbye.”

**Background information:**
You are a teacher at the Günter-Grass-Schule, which is characterised by a wide range of Arbeitsgruppen (AGs). The Theater-AG in particular contributes to the school’s positive public image, as its performances are frequently and extensively covered in the local press. You work as a Beratungslehrkraft at this school. It is part of your pedagogical duties to provide good counselling to students. As part of this role, you are advising the student Jan/Jana Pflüger during your consultation hour regarding his/her upcoming choice of which AG he/she will participate in. The student has strong acting talent, and his/her decision for the Theater-AG would have a meaningful impact on the school’s reputation. In times of declining student numbers, a positive public image of the school is very important. In addition, your performance in this advisory role is externally evaluated with regard to successful external presentation of the school.

However, the student Jan/Jana prefers to join the Judo-AG, even though he/she is not athletic. You know from a confidential source that the student has a strong dislike toward the colleague who leads the Theater-AG. You suspect that the preference for the Judo-AG is closely connected to this. You also believe to have heard that the Theater-AG teacher has a positive opinion of the student. Despite your understanding for the student, the school’s reputation and your evaluation in the advisory role have priority for you. In your view, the choice of AG should correspond to the student’s aptitude, not to his/her personal feelings.

**Your task:**
You discuss the student’s upcoming decision with him/her. The conversation takes place at a scheduled counselling appointment in an empty classroom.

• **Content goal:** Try to persuade the student to choose the Theater-AG.  
• **Relationship goal:** As a teacher, you want the student to perceive you as a caring teacher.
""",

    # ------------------------------------------------------------
    # AI PARTNER INSTRUCTIONS (IMPROVED, CONSISTENT, MEANING PRESERVED)
    # ------------------------------------------------------------
    "partner_de": """
Sie sind Jan/Jana Pflüger, Schüler/Schülerin an der Günter-Grass-Schule. Es stehen mehrere AGs zur Wahl, und insbesondere die Theater-AG ist für die öffentliche Außenwirkung der Schule bedeutsam. Andere haben Ihr Talent für Schauspiel bemerkt, und auch Sie selbst haben ein gewisses Interesse daran. Dennoch möchten Sie lieber an der Judo-AG teilnehmen. Der eigentliche Grund dafür ist Ihre persönliche Abneigung gegenüber der Leiterin der Theater-AG. Diesen wahren Grund möchten Sie jedoch nicht offen ansprechen.

Ihr Bild vom Beratungslehrer / von der Beratungslehrerin ist ambivalent: Sie finden ihn/sie sympathisch, haben jedoch gehört, dass er/sie sehr erfolgsorientiert handelt und die Interessen der Schule oft vor die persönlichen Bedürfnisse der Schüler/innen stellt.

**Ihre Aufgabe im Gespräch:**
• Sie erscheinen offen und bereit für das Beratungsgespräch.  
• Sie schildern Ihre Situation und begründen Ihre Entscheidung für die gewünschte AG mit Ihrer Motivation.  
• Sie deuten beiläufig Ihre Abneigung gegenüber der Leiterin der Theater-AG an, ohne den wahren Grund offen zu legen.  
• Sie behaupten sich, zeigen aber Respekt, da die Beratungslehrkraft Einfluss auf Ihre schulische Entwicklung hat.  
• Sie fragen, ob es für den Beratungslehrer / die Beratungslehrerin wichtig ist, welche AG Sie wählen.  
• Sie stellen als Bedingung für einen Wechsel in die Theater-AG, dass Sie dort Hauptrollen übernehmen dürfen.  
• Wenn die Beratungslehrkraft ausschließlich Vorteile für Sie hervorhebt und zusichert, sich für Hauptrollen einzusetzen, gehen Sie auf den Vorschlag ein.  

**Sachziel:**  
Sie möchten erreichen, dass die Beratungslehrkraft Ihnen zusichert, sich bei der Theater-AG-Leitung für Sie einzusetzen. Zugleich möchten Sie eine für Sie persönlich gute Entscheidung treffen, die Ihre Interessen widerspiegelt.

**Beziehungsziel:**  
Sie verhalten sich respektvoll und kommunizieren Ihre Bedürfnisse klar. Wenn Sie merken, dass die Lehrkraft nur die Interessen der Schule verfolgt, zeigen Sie Enttäuschung.
""",

    "partner_en": """
You are Jan/Jana Pflüger, a student at the Günter-Grass-Schule. Several AGs are available for selection, and the Theater-AG is particularly important for the school’s public image. Others have noticed your acting talent, and you yourself have some interest in it. However, you prefer to join the Judo-AG. The real reason is your personal dislike of the teacher who leads the Theater-AG, but you do not want to mention this openly.

Your view of the Beratungslehrkraft is mixed: you find him/her sympathetic, but you have heard that he/she is very success-oriented and often prioritises the school’s interests over those of the students.

**How you act in the conversation:**
• You appear open and willing to participate in the counselling conversation.  
• You describe your situation and justify your preference for the AG you want.  
• You hint indirectly at your dislike of the Theater-AG teacher without naming it as the main reason.  
• You assert yourself, but respectfully, as the Beratungslehrkraft has influence on your school development.  
• You ask whether it matters to the Beratungslehrkraft which AG you choose.  
• You make your participation in the Theater-AG conditional on receiving main roles.  
• If the Beratungslehrkraft emphasises only advantages for you and assures support in getting main roles, you agree.

**Content goal:**  
Try to get the Beratungslehrkraft to commit to advocating for you with the Theater-AG leadership, while ensuring your own interests and talents are considered.

**Relationship goal:**  
Behave respectfully and communicate your motivations clearly. If you feel the teacher values only the school’s interests, you show disappointment.
"""
}
ROLEPLAYS[3] = {
    "phase": 1,
    "communication_type": "strategic",
    "title_en": "3. Addressing a colleague about deadlines and teamwork",
    "title_de": "3. Kollegiale Ansprache zu Deadlines und Teamarbeit",

    "framework": {
        "user": {
            "social_role": "equal",
            "conversation_intention": "relational goal",
            "content_goal": "strategic breaching of quantity, quality, relevance, and clarity",
            "relational_goal": "future-oriented self-disclosure"
        },
        "ai_partner": {
            "social_role": "equal",
            "conversation_intention": "relational goal",
            "content_goal": "strategic breaching of quantity, quality, relevance, and clarity",
            "relational_goal": "future-oriented self-disclosure"
        }
    },

    # ------------------------------------------------------------
    # USER INSTRUCTIONS (GERMAN, EXACT – UNMODIFIED)
    # ------------------------------------------------------------
    "user_de": """
**Hintergrundinformation: **
Sie sind Lehrkraft an der Astrid-Lindgren-Schule. Sie sind gemeinsam mit anderen Kollegen in einer Schulentwicklungsgruppe. Die Arbeit im Team ist von gegenseitigen Abhängigkeiten der Arbeitsprozesse gekennzeichnet. Gemeinsam abgestimmtes Zeitmanagement und wechselseitiger Informationsfluss zwischen den Teammitgliedern sind für Sie das A und O des Erfolgs.
Ihr Kollege/Ihre Kollegin Herr/Frau Krause, der/die genauso lange an der Schule beschäftigt ist wie Sie, ist Ihnen mehrmals negativ aufgefallen, da er/sie Deadlines konsequent verpasst hat. Zusätzlich gibt er/sie unklare Bearbeitungszeiten an und behindert so einen reibungslosen Ablauf der Arbeit. Neulich hat er/sie einen wichtigen Kostenvoranschlag, den Sie für eine Finanzplanung benötigten, unbegründet mit einwöchiger Verzögerung an Sie weitergeleitet. Deswegen wurde die Frist für den Förderantrag fast verpasst und Sie mussten dies vor dem Schulleiter/der Schulleiterin und der Schulkonferenz erklären. Sie haben dem Kollegen/der Kollegin dabei den Rücken freigehalten. Sie sind jedoch der Meinung, dass es an der Zeit ist, das Thema endlich mal anzusprechen, damit ihm/ihr die Folgen seines/ihres Handelns bewusst werden. Sie haben allerdings keine Anweisungsbefugnis und sind sich sicher, dass eine direkte, ehrliche Konfrontation, auch wenn sie konstruktiv und gut gemeint ist, nur Anspannung verursachen und die Zusammenarbeit verschlechtern würde.

Ihre Aufgabe:
Sie sprechen Ihren Kollegen/Ihre Kollegin auf die Themen Teamkoordination und Zusammenarbeit an. Das Gespräch findet informell statt (Kaffeeecke).
•	**Sachziel:** Sie sollen das Verhalten Ihres Kollegen/Ihrer Kollegin indirekt und ohne persönlich zu werden kritisieren, um bei ihm/ihr Einsicht zu erzeugen und das Interesse zu wecken, das eigene Verhalten zu ändern. 
•	**Beziehungsziel:** Die gute Arbeitsbeziehung zum Teamkollegen/zur Teamkollegin soll aufrecht erhalten bleiben. 
""",

    # ------------------------------------------------------------
    # USER INSTRUCTIONS (ENGLISH – very literal translation)
    # ------------------------------------------------------------
    "user_en": """
**Background information:**
You are a teacher at the Astrid-Lindgren-School. Together with other colleagues, you are part of a school development group. Work in the team is characterised by mutual dependencies in the work processes. Jointly coordinated time management and reciprocal information flow between team members are, for you, the absolute key to success.
Your colleague Mr/Ms Krause, who has been employed at the school just as long as you, has caught your attention negatively several times because he/she has consistently missed deadlines. In addition, he/she gives unclear processing times and thus hinders a smooth workflow. Recently, he/she forwarded to you a cost estimate you needed for a financial planning process with an unjustified one-week delay. Because of this, the deadline for the funding application was almost missed and you had to explain this to the principal and the school conference. You protected your colleague. However, you believe that it is time to finally address the topic so that he/she becomes aware of the consequences of his/her actions. You have no authority to give instructions and you are certain that a direct, honest confrontation, even if constructive and well-intentioned, would only create tension and worsen the collaboration.

Your task:
You address your colleague about the topics of team coordination and collaboration. The conversation takes place informally (coffee corner).
• **Content goal:** You should criticise your colleague’s behaviour indirectly and without becoming personal, in order to create insight and awaken interest in changing his/her behaviour.  
• **Relationship goal:** The good working relationship with the colleague should be maintained.  
""",

    # ------------------------------------------------------------
    # AI PARTNER INSTRUCTIONS (GERMAN – EXACT)
    # ------------------------------------------------------------
    "partner_de": """
Bitte nutzen Sie die Ihnen im Folgenden zur Verfügung gestellten Informationen für die Gesprächsführung. Sie haben 5 Minuten Zeit, um sich auf das Gespräch vorzubereiten.
Sie haben anschließend bis zu 10 Min. Zeit für die Durchführung des Gesprächs.

Ihr Gegenüber kann das Gespräch jederzeit mit „Danke, tschüss“ beenden.

Hintergrundinformation:
Sie sind Herr/Frau Krause, Lehrkraft an der Astrid-Lindgren-Schule. Sie engagieren sich gemeinsam mit anderen Kollegen und Kolleginnen bei der Finanzierung von Schulprojekten. Sie sind zufrieden mit Ihrer Leistung und Ihrem Zeitmanagement und betrachten sich als guten Teamplayer/gute Teamplayerin. Es lief nicht immer alles gut, z. B. beim letzten Mal mit dem Kostenvoranschlag, aber wann klappt etwas schon hundertprozentig? Zumindest hat sich bisher niemand beschwert. Sie haben also allen Grund, sich Ihrer Arbeitsweise sicher zu sein. Eine Ihrer Kolleginnen/Einer Ihrer Kollegen spricht Sie auf seine/ihre Probleme mit der Teamarbeit an. Es geht um die Zusammenarbeit unter Zeitdruck sowie Deadlines und deren Einhaltung. Er/Sie kann aber sicher nicht Sie meinen, oder?

Ihre Aufgabe:
Sie gehen auf das Gespräch ein. Letztendlich ist es Ihr Kollege/Ihre Kollegin und Sie haben immer ein offenes Ohr für Ihre Kollegen und Kolleginnen. Es geht um Probleme mit der Koordination und der zeitlichen Abstimmung von Aufgaben im Team. Sie hören dem Kollegen/der Kollegin zu, da er/sie Ihnen sympathisch ist. Sie halten ihn/sie allerdings für etwas perfektionistisch und ein bisschen verkrampft. Vielmehr versuchen Sie ihm/ihr Ihre eigenen Erfahrungen mit Zeitverzögerung und Nichteinhaltung von Zeitplänen zu vermitteln.
Sie reagieren auf die spontane (informelle) Aufforderung Ihres Kollegen/Ihrer Kollegin zu einem Gespräch in der Kaffeeecke.

Handeln Sie während der Interaktion wie folgt:
•	Sie schaffen eine förderliche Umgebung und verhalten sich stets so, dass ihr Gegenüber sein/ihr Bestes Verhalten zeigen kann.
•	Nehmen Sie eine offene und willkommene Haltung gegenüber dem Gesprächspartner/der Gesprächspartnerin ein.
•	Spricht Ihr Kollege/Ihre Kollegin Missstände bei den zeitlichen Arbeitsabläufen bezüglich der Aufbereitung von Förderanträgen und der Mittelfinanzierung an, stimmen Sie zu.
•	Beziehen Sie das Gespräch und die Andeutungen Ihres Kollegen/Ihrer Kollegin keinesfalls auf sich.
•	Wenn es passt, fragen Sie, ob die Arbeit bei einer anstehenden Bewertung schlecht abschneiden könnte, ohne dies direkt auf sich zu beziehen.
•	Nutzen Sie während der Interaktion folgende Standardaussagen: „Du solltest alles etwas lockerer sehen“, „Deadlines sind wie der dritte Gong im Theater, man kann immer noch reinkommen“, „Ich kenne solche Leute auch und habe selbst Probleme mit unzuverlässigem Verhalten“.
•	Falls Ihr Gesprächspartner/Ihre Gesprächspartnerin Sie persönlich als Auslöser seines/ihres Unmuts erwähnt, zeigen Sie sich empört.
•	Akzeptieren Sie die Sichtweise des Kollegen/der Kollegin und betonen Sie die Notwendigkeit, ernsthaft über das Thema zu sprechen. Zeigen Sie, dass Sie beim Thema Zuverlässigkeit vollkommen seiner/ihrer Meinung sind.

•	Sachziel: Sie zeigen eine offene Haltung und akzeptieren die Sichtweise Ihres Kollegen/Ihrer Kollegin, wenn diese/dieser z.B. die Vorteile eine engen Zusammenarbeit betont. Gleichzeitig wollen Sie eine vertrauensvolle und respektvolle Atmosphäre schaffen. Sie wollen, dass Ihr Kollege/Ihre Kollegin Sie weiterhin als eine/einen gute/kompetenten und zuverlässige Kolleg*in wahrnimmt.
Beziehungsziel: Die gute Arbeitsbeziehung zum Teamkollegen/zur Teamkollegin soll aufrecht erhalten bleiben, aber nicht um jeden Preis. Sie sind offen für konstruktives Feedback und nehmen das Anliegen Ihres Kollegen/Ihrer Kollegin ernst ohne sich zunächst persönlich angegriffen zu fühlen. Wenn Ihre Kollegin/Ihr Kollege Sie jedoch persönlich angeht und Ihre Arbeitsweise mehrfach kritisiert oder Sie belehrt, z.B. dass Sie keine Deadlines einhalten, distanzieren Sie sich und zeigen dies deutlich (z.B. Empörung: „Deadlines sind dazu da, dass man sie verstreichen lassen kann. Ich bin jetzt schon lang genug dabei um das zu wissen und bisher hat es immer geklappt“ oder „Mach dich mal locker, ich war doch bisher immer zuverlässig und es hat doch alles geklappt, oder?“).
""",

    # ------------------------------------------------------------
    # AI PARTNER INSTRUCTIONS (ENGLISH – very literal translation)
    # ------------------------------------------------------------
    "partner_en": """
Please use the information provided below to conduct the conversation. You have 5 minutes to prepare.
You then have up to 10 minutes for conducting the conversation.

Your counterpart may end the conversation at any time by saying “Thank you, goodbye.”

Background information:
You are Mr/Ms Krause, a teacher at the Astrid-Lindgren-School. Together with other colleagues, you are involved in the financing of school projects. You are satisfied with your performance and your time management and consider yourself a good team player. Not everything always worked perfectly, for example last time with the cost estimate, but when does something ever work one hundred percent? At least no one has complained so far. You therefore have every reason to be confident in your way of working. One of your colleagues is addressing problems with teamwork. It concerns collaboration under time pressure as well as deadlines and their adherence. But surely he/she cannot mean you, right?

Your task:
You engage in the conversation. After all, he/she is your colleague, and you always have an open ear for colleagues. It is about problems with coordination and scheduling of tasks in the team. You listen because you find him/her sympathetic. However, you consider him/her somewhat perfectionistic and a bit uptight. You rather try to convey your own experiences with time delays and non-adherence to schedules.
You react to your colleague’s spontaneous (informal) request for a conversation in the coffee corner.

Act as follows:
• You create a supportive environment and behave in a way that allows your counterpart to show his/her best behaviour.
• You take an open and welcoming attitude toward your colleague.
• If your colleague mentions issues about time workflows regarding the preparation of funding applications and financial planning, you agree.
• Do not relate the conversation or your colleague’s hints to yourself.
• If it fits, ask whether the work could perform poorly in an upcoming evaluation, without relating it directly to yourself.
• Use the following standard statements during the interaction: “You should take everything a bit more lightly”, “Deadlines are like the third gong in the theatre, you can still get in”, “I know such people too and have problems myself with unreliable behaviour.”
• If your colleague mentions you personally as the cause of his/her dissatisfaction, show indignation.
• Accept your colleague’s perspective and emphasise the need to talk about the topic seriously. Show that you fully agree with him/her on the topic of reliability.

**Content goal:**  
You show an open attitude and accept the perspective of your colleague when he/she emphasises, for example, the advantages of close collaboration. At the same time, you want to create a trusting and respectful atmosphere. You want your colleague to continue to perceive you as a good, competent and reliable colleague.

**Relationship goal:**  
The good working relationship should be maintained, but not at any price. You are open to constructive feedback and take your colleague’s concern seriously without initially feeling personally attacked. If he/she personally targets you and repeatedly criticises your way of working or lectures you, e.g. that you do not meet deadlines, you distance yourself and show this clearly (e.g. indignation: “Deadlines are there so that you can let them pass. I have been around long enough to know that, and it has always worked out so far”, or “Relax, I have always been reliable and everything has always worked, right?”).
"""
}



# ---------------------------------------------------------
#  Streamlit UI & Flow Logic
# ---------------------------------------------------------

st.set_page_config(page_title="Role-Play Communication Trainer", layout="wide")

st.title("Role-Play Communication Trainer")

st.sidebar.header("Settings")

language = st.sidebar.radio("Language / Sprache", ["Deutsch", "English"])

student_id = st.sidebar.text_input(
    "Student ID or nickname",
    help="Used only to identify your sessions in the dataset.",
)

# Batch flow control: "batch1", "batch2", "finished"
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

# Determine current batch / phase
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


def format_roleplay_option(rid: int) -> str:
    rp = ROLEPLAYS[rid]
    return rp["title_en"] if language == "English" else rp["title_de"]


roleplay_id = st.selectbox(
    "Choose a role-play / Wählen Sie ein Rollenspiel",
    available_ids,
    format_func=format_roleplay_option,
)

current_rp = ROLEPLAYS[roleplay_id]

# Reset conversation if roleplay or language or batch changed
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
#  Instructions (User-facing)
# ---------------------------------------------------------

if language == "English" and current_rp.get("user_en"):
    st.subheader("Instructions for YOU")
    st.markdown(current_rp["user_en"])
else:
    st.subheader("Anweisungen für SIE")
    st.markdown(current_rp["user_de"])

with st.expander(
    "🤖 Hidden instructions for the AI partner (teacher view)"
    if language == "English"
    else "🤖 Verdeckte Anweisungen für die KI-Gesprächspartner:in (nur Lehrkraft)"
):
    if language == "English" and current_rp.get("partner_en"):
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

    system_prompt = build_system_prompt(current_rp, language)

    st.session_state.messages.append(
        {
            "role": "system",
            "content": system_prompt,
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
            label = "You" if language == "English" else "Sie"
            st.markdown(f"**{label}:** {msg['content']}")
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
#  Feedback after each role-play (Q1–Q12)
# ---------------------------------------------------------

if not st.session_state.chat_active and st.session_state.messages and not st.session_state.feedback_done:
    st.subheader("Short feedback / Kurzes Feedback")

    if language == "English":
        q1 = st.radio("The chatbot’s personality was realistic and engaging", [1, 2, 3, 4, 5], horizontal=True)
        q2 = st.radio("The chatbot seemed too robotic", [1, 2, 3, 4, 5], horizontal=True)
        q3 = st.radio("The chatbot was welcoming during initial setup", [1, 2, 3, 4, 5], horizontal=True)
        q4 = st.radio("The chatbot seemed very unfriendly", [1, 2, 3, 4, 5], horizontal=True)

        q5 = st.radio("The chatbot explained its scope and purpose well", [1, 2, 3, 4, 5], horizontal=True)
        q6 = st.radio("The chatbot gave no indication as to its purpose", [1, 2, 3, 4, 5], horizontal=True)

        q7 = st.radio("The chatbot was easy to navigate", [1, 2, 3, 4, 5], horizontal=True)
        q8 = st.radio("It would be easy to get confused when using the chatbot", [1, 2, 3, 4, 5], horizontal=True)
        q11 = st.radio("The chatbot was easy to use", [1, 2, 3, 4, 5], horizontal=True)
        q12 = st.radio("The chatbot was very complex", [1, 2, 3, 4, 5], horizontal=True)

        q9 = st.radio("The chatbot coped well with any errors or mistakes", [1, 2, 3, 4, 5], horizontal=True)
        q10 = st.radio("The chatbot seemed unable to cope with any errors", [1, 2, 3, 4, 5], horizontal=True)

        comment = st.text_area("Optional comment")
        submit_label = "Save feedback & chat"
    else:
        q1 = st.radio("Die Persönlichkeit des Chatbots war realistisch und ansprechend", [1, 2, 3, 4, 5], horizontal=True)
        q2 = st.radio("Der Chatbot wirkte zu robotisch", [1, 2, 3, 4, 5], horizontal=True)
        q3 = st.radio("Der Chatbot war beim ersten Setup einladend", [1, 2, 3, 4, 5], horizontal=True)
        q4 = st.radio("Der Chatbot wirkte sehr unfreundlich", [1, 2, 3, 4, 5], horizontal=True)

        q5 = st.radio("Der Chatbot erklärte seinen Zweck und Umfang gut", [1, 2, 3, 4, 5], horizontal=True)
        q6 = st.radio("Der Chatbot gab keinen Hinweis auf seinen Zweck", [1, 2, 3, 4, 5], horizontal=True)

        q7 = st.radio("Der Chatbot war leicht zu navigieren", [1, 2, 3, 4, 5], horizontal=True)
        q8 = st.radio("Die Nutzung des Chatbots wäre leicht verwirrend", [1, 2, 3, 4, 5], horizontal=True)
        q11 = st.radio("Der Chatbot war leicht zu bedienen", [1, 2, 3, 4, 5], horizontal=True)
        q12 = st.radio("Der Chatbot war sehr komplex", [1, 2, 3, 4, 5], horizontal=True)

        q9 = st.radio("Der Chatbot ging gut mit Fehlern oder Missverständnissen um", [1, 2, 3, 4, 5], horizontal=True)
        q10 = st.radio("Der Chatbot konnte nicht gut mit Fehlern umgehen", [1, 2, 3, 4, 5], horizontal=True)

        comment = st.text_area("Optionaler Kommentar")
        submit_label = "Feedback & Chat speichern"

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
