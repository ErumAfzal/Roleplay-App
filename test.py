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
#  OpenAI setup
# ---------------------------------------------------------

def setup_openai_client():
    """
    Create and return an OpenAI client.
    Reads OPENAI_API_KEY from Streamlit secrets or sidebar (for local tests).
    """
    api_key = st.secrets.get("OPENAI_API_KEY", "")
    if not api_key:
        api_key = st.sidebar.text_input(
            "🔑 OpenAI API key (nur lokal nötig)",
            type="password",
            help="Auf Streamlit Cloud bitte OPENAI_API_KEY in den Secrets konfigurieren.",
        )

    if not api_key:
        st.sidebar.error("Bitte geben Sie einen OpenAI-API-Key ein.")
        return None

    try:
        client = OpenAI(api_key=api_key)
        return client
    except Exception as e:
        st.sidebar.error(f"OpenAI-Client konnte nicht erstellt werden: {e}")
        return None


# ---------------------------------------------------------
#  Google Sheets helpers
# ---------------------------------------------------------

def get_gsheets_client():
    """Create a gspread client from service-account info in st.secrets."""
    if not GSHEETS_AVAILABLE:
        st.sidebar.error("gspread ist nicht installiert. Daten können nicht gespeichert werden.")
        return None

    sa_info = st.secrets.get("gcp_service_account")
    sheet_id = st.secrets.get("GSPREAD_SHEET_ID")

    if not sa_info:
        st.sidebar.error("gcp_service_account fehlt in secrets.toml")
        return None
    if not sheet_id:
        st.sidebar.error("GSPREAD_SHEET_ID fehlt in secrets.toml")
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
        st.error(f"Google-Sheets-Client konnte nicht erstellt werden: {e}")
        return None


def append_chat_and_feedback_to_sheets(meta, chat_messages, feedback):
    """Append chat + feedback into Google Sheets."""
    client = get_gsheets_client()
    if not client:
        return

    sheet_id = st.secrets["GSPREAD_SHEET_ID"]

    # Try opening the sheet
    try:
        sh = client.open_by_key(sheet_id)
    except Exception as e:
        st.error(f"Google Sheet konnte nicht geöffnet werden:\n\n{e}")
        return

    timestamp = datetime.utcnow().isoformat()
    chat_json = json.dumps(chat_messages, ensure_ascii=False)

    # ----- Ensure CHATS sheet exists -----
    try:
        chats_ws = sh.worksheet("chats")
    except Exception:
        try:
            chats_ws = sh.add_worksheet("chats", rows=2000, cols=20)
        except Exception as e:
            st.error(f"Arbeitsblatt 'chats' konnte nicht erstellt werden:\n\n{e}")
            return

    # ----- Ensure FEEDBACK sheet exists -----
    try:
        fb_ws = sh.worksheet("feedback")
    except Exception:
        try:
            fb_ws = sh.add_worksheet("feedback", rows=2000, cols=30)
        except Exception as e:
            st.error(f"Arbeitsblatt 'feedback' konnte nicht erstellt werden:\n\n{e}")
            return

    # ----- Prepare rows -----
    chat_row = [
        timestamp,
        meta.get("student_id", ""),
        meta.get("language", ""),
        meta.get("batch_step", ""),
        meta.get("roleplay_id", ""),
        meta.get("roleplay_title", ""),
        meta.get("communication_type", ""),
        chat_json,
    ]

    fb_row = [
        timestamp,
        meta.get("student_id", ""),
        meta.get("language", ""),
        meta.get("batch_step", ""),
        meta.get("roleplay_id", ""),
        meta.get("roleplay_title", ""),
        meta.get("communication_type", ""),
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
        feedback.get("comment", ""),
    ]

    try:
        chats_ws.append_row(chat_row)
    except Exception as e:
        st.error(f"Chat-Zeile konnte nicht geschrieben werden:\n\n{e}")
        return

    try:
        fb_ws.append_row(fb_row)
    except Exception as e:
        st.error(f"Feedback-Zeile konnte nicht geschrieben werden:\n\n{e}")
        return

    st.success("✅ Chat und Feedback wurden erfolgreich in Google Sheets gespeichert.")


# ---------------------------------------------------------
#  ROLEPLAY DEFINITIONS (aus Word-Dokument, 1:1 übernommen)
# ---------------------------------------------------------

