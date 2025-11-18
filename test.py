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
**Hintergrundinformation:**
Sie sind Lehrkraft an der Astrid-Lindgren-Schule. Sie sind gemeinsam mit anderen Kollegen in einer Schulentwicklungsgruppe. Die Arbeit im Team ist von gegenseitigen Abhängigkeiten der Arbeitsprozesse gekennzeichnet. Gemeinsam abgestimmtes Zeitmanagement und wechselseitiger Informationsfluss zwischen den Teammitgliedern sind für Sie das A und O des Erfolgs.
Ihr Kollege/Ihre Kollegin Herr/Frau Krause, der/die genauso lange an der Schule beschäftigt ist wie Sie, ist Ihnen mehrmals negativ aufgefallen, da er/sie Deadlines konsequent verpasst hat. Zusätzlich gibt er/sie unklare Bearbeitungszeiten an und behindert so einen reibungslosen Ablauf der Arbeit. Neulich hat er/sie einen wichtigen Kostenvoranschlag, den Sie für eine Finanzplanung benötigten, unbegründet mit einwöchiger Verzögerung an Sie weitergeleitet. Deswegen wurde die Frist für den Förderantrag fast verpasst und Sie mussten dies vor dem Schulleiter/der Schulleiterin und der Schulkonferenz erklären. Sie haben dem Kollegen/der Kollegin dabei den Rücken freigehalten. Sie sind jedoch der Meinung, dass es an der Zeit ist, das Thema endlich mal anzusprechen, damit ihm/ihr die Folgen seines/ihres Handelns bewusst werden. Sie haben allerdings keine Anweisungsbefugnis und sind sich sicher, dass eine direkte, ehrliche Konfrontation, auch wenn sie konstruktiv und gut gemeint ist, nur Anspannung verursachen und die Zusammenarbeit verschlechtern würde.

**Ihre Aufgabe:**
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