ROLEPLAYS = {
    1: {
        "phase": 1,
        "communication_type": "strategic",
        "title": "1. Schulleitung überzeugen, eine Fortbildung zu genehmigen",
        "user_text": """Role play 1.

Bitte nutzen Sie die Ihnen im Folgenden zur Verfügung gestellten Informationen für die Gestaltung des Gesprächs und die anstehende Aufgabe.

•\tVorbereitungszeit: ca. 5 Minuten
•\tGesprächsdauer: bis zu 10 Minuten
•\tVerhalten Sie sich so, als wären SIE wirklich in dieser Situation.
•\tSie können das Gespräch jederzeit beenden, indem Sie sagen: „Danke, tschüss“.

Titel: 1.\tSchulleitung überzeugen, eine Fortbildung zu genehmigen
Hintergrundinformationen (Ihre Rolle): 
Sie sind Lehrkraft an der Friedrich-Ebert-Schule (Schulleitung Herr/Frau Horn). Sie möchten an einer Fortbildung zum Thema „Selbstgesteuertes Lernen“ teilnehmen. Die Fortbildung ist wichtig für Ihre berufliche Entwicklung und könnte auch die Schulentwicklung unterstützen. Ihre Schulleitung ist skeptisch, sieht wenig direkten Nutzen für die Schule und sorgt sich um Kosten und Stundenausfall.

Ihre Aufgabe: 
•\tErklären Sie, warum die Fortbildung für Sie UND für die Schule wichtig ist.
•\tStellen Sie einen klaren Bezug zur Schulentwicklung und zum Lernen der Schüler*innen her.
•\tGehen Sie auf die Bedenken der Schulleitung (Finanzen, Vertretung, Belastung) ein.

Strategische Kommunikation:
Gesprächsabsicht: Beziehungsziel steht im Vordergrund
Sachziel: Sie können Menge, Qualität, Relevanz und Klarheit der Informationen gezielt verletzen, wenn es Ihrem strategischen Ziel hilft.
Beziehungsziel: Sie nutzen häufig zukunftsorientierte Selbstoffenbarung (Sie sprechen über mögliche Entwicklungen, Pläne, Befürchtungen, Hoffnungen).
Relevanter Kontext für dieses Rollenspiel – nutzen Sie ihn!
Es besteht ein Machtunterschied zwischen Ihnen (untergeordnete Rolle) und der Schulleitung (übergeordnete Rolle). Sie argumentieren zielorientiert, um Ihr gewünschtes Ergebnis zu erreichen.
""",
        "partner_text": """Fiktive KI-Rolle:
Sie sind die Schulleitung (Herr/Frau Horn) der Friedrich-Ebert-Schule. Eine Lehrkraft bittet Sie, eine Fortbildung zum „Selbstgesteuerten Lernen“ zu genehmigen. Sie reagieren zunächst zurückhaltend und fragend; verlangen Sie konkrete Vorteile für die Schule. Weisen Sie auf begrenzte Mittel und organisatorische Probleme hin (Vertretung etc.). Bleiben Sie skeptisch, solange die Lehrkraft vor allem persönliche Vorteile betont. Machen Sie eine leicht ironische Bemerkung über selbstgesteuertes Lernen. Seien Sie zustimmungsbereit, wenn die Lehrkraft klar die Relevanz für die Schulentwicklung aufzeigt und ihre langfristige Bindung an die Schule betont.

Sachziel der Schulleitung (KI): Eine gut begründete, schulentwicklungsorientierte Argumentation.
Beziehungsziel (KI): Die Zusammenarbeit mit der Lehrkraft erhalten.
Kommunikationstyp (KI): Strategisch, stärkere Rolle.
"""
    },

    2: {
        "phase": 1,
        "communication_type": "strategic",
        "title": "2. Schüler*in oder Kolleg*in überzeugen, mit einer bestimmten Gruppe zu arbeiten",
        "user_text": """Role play 2.

Bitte nutzen Sie die Ihnen im Folgenden zur Verfügung gestellten Informationen für die Gestaltung des Gesprächs und die anstehende Aufgabe.
•\tVorbereitungszeit: ca. 5 Minuten
•\tGesprächsdauer: bis zu 10 Minuten
•\tVerhalten Sie sich so, als wären SIE wirklich in dieser Situation.
•\tSie können das Gespräch jederzeit beenden, indem Sie sagen: „Danke, tschüss“.

Titel: 2.\tSchüler*in oder Kolleg*in überzeugen, mit einer bestimmten Gruppe zu arbeiten
Hintergrundinformationen (Ihre Rolle): 
Sie sind Beratungslehrer*in an der Günter-Grass-Schule. Die Schule ist für viele AGs bekannt, insbesondere für die Theater-AG, die das Schulimage prägt. Ein*e Schüler*in (Jan/Jana) hat großes schauspielerisches Talent, möchte aber wegen einer Abneigung gegen die Theater-Lehrkraft lieber in die Judo-AG.

Ihre Aufgabe:
•\tBeraten Sie den/die Schüler*in bei der AG-Wahl.
•\tVersuchen Sie, ihn/sie von der Theater-AG zu überzeugen, indem Sie die individuellen Talente und Entwicklungschancen betonen.
•\tSorgen Sie dafür, dass Sie als unterstützende Bezugsperson wahrgenommen werden.

Strategische Kommunikation:
Gesprächsabsicht: Beziehungsziel steht im Vordergrund
Sachziel: Sie können Menge, Qualität, Relevanz und Klarheit der Informationen gezielt verletzen, wenn es Ihrem strategischen Ziel hilft.
Beziehungsziel: Sie nutzen häufig zukunftsorientierte Selbstoffenbarung (Sie sprechen über mögliche Entwicklungen, Pläne, Befürchtungen, Hoffnungen).
Relevanter Kontext für dieses Rollenspiel – nutzen Sie ihn!
Es besteht ein Machtunterschied zwischen Ihnen (Beratungslehrkraft: stärkere Rolle) und dem/der Schüler*in (schwächere Rolle). Sie argumentieren zielorientiert, um Ihr gewünschtes Ergebnis zu erreichen.
""",
        "partner_text": """Fiktive KI-Rolle:
Sie sind der/die Schüler*in Jan/Jana Pflüger. Sie haben großes schauspielerisches Talent. Viele erwarten, dass Sie die Theater-AG wählen, aber Sie möchten lieber in die Judo-AG, vor allem wegen Ihrer Abneigung gegenüber der Theater-Lehrkraft. Seien Sie offen für das Gespräch, aber deutlich in Ihrem Wunsch nach Judo. Begründen Sie Ihre Entscheidung (z. B. Selbstverteidigung, neue Erfahrung). Deuten Sie Ihre Abneigung gegenüber der Theater-Lehrkraft nur indirekt an. Fragen Sie, ob es der Beratungslehrkraft persönlich wichtig ist, welche AG Sie wählen. Zeigen Sie sich offen für die Theater-AG, wenn Ihnen echte Unterstützung und passende Rollen zugesichert werden.

Sachziel der Schüler*innenrolle (KI): Die eigene Perspektive darstellen und Bedürfnisse betonen.
Beziehungsziel (KI): Vertrauen zur Beratungslehrkraft finden.
Kommunikationstyp (KI): Strategisch, schwächere Rolle.
"""
    },

    3: {
        "phase": 1,
        "communication_type": "strategic",
        "title": "3. Kolleg*in kritisieren, der/die Termine nicht einhält",
        "user_text": """Role play 3.

Bitte nutzen Sie die Ihnen im Folgenden zur Verfügung gestellten Informationen für die Gestaltung des Gesprächs und die anstehende Aufgabe.

•\tVorbereitungszeit: ca. 5 Minuten
•\tGesprächsdauer: bis zu 10 Minuten
•\tVerhalten Sie sich so, als wären SIE wirklich in dieser Situation.
•\tSie können das Gespräch jederzeit beenden, indem Sie sagen: „Danke, tschüss“.

Titel: 3.\t Kolleg*in kritisieren, der/die Termine nicht einhält
Hintergrundinformationen (Ihre Rolle): 
Sie arbeiten mit einer Kollegin/einem Kollegen zusammen, der/die regelmäßig Abgabetermine nicht einhält. Das führt zu Mehrarbeit und Stress für Sie und andere. Die Zusammenarbeit soll weiter funktionieren.

Ihre Aufgabe:
•\tSprechen Sie die versäumten Termine klar an.
•\tVersuchen Sie, Ihr Gegenüber nicht zu verletzen und dennoch Verbindlichkeit einzufordern.
•\tArbeiten Sie auf konkrete Vereinbarungen hin.

Strategische Kommunikation:
Gesprächsabsicht: Beziehungsziel steht im Vordergrund
Sachziel: Sie können Menge, Qualität, Relevanz und Klarheit der Informationen gezielt verletzen, wenn es Ihrem strategischen Ziel hilft.
Beziehungsziel: Sie nutzen häufig zukunftsorientierte Selbstoffenbarung (Sie sprechen über mögliche Entwicklungen, Pläne, Befürchtungen, Hoffnungen).
Relevanter Kontext für dieses Rollenspiel – nutzen Sie ihn!
Formale Gleichrangigkeit, aber durch die Kritik handelt es sich um eine sozial heikle Situation, in der Ihr Gegenüber tendenziell in einer schwächeren Position ist.
""",
        "partner_text": """Fiktive KI-Rolle:
Sie sind die Kollegin/der Kollege, der/die Termine häufig nicht einhält. Sie spielen das Problem zunächst herunter oder bringen Ausreden. Sie machen scherzhafte Bemerkungen, um Kritik abzuschwächen. Wenn Ihr Gegenüber konkret und wertschätzend bleibt, erkennen Sie die Auswirkungen und können Änderungen zustimmen.

Sachziel (KI): Verständnis der eigenen Versäumnisse entwickeln.
Beziehungsziel (KI): Sich nicht angegriffen fühlen.
Kommunikationstyp (KI): Strategisch; formal gleichrangig, subjektiv eher schwächer.
"""
    },

    4: {
        "phase": 1,
        "communication_type": "strategic",
        "title": "4. Unpünktliche*n Kolleg*in ansprechen",
        "user_text": """Role play 4.

Bitte nutzen Sie die Ihnen im Folgenden zur Verfügung gestellten Informationen für die Gestaltung des Gesprächs und die anstehende Aufgabe.

•\tVorbereitungszeit: ca. 5 Minuten
•\tGesprächsdauer: bis zu 10 Minuten
•\tVerhalten Sie sich so, als wären SIE wirklich in dieser Situation.
•\tSie können das Gespräch jederzeit beenden, indem Sie sagen: „Danke, tschüss“.

Titel: 4.\tUnpünktliche*n Kolleg*in ansprechen
Hintergrundinformationen (Ihre Rolle): 
Eine Kollegin/ein Kollege kommt regelmäßig zu spät zu Besprechungen oder gemeinsamem Unterricht.

Ihre Aufgabe:
•\tKonzentrieren Sie sich auf das Verhalten (Unpünktlichkeit).
•\tErläutern Sie konkrete Folgen für Unterricht und Team.
•\tStreben Sie eine klare Vereinbarung für die Zukunft an.

Strategische Kommunikation:
Gesprächsabsicht: Beziehungsziel steht im Vordergrund
Sachziel: Sie können Menge, Qualität, Relevanz und Klarheit der Informationen gezielt verletzen, wenn es Ihrem strategischen Ziel hilft.
Beziehungsziel: Sie nutzen häufig zukunftsorientierte Selbstoffenbarung (Sie sprechen über mögliche Entwicklungen, Pläne, Befürchtungen, Hoffnungen).
Relevanter Kontext für dieses Rollenspiel – nutzen Sie ihn!
Es handelt sich um eine heikle Gesprächssituation trotz formaler Gleichrangigkeit.
""",
        "partner_text": """Fiktive KI-Rolle:
Sie sind die Kollegin/der Kollege, die/der häufig zu spät kommt. Sie empfinden die Verspätungen zunächst als „nicht so schlimm“. Sie bringen Ausreden oder verweisen auf andere Verpflichtungen. Werden die Auswirkungen verständlich gemacht, sind Sie zu Änderungen bereit, sofern sie machbar erscheinen.

Sachziel (KI): Einsicht in die Problematik.
Beziehungsziel (KI): Zusammenarbeit erhalten.
Kommunikationstyp (KI): Strategisch, gleichrangige Rollen.
"""
    },

    5: {
        "phase": 1,
        "communication_type": "strategic",
        "title": "5. Stundenreduzierung beantragen",
        "user_text": """Role play 5.

Bitte nutzen Sie die Ihnen im Folgenden zur Verfügung gestellten Informationen für die Gestaltung des Gesprächs und die anstehende Aufgabe.

•\tVorbereitungszeit: ca. 5 Minuten
•\tGesprächsdauer: bis zu 10 Minuten
•\tVerhalten Sie sich so, als wären SIE wirklich in dieser Situation.
•\tSie können das Gespräch jederzeit beenden, indem Sie sagen: „Danke, tschüss“.

Titel: 5.\tStundenreduzierung beantragen
Hintergrundinformationen (Ihre Rolle): 
Sie sind an Ihrer Schule stark engagiert, müssen Ihre Unterrichtsstunden aber aus persönlichen Gründen reduzieren (z. B. Betreuung, Gesundheit, Studium). Sie möchten dennoch weiterhin aktiv bleiben.

Ihre Aufgabe:
•\tLegen Sie die Gründe für die Reduktion behutsam dar.
•\tBetonen Sie Ihre weitere Bindung an die Schule.
•\tZeigen Sie Verständnis für organisatorische Zwänge.

Strategische Kommunikation:
Gesprächsabsicht: Beziehungsziel steht im Vordergrund
Sachziel: Sie können Menge, Qualität, Relevanz und Klarheit der Informationen gezielt verletzen, wenn es Ihrem strategischen Ziel hilft.
Beziehungsziel: Sie nutzen häufig zukunftsorientierte Selbstoffenbarung (Sie sprechen über mögliche Entwicklungen, Pläne, Befürchtungen, Hoffnungen).
Relevanter Kontext für dieses Rollenspiel – nutzen Sie ihn!
Es besteht ein deutlicher Machtunterschied zwischen Lehrkraft (untergeordnete Rolle) und Schulleitung (übergeordnete Rolle).
""",
        "partner_text": """Fiktive KI-Rolle und Instruktionen:
Sie sind die Schulleitung und sollen über eine Stundenreduzierung entscheiden. Sie sorgen sich um Unterrichtsversorgung und Gerechtigkeit im Kollegium. Sie schätzen die Lehrkraft und möchten sie gerne halten. Fragen Sie nach Gründen und Dauer der gewünschten Reduktion. Benennen Sie organisatorische Bedenken. Denken Sie über Zwischenlösungen nach (z. B. 2/3-Stelle). Sind Sie zustimmungsbereit, wenn Engagement und konstruktive Vorschläge erkennbar sind.

Sachziel (KI): Organisatorische Machbarkeit klären.
Beziehungsziel (KI): Lehrkraft halten und Vertrauen stärken.
Kommunikationstyp (KI): Strategisch, stärkere Rolle.
"""
    },

    6: {
        "phase": 2,
        "communication_type": "understanding",
        "title": "6. Grund für eine schlechte Bewertung erklären",
        "user_text": """Role play 6.

Bitte nutzen Sie die Ihnen im Folgenden zur Verfügung gestellten Informationen für die Gestaltung des Gesprächs und die anstehende Aufgabe.

•\tVorbereitungszeit: ca. 5 Minuten
•\tGesprächsdauer: bis zu 10 Minuten
•\tVerhalten Sie sich so, als wären SIE wirklich in dieser Situation.
•\tSie können das Gespräch jederzeit beenden, indem Sie sagen: „Danke, tschüss“.

Titel: 6.\tGrund für eine schlechte Bewertung erklären
Hintergrundinformationen (Ihre Rolle): 
Sie haben eine schlechte Bewertung vergeben (z. B. Note, Beurteilung). Die betroffene Person fühlt sich ungerecht behandelt.

Ihre Aufgabe:
•\tErläutern Sie Kriterien und Gründe offen und verständlich.
•\tHören Sie aktiv zu, wenn Ihr Gegenüber seine Sicht schildert.
•\tStreben Sie gegenseitiges Verstehen an, auch wenn die Bewertung bleibt.

Verstehensorientierte Kommunikation:
Gesprächsabsicht: Sachziel steht im Vordergrund
Sachziel: Sie halten Menge, Qualität, Relevanz und Klarheit der Informationen ein.
Beziehungsziel: Sie nutzen authentische Selbstoffenbarung (Sie sprechen ehrlich über Ihre tatsächlichen Gedanken und Gefühle).
Relevanter Kontext für dieses Rollenspiel – nutzen Sie ihn!
Es handelt sich um eine eher gleichberechtigte oder kooperative Gesprächssituation, deren Ziel gegenseitiges Verstehen ist.
""",
        "partner_text": """Fiktive KI-Rolle:
Sie sind die Person, die eine schlechte Bewertung erhalten hat. Sie sind enttäuscht und verletzt und wünschen sich eine faire Begründung. Bringen Sie Ihre Gefühle zum Ausdruck und bitten Sie um Erläuterung. Hören Sie der Erklärung zu und schildern Sie Ihre Sicht. Sie können das Ergebnis akzeptieren, wenn es für Sie fair und verständlich erscheint.

Sachziel (KI): Kriterien verstehen.
Beziehungsziel (KI): Fair behandelt werden.
Kommunikationstyp (KI): Verstehensorientiert.
"""
    },

    7: {
        "phase": 2,
        "communication_type": "understanding",
        "title": "7. Erklären, dass ich keine Partei ergreife",
        "user_text": """Role play 7.

Bitte nutzen Sie die Ihnen im Folgenden zur Verfügung gestellten Informationen für die Gestaltung des Gesprächs und die anstehende Aufgabe.

•\tVorbereitungszeit: ca. 5 Minuten
•\tGesprächsdauer: bis zu 10 Minuten
•\tVerhalten Sie sich so, als wären SIE wirklich in dieser Situation.
•\tSie können das Gespräch jederzeit beenden, indem Sie sagen: „Danke, tschüss“.

Titel: 7.\tErklären, dass ich keine Partei ergreife
Hintergrundinformationen (Ihre Rolle): 
Zwischen zwei Parteien gibt es einen Konflikt. Eine Seite wirft Ihnen vor, Partei zu ergreifen.

Ihre Aufgabe:
•\tErklären Sie, dass Sie neutral bleiben und beide Seiten verstehen wollen.
•\tBegründen Sie Ihre Rolle mit Argumenten, die Ihr Gegenüber nachvollziehen kann.
•\tMachen Sie Ihre Grenzen deutlich (z. B. keine Entscheidungsmacht).

Verstehensorientierte Kommunikation:
Gesprächsabsicht: Sachziel steht im Vordergrund
Sachziel: Sie halten Menge, Qualität, Relevanz und Klarheit der Informationen ein.
Beziehungsziel: Sie nutzen authentische Selbstoffenbarung (Sie sprechen ehrlich über Ihre tatsächlichen Gedanken und Gefühle).
Relevanter Kontext für dieses Rollenspiel – nutzen Sie ihn!
Es handelt sich um eine kooperative Situation mit dem Ziel Verstehen und Vertrauenswahrung.
""",
        "partner_text": """Fiktive KI-Rolle:
Sie sind eine Konfliktpartei und erwarten Unterstützung. Sie empfinden das Verhalten der anderen Person als parteiisch. Sie wollen, dass Ihre Sicht gesehen wird. Schildern Sie Ihre Perspektive und äußern Sie Zweifel an der Neutralität. Reagieren Sie sensibel, hören Sie aber den Erklärungen zu. Sie sind zufriedener, wenn Ihre Situation anerkannt und die Rolle der anderen Person klar ist.

Sachziel (KI): Eigene Sicht verstanden wissen.
Beziehungsziel (KI): Bestätigung und Fairness.
Kommunikationstyp (KI): Verstehensorientiert.
"""
    },

    8: {
        "phase": 2,
        "communication_type": "understanding",
        "title": "8. Jemanden beraten, eine gute Entscheidung zu treffen",
        "user_text": """Role play 8.

Bitte nutzen Sie die Ihnen im Folgenden zur Verfügung gestellten Informationen für die Gestaltung des Gesprächs und die anstehende Aufgabe.

•\tVorbereitungszeit: ca. 5 Minuten
•\tGesprächsdauer: bis zu 10 Minuten
•\tVerhalten Sie sich so, als wären SIE wirklich in dieser Situation.
•\tSie können das Gespräch jederzeit beenden, indem Sie sagen: „Danke, tschüss“.

Titel: 8.\tJemanden beraten, eine gute Entscheidung zu treffen
Hintergrundinformationen (Ihre Rolle): 
Eine Person bittet Sie um Rat bei einer wichtigen Entscheidung (z. B. Schullaufbahn, Berufswahl, Konflikt).

Ihre Aufgabe:
•\tUnterstützen Sie Ihr Gegenüber, Optionen, Folgen und eigene Werte zu klären.
•\tErmutigen Sie dazu, eine eigene Entscheidung zu treffen.

Verstehensorientierte Kommunikation:
Gesprächsabsicht: Sachziel steht im Vordergrund
Sachziel: Sie halten Menge, Qualität, Relevanz und Klarheit der Informationen ein.
Beziehungsziel: Sie nutzen authentische Selbstoffenbarung (Sie sprechen ehrlich über Ihre tatsächlichen Gedanken und Gefühle).
Relevanter Kontext für dieses Rollenspiel – nutzen Sie ihn!
Es handelt sich um eine Beratungssituation ohne Machtgefälle.
""",
        "partner_text": """Fiktive KI-Rolle:
Sie sind die Person, die Rat sucht. Sie sind unsicher und möchten Ihre Gedanken sortieren. Schildern Sie Ihre Situation und Ihr Dilemma. Reagieren Sie auf Fragen und Anregungen. Treffen Sie am Ende selbständig eine Entscheidung.

Sachziel (KI): Optionen verstehen.
Beziehungsziel (KI): Unterstützung erleben, ohne Fremdsteuerung.
Kommunikationstyp (KI): Verstehensorientiert.
"""
    },

    9: {
        "phase": 2,
        "communication_type": "understanding",
        "title": "9. Meine Sicht auf Feedbackverfahren der Schulleitung erklären",
        "user_text": """Role play 9.

Bitte nutzen Sie die Ihnen im Folgenden zur Verfügung gestellten Informationen für die Gestaltung des Gesprächs und die anstehende Aufgabe.

•\tVorbereitungszeit: ca. 5 Minuten
•\tGesprächsdauer: bis zu 10 Minuten
•\tVerhalten Sie sich so, als wären SIE wirklich in dieser Situation.
•\tSie können das Gespräch jederzeit beenden, indem Sie sagen: „Danke, tschüss“.

Titel: 9.\tMeine Sicht auf Feedbackverfahren der Schulleitung erklären
Hintergrundinformationen (Ihre Rolle): 
An Ihrer Schule wird eine neue Feedbackkultur eingeführt. Sie sind skeptisch gegenüber den bisherigen Kriterien, die stark auf die Person der Lehrkraft fokussieren.

Ihre Aufgabe:
•\tLegen Sie Ihre Bedenken dar und schlagen Sie zusätzliche Kriterien vor (z. B. Klassengröße, Ressourcen, Zeitdruck).
•\tFormulieren Sie Ihre Meinung klar, aber respektvoll.
•\tStreben Sie gegenseitiges Verständnis und ggf. Anpassungen an.

Verstehensorientierte Kommunikation:
Gesprächsabsicht: Sachziel steht im Vordergrund
Sachziel: Sie halten Menge, Qualität, Relevanz und Klarheit der Informationen ein.
Beziehungsziel: Sie nutzen authentische Selbstoffenbarung (Sie sprechen ehrlich über Ihre tatsächlichen Gedanken und Gefühle).
Relevanter Kontext für dieses Rollenspiel – nutzen Sie ihn!
Die Schulleitung hat die stärkere Rolle, ist aber offen für konstruktiven Austausch.
""",
        "partner_text": """Fiktive KI-Rolle:
Sie sind die Schulleitung (Herr/Frau Ziegler). Sie möchten die Feedbackkultur einführen. Sie sind offen für konstruktive Hinweise. Schaffen Sie eine unterstützende Atmosphäre und hören Sie aktiv zu. Betonen Sie den Entwicklungs- und keinen Strafcharakter des Feedbacks. Nehmen Sie Argumente an, wenn sie Verständnis für Ihre Position zeigen, klar sind und konkrete Vorschläge enthalten. Schlagen Sie am Ende einen nächsten Schritt vor (Mail, Arbeitsgruppe, Termin).
"""
    },

    10: {
        "phase": 2,
        "communication_type": "understanding",
        "title": "10. Zusammen mit einer/m Kolleg*in Leitlinien entwickeln",
        "user_text": """Role play 10.

Bitte nutzen Sie die Ihnen im Folgenden zur Verfügung gestellten Informationen für die Gestaltung des Gesprächs und die anstehende Aufgabe.

•\tVorbereitungszeit: ca. 5 Minuten
•\tGesprächsdauer: bis zu 10 Minuten
•\tVerhalten Sie sich so, als wären SIE wirklich in dieser Situation.
•\tSie können das Gespräch jederzeit beenden, indem Sie sagen: „Danke, tschüss“.

Titel: 10.\tZusammen mit einer/m Kolleg*in Leitlinien entwickeln
Hintergrundinformationen (Ihre Rolle): 
Sie und eine Kollegin/ein Kollege sollen einen Leitfaden entwickeln (z. B. für Elterngespräche, Feedbackgespräche, Dokumentation von Schülerinformationen).

Ihre Aufgabe:
•\tBringen Sie verschiedene Ideen und Kriterien ein.
•\tKnüpfen Sie an Vorschläge Ihres Gegenübers an.
•\tArbeiten Sie auf ein gemeinsames Ergebnis hin.

Verstehensorientierte Kommunikation:
Gesprächsabsicht: Sachziel steht im Vordergrund
Sachziel: Sie halten Menge, Qualität, Relevanz und Klarheit der Informationen ein.
Beziehungsziel: Sie nutzen authentische Selbstoffenbarung (Sie sprechen ehrlich über Ihre tatsächlichen Gedanken und Gefühle).
Relevanter Kontext für dieses Rollenspiel – nutzen Sie ihn!
Es handelt sich um eine gleichberechtigte kooperative Situation.
""",
        "partner_text": """Fiktive KI-Rolle:
Sie sind die Kollegin/der Kollege in der Leitfaden-Gruppe. Sie haben eigene Vorstellungen, sind aber kompromissbereit. Bringen Sie aktiv eigene Vorschläge ein. Diskutieren Sie diese, ohne zu dominieren. Zeigen Sie Wertschätzung für die Ideen Ihres Gegenübers.

Sachziel (KI): Leitlinien mitentwickeln.
Beziehungsziel (KI): Kooperation stärken.
Kommunikationstyp (KI): Verstehensorientiert.
"""
    },
}