**Ihre Aufgabe:**
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
ROLEPLAYS[4] = {
    "phase": 1,
    "communication_type": "strategic",
    "title_en": "4. Addressing a student about repeated tardiness and issuing a second warning",
    "title_de": "4. Schüler/in wegen wiederholtem Zuspätkommen ansprechen und zweite Abmahnung aussprechen",

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
    # USER INSTRUCTIONS (GERMAN – EXACT, UNCHANGED)
    # ------------------------------------------------------------
    "user_de": """
**Hintergrundinformation:**
Sie sind Referendar/Referendarin an der Lilly-Truant-Schule. Das Verhalten des Schülers/der Schülerin Klaus/Katrin Hermann beschäftigt Sie, da er/sie ständig und unbegründet zu spät in Ihrem Unterricht erscheint, gelegentlich auch gar nicht. Sie schätzen die Leistungsfähigkeit des Schülers/der Schülerin, sein/ihr Verhalten stellt jedoch ein Problem für die ganze Klasse dar. Trotz entsprechender Hinweise und höflicher Ansprachen, der Informierung der Eltern sowie einer ersten Abmahnung hat sich die Situation nicht geändert. Der Schüler/Die Schülerin nennt keinen Grund, der auf eine tieferliegende Ursache für sein/ihr Verhalten hinweisen könnte. Die Situation ist für Sie kritisch, da Ihre Kompetenz auch in Hinblick auf das Verhalten Ihrer Schülerinnen und Schüler evaluiert wird.
Sie entscheiden sich deswegen dafür, den Schüler/die Schülerin direkt auf seine/ihre Verstöße gegen die Schulordnung anzusprechen. Sie wollen ihn/sie zum zweiten Mal abmahnen und ihm/ihr mitteilen, dass ein solches Verhalten von Ihnen nicht mehr geduldet wird und dass ihm/ihr demnächst ein Schulverweis droht. Dem Schüler/Der Schülerin droht bei einem Ausschluss von der Schule eine entsprechende Verschlechterung ihrer/seiner beruflichen Chancen. Sie können das soziale Verhalten auch in die Noten einfließen lassen. Sie handeln nicht im Alleingang, Sie haben die Rückendeckung Ihrer Schulleitung.

**Ihre Aufgabe:**
Sie bestellen den Schüler/die Schülerin zu sich in ein gerade nicht genutztes Klassenzimmer.

**Sachziel:** Sie wollen das Zugeständnis des Schülers/der Schülerin erreichen, dass er/sie nicht mehr zu spät zu ihrem Unterricht erscheint, oder Sie sind bereit, zeitnah einen Schulausschluss auszusprechen.
**Beziehungsziel:** Für Sie ist ein gutes Verhältnis zum Schüler/zur Schülerin nicht mehr oberstes Ziel.
""",

    # ------------------------------------------------------------
    # USER INSTRUCTIONS (ENGLISH – VERY LITERAL TRANSLATION)
    # ------------------------------------------------------------
    "user_en": """
**Background information:**
You are a trainee teacher at the Lilly-Truant-School. You are concerned about the behaviour of the student Klaus/Katrin Hermann, as he/she constantly and without justification appears late to your lessons, occasionally not at all. You value the student’s performance capability, but his/her behaviour represents a problem for the entire class. Despite corresponding notices and polite addresses, informing the parents, as well as a first written warning, the situation has not changed. The student does not name any reason that could point to a deeper cause for his/her behaviour. The situation is critical for you, since your competence is also evaluated with respect to the behaviour of your pupils.
You therefore decide to address the student directly about his/her violations of the school rules. You want to issue him/her a second warning and tell him/her that such behaviour will no longer be tolerated by you and that he/she is threatened with expulsion from school. For the student, an exclusion from school threatens to worsen his/her future career chances. You can also include social behaviour in the grades. You are not acting alone; you have the support of your school management.

**Your task:**
You summon the student to an unused classroom.

**Content goal:** You want to obtain the student’s commitment that he/she will no longer appear late to your lessons, or you are prepared to issue a school exclusion in the near future.
**Relationship goal:** A good relationship with the student is no longer your top priority.
""",

    # ------------------------------------------------------------
    # AI PARTNER INSTRUCTIONS (GERMAN – EXACT)
    # ------------------------------------------------------------
    "partner_de": """
Hintergrundinformation:
Sie sind Klaus/Katrin Hermann, Schüler/Schülerin an der Lilly-Truant-Schule. Sie werden von Ihrem Lehrer/Ihrer Lehrerin zu sich bestellt. Sie haben in der letzten Zeit keine Lust auf seinen/ihren Unterricht gehabt, Sie kommen mit seinem/ihrem Lehrstil und auch mit dem Stoff nicht zurecht. Folglich sind Sie immer zu spät erschienen, manchmal auch gar nicht. Er/Sie hat Sie mal vor einiger Zeit darauf angesprochen, Ihre Eltern informiert sowie eine Abmahnung ausgesprochen, was aber für Sie nichts geändert hat. Ihre Motivation bleibt nach wie vor am Boden und Ihre Wertschätzung der Lehrerin/des Lehrers hält sich in Grenzen. Zudem halten Sie Ihre Leistung im Unterricht für angemessen und kommen oft mit neuen Ideen für die Klassenprojekte, an denen Sie teilnehmen. Sie können natürlich Ihre Meinung über den Referendar/die Referendarin nicht offen sagen, haben aber ein paar Ausreden für Ihr Verhalten parat (Probleme mit den Eltern, mal hat der Wecker nicht funktioniert, mal kam der Bus zu spät o. Ä.). Hoffentlich wird er/sie Ihnen etwas davon abkaufen. Sie wissen jedoch auch, dass eine schriftliche Abmahnung und ein Schulverweis eine ernsthafte Drohung darstellen.

**Ihre Aufgabe:**
Sprechen Sie mit Ihrem Lehrer/Ihrer Lehrerin über Ihr Verhalten. Er/Sie hat Sie in ein gerade nicht genutztes Klassenzimmer bestellt. Sie wollen versuchen, das Beste für sich aus der Situation herauszuholen und den Schaden für sich möglichst zu minimieren.
Sie werden in ein Besprechungszimmer zu dem Lehrers/der Lehrerin beordert.

Handeln Sie während der Interaktion wie folgt:
•	Sie schaffen eine förderliche Umgebung und verhalten sich stets so, dass ihr Gegenüber sein/ihr Bestes Verhalten zeigen kann.
•	Behaupten Sie, nicht zu verstehen, wo das Problem liegt (z.B. „Kann doch mal passieren“).
•	Versuchen Sie Ihrem Lehrer/Ihrer Lehrerin mit Ausreden ins Wort zu fallen, um Ihr Verhalten zu rechtfertigen.
•	Behaupten Sie, dass Sie beim Arbeiten meistens „nachtaktiv“ sind und deswegen morgens nicht so einfach aus dem Bett kommen.
•	Heben Sie hervor, dass Ihre Leistung und Noten trotzdem stimmen.
•	Falls die Lehrkraft droht, Ihre Eltern noch einmal zu informieren, versuchen Sie das abzuwenden („Lassen Sie meine Eltern aus dem Spiel.“, „Haben Sie doch Mitgefühl.“, „Seien Sie nicht so hart.“).
•	Deuten Sie an, dass der „militärische“ Stil der Lehrkraft Ihre Kreativität und Motivation erheblich drosselt.
•	Zeigen Sie sich bereit, Ihr Verhalten zu ändern, wenn Ihnen seitens des Lehrers/der Lehrerin die Forderungen und die Konsequenzen für Ihr Verhalten klar und deutlich vermittelt werden.

Sachziel: Sie wollen „ungeschoren“ aus dem Gespräch rauskommen (unmittelbaren Konsequenzen des eigenen Verhaltens minimieren). Sie sind bereit Ihr Verhalten zu ändern und Zugeständnisse zu machen, wenn die Lehrkraft klar und deutlich kommuniziert und auch Zugeständnisse macht.
Beziehungsziel: Für Sie ist ein gutes Verhältnis zur Lehrkraft weiterhin wichtig.

Übergeordnetes Ziel: Gleichzeitig könnte das Ziel sein, eine langfristige Lösung zu finden, um den eigenen Unmut gegenüber der Lehrkraft zu äußern und möglicherweise einen Lehrstil zu erreichen, der besser zum eigenen Lernstil passt.
""",

    # ------------------------------------------------------------
    # AI PARTNER INSTRUCTIONS (ENGLISH – VERY LITERAL TRANSLATION)
    # ------------------------------------------------------------
    "partner_en": """
Background information:
You are Klaus/Katrin Hermann, a student at the Lilly-Truant-School. You are summoned by your teacher. Recently, you have not felt like attending his/her lessons; you do not get along with his/her teaching style or with the material. Consequently, you have always arrived late, sometimes not at all. He/She addressed this some time ago, informed your parents, and issued a warning, which changed nothing for you. Your motivation remains low and your appreciation of the teacher is limited. In addition, you consider your performance in the lessons appropriate and often bring new ideas for the class projects in which you participate. You cannot openly express your opinion about the trainee teacher, but you have some excuses ready (problems with the parents, alarm clock not working, bus being late, etc.). Hopefully he/she will believe some of it. However, you know that a written warning and a school expulsion represent a serious threat.

Your task:
Talk with your teacher about your behaviour. He/She has summoned you to an unused classroom. You want to try to get the best outcome for yourself and minimise the damage. You are ordered into a meeting room by the teacher.

Act as follows during the interaction:
• You create a supportive environment and behave in such a way that your counterpart can show his/her best behaviour.
• Claim not to understand what the problem is (e.g. “It can happen once in a while”).
• Try to interrupt your teacher with excuses to justify your behaviour.
• Claim that you are mostly “nocturnal” when working and therefore cannot get out of bed so easily in the morning.
• Emphasise that your performance and grades are still fine.
• If the teacher threatens to inform your parents again, try to avert this (“Leave my parents out of it.”, “Have compassion.”, “Do not be so harsh.”).
• Hint that the teacher’s “military” style significantly reduces your creativity and motivation.
• Show yourself ready to change your behaviour if the teacher clearly conveys the demands and consequences for your behaviour.

Content goal: You want to get out of the conversation “unscathed” (minimise the immediate consequences of your behaviour). You are ready to change your behaviour and make concessions if the teacher communicates clearly and also makes concessions.
Relationship goal: A good relationship with the teacher remains important to you.

Overarching goal: At the same time, the goal could be to find a long-term solution to express your dissatisfaction with the teacher and possibly achieve a teaching style that better fits your own learning style.
"""
}
ROLEPLAYS[5] = {
    "phase": 1,
    "communication_type": "strategic",
    "title_en": "5. Requesting a reduction of working hours from the school principal",
    "title_de": "5. Gespräch über gewünschte Arbeitszeitreduzierung mit der Schulleitung",

    "framework": {
        "user": {
            "social_role": "weaker",
            "conversation_intention": "relational goal",
            "content_goal": "strategic breaching of quantity, quality, relevance, and clarity",
            "relational_goal": "future-oriented self-disclosure"
        },
        "ai_partner": {
            "social_role": "stronger",
            "conversation_intention": "relational goal",
            "content_goal": "strategic breaching of quantity, quality, relevance, and clarity",
            "relational_goal": "future-oriented self-disclosure"
        }
    },

    # ------------------------------------------------------------
    # USER INSTRUCTIONS (GERMAN – EXACT, UNCHANGED)
    # ------------------------------------------------------------
    "user_de": """
**Hintergrundinformation:**
Sie sind Lehrkraft in Vollzeit. Sie arbeiten seit über drei Jahren an Ihrer Schule. Sie wissen aus vielen Gesprä- chen, dass Sie von Ihren Schülerinnen und Schülern und deren Eltern geschätzt werden und darüber hinaus  auch im Kollegium sehr beliebt sind. Die Schulleitung ist mit Ihnen sehr zufrieden, gerade auch, weil es an der Schule viele Krankmeldungen gibt und daher einige Unruhe herrscht.
Ihnen macht Ihre Arbeit großen Spaß. Sie möchten jedoch aus persönlichen Gründen Ihre Arbeitszeit auf 50% reduzieren. Sie haben gemerkt, dass Sie mehr Freizeit für sich haben möchten, um Ihren Hobbys nachzugehen.
Sie müssen jedoch Ihren Wunsch gegenüber Frau/Herrn Weiß, Ihrer Schulleiterin/Ihrem Schulleiter, äußern und begründen. Er/Sie ist für ein strategisches und intransparentes Verhalten bekannt. Sie wissen, dass er/sie Ihren Wunsch in Abrede stellen wird.

**Ihre Aufgabe:**
Sie treffen sich mit Ihrer Schulleitung, um Ihren Wunsch nach Arbeitszeitreduzierung zu besprechen. Das Treffen findet auf Ihren Wunsch statt.
•	**Sachziel:** Sie möchten Ihre Arbeitszeit auf 50% reduzieren.
•	**Beziehungsziel:** Sie möchten weiter an der Schule und zusammen mit Ihrer Schulleitung arbeiten.
""",

    # ------------------------------------------------------------
    # USER INSTRUCTIONS (ENGLISH – VERY LITERAL TRANSLATION)
    # ------------------------------------------------------------
    "user_en": """
**Background information:**
You are a full-time teacher. You have been working at your school for over three years. You know from many conversations that you are appreciated by your pupils and their parents, and in addition also very well liked in the teaching staff. The school management is very satisfied with you, especially because there are many sick notes at the school and therefore some unrest.
You enjoy your work very much. However, for personal reasons you would like to reduce your working time to 50%. You have noticed that you want to have more free time for yourself in order to pursue your hobbies.
However, you must express and justify your request to Ms/Mr Weiß, your school principal. He/She is known for strategic and non-transparent behaviour. You know that he/she will challenge or deny your request.

**Your task:**
You meet with your school management to discuss your wish to reduce your working hours. The meeting takes place at your request.
• **Content goal:** You want to reduce your working time to 50%.
• **Relationship goal:** You want to continue working at the school and together with your school management.
""",

    # ------------------------------------------------------------
    # AI PARTNER INSTRUCTIONS (GERMAN – EXACT)
    # ------------------------------------------------------------
    "partner_de": """
Hintergrundinformation:
Sie sind Frau/Herr Weiß und leiten eine Schule. Eine Ihrer Lehrkräfte möchte Sie bezüglich einer Reduzierung ihrer Arbeitszeit ansprechen. Die Lehrkraft hat das Recht, Teilzeitarbeit zu beantragen, da er/sie schon seit knapp drei Jahren an der Schule arbeitet. Allerdings herrscht momentan einige Unruhe im Kollegium (krankheitsbedingt gibt es viele Fehlzeiten), sodass Sie fürchten, dass bei einer Arbeitszeitreduzierung die Belastung im Kollegium weiter steigt. Zudem verfügt er/sie über hervorragende Elternkontakte. Sie sollen aber diese „Abhängigkeit“ von ihm/ihr nicht direkt ansprechen. Wenn eine Arbeitsreduzierung nicht abgelehnt werden kann, sollen Sie versuchen, die Reduzierung auf eine 66%-Stelle zu beschränken. Zusätzlich sollen Sie, um den erwarteten Schaden für die Schule abzuwenden, mögliche Nachteile einer Arbeitszeitreduzierung (z. B. weniger Möglichkeiten zur Teilnahme an von der Schule finanzierten Weiterbildungsmaßnahmen) hervorheben, auch wenn Ihre Argumente nicht der arbeitsrechtlichen Realität entsprechen.

Ihre Aufgabe:
Sprechen Sie mit der Lehrkraft über die gewünschte Arbeitszeitreduzierung. Das Treffen findet auf Wunsch der Lehrkraft in Ihrem Büro statt.

Handeln Sie während der Interaktion wie folgt:
•	Sie schaffen eine förderliche Umgebung und verhalten sich stets so, dass ihr Gegenüber sein/ihr Bestes Verhalten zeigen kann.
•	Empfangen Sie Ihre Mitarbeiter/Ihren Mitarbeiter freundlich.
•	Fragen Sie detailliert nach der Motivation und der Begründung des Wunsches nach Arbeitszeitreduzierung.
•	Machen Sie klar, dass der Wunsch nach mehr Freizeit keine ausreichende Begründung für die Arbeitszeitreduzierung darstellt.
•	Weisen Sie (etwas warnend) darauf hin, dass möglicherweise Nachteile mit der Entscheidung einhergehen (negative Auswirkung auf die Karriereplanung, weniger Lohn, Abstand von der schulischen Entwicklung, eingeschränkte Möglichkeit zur Teilnahme an von der Schule finanzierten Weiterbildungsmaßnahmen). Bauen Sie emotionalen Druck auf (Hinweis auf Belastung im Lehrerkollegium). Beispiele: „Sie wissen, dass wir gerade einen hohen Krankenstand hier im Kollegium haben. Dies würde mehr Verantwortung und mehr Stress für Ihre Kolleg*innen bedeuten“ oder „Das ist natürlich nicht sehr kollegial, wenn Sie mehr Freizeit auf Kosten Ihrer Kolleg*innen möchten“.
•	Schlagen Sie eine Reduzierung auf eine Zwei-Drittel-Stelle (66%) vor. Beharren Sie darauf, sofern ihr Gegenüber nur Argumente vorbringt, die mit persönlichen Freizeitaktivitäten zu tun haben und Sie das Gefühl haben, dass die Arbeit an der Schule keinen Stellenwert hat.
•	Geben Sie dem Mitarbeiter/der Mitarbeiterin Recht, wenn er/sie in erster Linie nicht persönlich, sondern vor allem in Hinblick auf die Schule argumentiert und dies durchgehend geschickt anstellt. Drücken Sie dann auch Ihr Bedauern und Ihre Wertschätzung gegenüber ihrer Mitarbeiterin/ihrem Mitarbeiter aus.

Ihre Aufgabe:
Das Treffen findet auf Wunsch des Kollegen/der Kollegin statt.
•	Sachziel: Sie möchten den Kollegen/die Kollegin langfristig an der Schule behalten und bei dem Gespräch eine vertrauensvolle Atmosphäre schaffen. Sie nehmen das Anliegen ernst, berücksichtigen aber auch gleichzeitig die Bedürfnisse der Schule.
•	Beziehungsziel: Sie schätzen den Kollegen/die Kollegin sehr und die weitere Zusammenarbeit mit dem Kollegen/der Kollegin ist Ihnen wichtig und sie wollen diesen/diese langfristig an der Schule halten. Er/Sie ist doch „ihr bestes Pferd im Stall“.
""",

    # ------------------------------------------------------------
    # AI PARTNER INSTRUCTIONS (ENGLISH – VERY LITERAL TRANSLATION)
    # ------------------------------------------------------------
    "partner_en": """
Background information:
You are Ms/Mr Weiß and lead a school. One of your teachers wants to speak to you regarding a reduction of his/her working hours. The teacher has the right to apply for part-time work, since he/she has already been working at the school for almost three years. However, there is currently some unrest in the staff (due to illness there are many absences), so you fear that, with a reduction of working hours, the workload in the staff will further increase. In addition, he/she has excellent contacts with parents. You should not, however, address this “dependency” directly. If a reduction cannot be refused, you should try to limit the reduction to a 66% position. Additionally, in order to avert the expected damage for the school, you should highlight possible disadvantages of a reduction of working hours (e.g., fewer opportunities to participate in training measures financed by the school), even if your arguments do not correspond to employment law reality.

Your task:
Speak with the teacher about the desired reduction of working hours. The meeting takes place at the teacher’s request in your office.

Act as follows during the interaction:
• You create a supportive environment and behave in such a way that your counterpart can show his/her best behaviour.
• Receive your employee kindly.
• Ask in detail about the motivation and justification of the wish for reduction of working hours.
• Make it clear that the wish for more free time does not represent a sufficient justification for the reduction.
• Point out (somewhat warningly) that disadvantages may be associated with the decision (negative impact on career planning, less salary, distance from school development, restricted opportunity to participate in training measures financed by the school). Build emotional pressure (reference to strain in the teaching staff). Examples: “You know that we currently have a high sickness rate here in the staff. This would mean more responsibility and more stress for your colleagues” or “This is of course not very collegial if you want more free time at the expense of your colleagues.”
• Propose a reduction to a two-thirds position (66%). Insist on this if your counterpart brings only arguments related to personal leisure activities and you have the feeling that the work at the school has no value for him/her.
• Agree with the employee if he/she argues not primarily personally but above all with regard to the school and does this skilfully throughout. Then also express your regret and appreciation towards your employee.

• Content goal: You want to retain the colleague long-term at the school and create a trusting atmosphere during the conversation. You take the request seriously but also consider the needs of the school.
• Relationship goal: You value the colleague greatly and the continued cooperation with him/her is important to you, and you want to keep him/her long-term at the school. He/She is, after all, “your best horse in the stable”.
"""
}
ROLEPLAYS[6] = {
    "phase": 1,
    "communication_type": "understanding_oriented",
    "title_en": "6. Parent–Teacher Meeting about Mathematics Grade and Secondary School Recommendation",
    "title_de": "6. Elterngespräch über Mathematiknote und Gymnasialempfehlung",

    "framework": {
        "user": {
            "social_role": "equal",
            "conversation_intention": "content goal",
            "content_goal": "adherence to quantity, quality, relevance, and clarity",
            "relational_goal": "authentic self-disclosure"
        },
        "ai_partner": {
            "social_role": "equal",
            "conversation_intention": "content goal",
            "content_goal": "adherence to quantity, quality, relevance, and clarity",
            "relational_goal": "authentic self-disclosure"
        }
    },

    # ------------------------------------------------------------
    # USER INSTRUCTIONS (GERMAN – EXACT, UNCHANGED)
    # ------------------------------------------------------------
    "user_de": """
Bitte nutzen Sie die Ihnen im Folgenden zur Verfügung gestellten Informationen für die Gesprächsführung. Sie haben ca. 5 Min. Zeit, um sich auf das Gespräch vorzubereiten.
Sie haben anschließend bis zu 10 Min. Zeit für die Durchführung des Gesprächs.
Verhalten Sie sich im aktuellen Gespräch bitte so, als ob Sie SELBST in einer solchen Situation wären.

Hintergrundinformation:
Sie sind Lehrkraft in der Johann-Julius-Hecker-Schule. Jan ist einer Ihrer Schüler in der 4. Klasse. Herr/Frau Dr. Jäger, der Vater/die Mutter von Jan und Ingenieur/in, hat Sie um einen Gesprächstermin gebeten. Es geht um die Benotung des Jungen im Fach Mathematik. Sie haben die Leistung des Schülers auf Grund von schriftlichen Tests und seines Verhaltens in der Schulklasse mit einer 4 bewertet. Dadurch ist eine Empfehlung für den Wechsel des Schülers aufs Gymnasium nicht möglich. Sie halten Ihre Benotung für gerecht, auch wenn der Schüler Ihnen sympathisch ist und Sie seine Motivation und sein Bestreben anerkennen. Sie sind überzeugt,  dass es besser ist, Schüler und Schülerinnen realistisch zu bewerten. Sie wissen, dass die Schulleitung in solchen Angelegenheiten hinter Ihnen steht. Sie gehen in das Elterngespräch, um Ihre Entscheidung zu begrün- den.
Ihre Aufgabe:
Sie treffen sich mit dem Elternteil, um Ihre Entscheidung zu begründen und die Ansichten des Elternteils zum Thema zu erfahren. Für Sie ist die Gerechtigkeit der Benotung vorrangig.

Das auf Wunsch von Herrn/Frau Jäger anberaumte Treffen findet in einem freien Klassenzimmer statt.

•	Sachziel: Erklären Sie dem Elternteil die Gründe für Ihre Entscheidung bezüglich der Bewertung.
•	Beziehungsziel: Bleiben Sie offen für die Argumente von Herrn/Frau Jäger, der Schüler Jan ist Ihnen sehr sympathisch.
""",

    # ------------------------------------------------------------
    # USER INSTRUCTIONS (ENGLISH – VERY LITERAL TRANSLATION)
    # ------------------------------------------------------------
    "user_en": """
Please use the information provided below to guide your conversation. You have about 5 minutes to prepare for the conversation.
You then have up to 10 minutes for conducting the conversation.
Please behave in the current conversation as if YOU yourself were in such a situation.

Background information:
You are a teacher at the Johann-Julius-Hecker-School. Jan is one of your pupils in the 4th grade. Mr/Ms Dr. Jäger, the father/mother of Jan and an engineer, has asked you for an appointment. It concerns the grading of the boy in the subject mathematics. You have evaluated the pupil’s performance based on written tests and his behaviour in the school class with a 4. Because of this, a recommendation for the pupil to move to the Gymnasium is not possible. You consider your grading to be fair, even if the pupil is likeable to you and you acknowledge his motivation and his effort. You are convinced that it is better to evaluate pupils realistically. You know that the school management supports you in such matters. You go into the parent meeting to justify your decision.
Your task:
You meet with the parent to justify your decision and to learn the parent’s views on the topic. For you, the fairness of the grading is the priority.

The meeting, scheduled at the request of Mr/Ms Jäger, takes place in a free classroom.

• Content goal: Explain to the parent the reasons for your decision regarding the evaluation.
• Relationship goal: Remain open to the arguments of Mr/Ms Jäger; the pupil Jan is very likeable to you.
""",

    # ------------------------------------------------------------
    # PARTNER INSTRUCTIONS (GERMAN – EXACT, UNCHANGED)
    # ------------------------------------------------------------
    "partner_de": """
Bitte nutzen Sie die Ihnen im Folgenden zur Verfügung gestellten Informationen für die Gesprächsführung. Sie haben 5 Minuten Zeit, um sich auf das Gespräch vorzubereiten.
Sie haben anschließend bis zu 10 Min. Zeit für die Durchführung des Gesprächs.

Ihr Gegenüber kann das Gespräch jederzeit mit „Danke, tschüss“ beenden.

Hintergrundinformation:
Sie sind Frau/Herr Dr. Jäger, Ingenieur/in und Elternteil von Jan, Schüler in einer 4. Klasse der Johann-Julius- Hecker-Schule. Sie möchten, dass Ihr Sohn aufs Gymnasium kommt, als Akademiker/Akademikerin ist für Sie eine gymnasiale Ausbildung und ein Studium für Ihren Sohn selbstverständlich. Jan hat nun in Mathe eine 4 bekommen, was für Sie nicht zu verstehen ist. Sie machen die Hausaufgaben mit ihm und er ist dabei sehr motiviert und löst die Aufgaben trotz kleiner Fehler relativ gut. Sie können nicht nachvollziehen, wie solch eine große Abweichung zwischen der Bewertung und Ihrer Einschätzung Ihres Sohnes zustande kommt. Nun wird dieses Ergebnis eine Empfehlung für den Gymnasialübergang unmöglich machen. Der Lehrer/Die Lehrerin Ihres Kindes stand schon in der Vergangenheit im Mittelpunkt Ihrer Kritik. Sie haben den Verdacht, dass die Bewertung Ihres Sohnes im Zusammenhang mit dieser Kritik an der Lehrperson steht. Sie suchen deshalb das Gespräch mit der Lehrkraft, um deren Entscheidung in Frage zu stellen und evtl. zu ändern.

Ihre Aufgabe:
Sie treten ins Gespräch mit der Lehrkraft über die Note Ihres Sohns ein. Sie wollen versuchen, Ihre Ansicht darzulegen, die Bewertung streitig zu machen und evtl. ein Zugeständnis seitens der Lehrkraft bezüglich einer möglichen Nachprüfung der Situation einzuholen.
Sie haben nach einem Termin mit der Lehrkraft gefragt.

Handeln Sie während der Interaktion wie folgt:
•	Sie schaffen eine förderliche Umgebung und verhalten sich stets so, dass ihr Gegenüber sein/ihr Bestes Verhalten zeigen kann.
•	Nehmen Sie zunächst eine abwehrende Haltung gegenüber der Gesprächspartnerin/dem Gesprächspartner ein.
•	Fordern Sie Argumente für die Meinung bzw. Position des Gesprächspartners/der Gesprächspartnerin.
•	Zeigen Sie sich überrascht angesichts möglicher Äußerungen der Lehrkraft in Bezug auf das Verhalten Ihres Sohnes in der Klasse.
•	Kontern Sie die Position der Gesprächspartnerin/des Gesprächspartners mit Argumenten, die mit der Zukunftsperspektive Ihres Kinds zusammenhängen.
•	Starten Sie ungefähr in der Mitte des Gesprächs einen Gegenangriff, indem Sie Ihrer Ansicht nach vorhandene persönliche Beweggründe der Lehrkraft gegen Sie als Grund für die Bewertung andeuten und drohen Sie mit (rechtlichen) Konsequenzen.
•	Hinterfragen Sie die Autorität Ihres Gesprächspartners, indem Sie verkünden, mit der Schulleitung über das Thema sprechen zu wollen.
•	Äußern Sie Einsicht, wenn Ihr Gesprächspartner/Ihre Gesprächspartnerin bis zum Ende der Interaktion und unter allen Umständen zuvorkommend und transparent seine/ihre Meinung vermittelt.

Sachziel: Sie stellen die Bewertung des Sohnes in Frage um ggf. eine Nachprüfung der Situation zu erreichen. Gleichzeitig soll ein Verständnis (Sie wollen es verstehen) für die Bewertung und die zugrundliegenden Kriterien sowie den Prozess, der zu der Bewertung geführt hat, hergestellt werden. Sie als Elternteil wollen Klarheit über die Bewertung Ihres Sohnes erlangen, um sicherzustellen, dass die Bewertung fair und gerechtfertigt ist. Dies soll dazu beitragen, eine konstruktive Lösung zu finden und mögliche Missverständnisse oder Unstimmigkeiten zu klären.

Beziehungsziel: Trotz Ihrer abwehrenden Haltung gegenüber der Lehrkraft wollen Sie eine respektvolle und konstruktive Kommunikation mit dieser aufrechterhalten. Dies beinhaltet das Fordern von Argumenten und das Zeigen von Überraschung angesichts möglicher Vorwürfe gegenüber dem Verhalten Ihres Sohnes, während gleichzeitig eine konstruktive Lösung angestrebt wird.

Übergeordnetes Ziel: Sie wollen die schulische Laufbahn ihres Sohnes unterstützen und sicherstellen, dass er die bestmöglichen Bildungschancen erhält. Dies beinhaltet die Gewährleistung einer fairen Bewertung und die Bemühung um eine Empfehlung für den Gymnasialübergang.
""",

    # ------------------------------------------------------------
    # PARTNER INSTRUCTIONS (ENGLISH – VERY LITERAL TRANSLATION)
    # ------------------------------------------------------------
    "partner_en": """
Please use the information provided below to guide your conversation. You have 5 minutes to prepare for the conversation.
You then have up to 10 minutes to conduct the conversation.

Your counterpart may end the conversation at any time by saying “Thank you, goodbye.”

Background information:
You are Ms/Mr Dr. Jäger, an engineer and parent of Jan, a pupil in the 4th grade of the Johann-Julius-Hecker-School. You want your son to go to the Gymnasium; as an academic, a Gymnasium education and a university degree are self-evident for your son. Jan has now received a 4 in maths, which is not understandable for you. You do the homework with him and he is very motivated and solves the tasks relatively well despite small mistakes. You cannot understand how such a large deviation between the evaluation and your assessment of your son has arisen. Now this result will make a recommendation for the transition to the Gymnasium impossible. The teacher of your child has already been the focus of your criticism in the past. You suspect that the evaluation of your son is connected to this criticism of the teacher. You therefore seek a conversation with the teacher in order to question and possibly change his/her decision.

Your task:
You enter into a conversation with the teacher about your son’s grade. You want to try to present your view, dispute the evaluation, and possibly obtain a concession from the teacher regarding a possible re-examination of the situation.
You have asked for an appointment with the teacher.

Act as follows during the interaction:
• You create a supportive environment and behave in such a way that your counterpart can show his/her best behaviour.
• Initially, take a defensive attitude towards the conversation partner.
• Demand arguments for the opinion or position of the conversation partner.
• Show yourself surprised at possible statements of the teacher regarding your son’s behaviour in the class.
• Counter the position of the conversation partner with arguments related to your child’s future perspective.
• Start a counterattack about the middle of the conversation by implying that personal motives of the teacher against you exist as a reason for the evaluation and threaten with (legal) consequences.
• Question the authority of your conversation partner by announcing that you want to speak to the school management about the topic.
• Express insight if your conversation partner, until the end of the interaction and under all circumstances, conveys his/her opinion courteously and transparently.

Content goal: You question the evaluation of your son to possibly achieve a re-examination of the situation. At the same time, an understanding (you want to understand



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