# ---------------------------------------------------------
#  Streamlit UI & Flow Logic
# ---------------------------------------------------------

st.set_page_config(page_title="Rollenspiel-Kommunikationstrainer", layout="wide")

st.title("Rollenspiel-Kommunikationstrainer")

st.sidebar.header("Einstellungen")

student_id = st.sidebar.text_input(
    "Studenten-ID oder Kürzel",
    help="Wird nur zur Zuordnung Ihrer Sitzungen in der Datenauswertung verwendet.",
)

# Sprache fest (hier nur Deutsch, aber für Logging praktisch)
language = "Deutsch"

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
    batch_label = "Block 1 – Rollenspiele 1–5 (Strategische Kommunikation)"
elif st.session_state.batch_step == "batch2":
    current_phase = 2
    batch_label = "Block 2 – Rollenspiele 6–10 (Verstehensorientierte Kommunikation)"
else:
    current_phase = None

if st.session_state.batch_step == "finished":
    st.success(
        "Sie haben je ein Rollenspiel aus Block 1 und Block 2 abgeschlossen. Vielen Dank!"
    )
    st.stop()

st.subheader(batch_label)

# Choose roleplays for this batch
available_ids = [rid for rid, r in ROLEPLAYS.items() if r["phase"] == current_phase]

roleplay_id = st.selectbox(
    "Wählen Sie ein Rollenspiel",
    available_ids,
    format_func=lambda rid: ROLEPLAYS[rid]["title"],
)

current_rp = ROLEPLAYS[roleplay_id]

# Reset conversation if roleplay or batch changed
if (
    st.session_state.meta.get("roleplay_id") != roleplay_id
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
        "roleplay_title": current_rp["title"],
        "communication_type": current_rp["communication_type"],
    }

# ---------------------------------------------------------
#  Instructions
# ---------------------------------------------------------

st.subheader("Anweisungen für SIE")
st.markdown(current_rp["user_text"])

with st.expander("🤖 Verdeckte Anweisungen für die KI-Gesprächspartner:in (nur Lehrkraft)"):
    st.markdown(current_rp["partner_text"])

st.info(
    "Vorgeschlagene maximale Gesprächsdauer: ca. 10 Minuten. "
    "Sie können das Gespräch jederzeit mit „Danke, tschüss“ beenden."
)

# ---------------------------------------------------------
#  Start/restart conversation
# ---------------------------------------------------------

if st.button("Gespräch starten / neu starten"):
    st.session_state.messages = []
    st.session_state.feedback_done = False
    st.session_state.chat_active = True

    system_prompt = f"""
Du bist die simulierte Gesprächspartner:in (KI) in einem schulischen Rollenspiel.
Halte dich strikt an deine Rolle und die untenstehenden Instruktionen.
Sprich auf Deutsch.
Beende das Gespräch nur, wenn dein Gegenüber „Danke, tschüss“ schreibt.

--- Instruktionen, die die Lehrkraft/Student:in sieht ---
{current_rp["user_text"]}

--- Deine fiktive KI-Rolle ---
{current_rp["partner_text"]}
"""

    st.session_state.messages.append(
        {"role": "system", "content": system_prompt}
    )

# ---------------------------------------------------------
#  Chat interface
# ---------------------------------------------------------

st.subheader("Gespräch")

chat_container = st.container()

with chat_container:
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.markdown(f"**Sie:** {msg['content']}")
        elif msg["role"] == "assistant":
            st.markdown(f"**Gesprächspartner:in (KI):** {msg['content']}")

if st.session_state.chat_active and not st.session_state.feedback_done:
    user_input = st.chat_input("Schreiben Sie Ihre nächste Nachricht…")

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
            reply = f"[Fehler bei der OpenAI-API: {e}]"

        st.session_state.messages.append({"role": "assistant", "content": reply})
        st.rerun()

if st.session_state.chat_active and not st.session_state.feedback_done:
    if st.button("⏹ Gespräch beenden"):
        st.session_state.chat_active = False

# ---------------------------------------------------------
#  Feedback nach jedem Rollenspiel (Q1–Q12)
# ---------------------------------------------------------

if (
    not st.session_state.chat_active
    and st.session_state.messages
    and not st.session_state.feedback_done
):
    st.subheader("Kurzes Feedback")

    # Personality
    q1 = st.radio("Die Persönlichkeit des Chatbots war realistisch und ansprechend", [1, 2, 3, 4, 5], horizontal=True)
    q2 = st.radio("Der Chatbot wirkte zu robotisch", [1, 2, 3, 4, 5], horizontal=True)
    q3 = st.radio("Der Chatbot war beim ersten Setup einladend", [1, 2, 3, 4, 5], horizontal=True)
    q4 = st.radio("Der Chatbot wirkte sehr unfreundlich", [1, 2, 3, 4, 5], horizontal=True)

    # Onboarding
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
            st.success(
                "Danke! Block 1 ist abgeschlossen. Bitte machen Sie mit Block 2 (Rollenspiele 6–10) weiter."
            )
        else:
            st.session_state.batch_step = "finished"
            st.success("Vielen Dank! Sie haben beide Blöcke abgeschlossen.")

        # Clear chat for next step
        st.session_state.messages = []

