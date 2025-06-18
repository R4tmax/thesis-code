from google.cloud import bigquery
from vertexai.generative_models import GenerativeModel
import vertexai
import pandas as pd
import re
from authlib.integrations.requests_client import OAuth2Session
import os
import streamlit as st
from dotenv import load_dotenv
import base64
import yaml
import logging
from datetime import datetime
from google.oauth2 import service_account
import json
import sys
from langdetect import detect

def get_lang(text):
    try:
        return detect(text)
    except:
        return 'unknown'


class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "time": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "message": record.getMessage(),
        }
        # Přidej další položky, pokud existují
        if hasattr(record, "extra") and record.extra:
            log_record.update(record.extra)
        return json.dumps(log_record)

handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(JsonFormatter())
logging.basicConfig(level=logging.INFO, handlers=[handler])
logger = logging.getLogger("behavio-chatbot")

# === 0.1 Načti prostředí ===
load_dotenv()

CLIENT_ID = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")
REDIRECT_URI = os.getenv("GOOGLE_OAUTH_REDIRECT_URI")
SCOPE = "openid email profile"
AUTHORIZATION_BASE_URL = "https://accounts.google.com/o/oauth2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
WHITELISTED_EMAILS = [e.strip().lower() for e in os.getenv("WHITELISTED_EMAILS", "").split(",") if e]
WHITELISTED_DOMAINS = [d.strip().lower() for d in os.getenv("WHITELISTED_DOMAINS", "").split(",") if d]


def is_allowed_email(email):
    email = email.strip().lower()
    if email in WHITELISTED_EMAILS:
        return True
    return any(email.endswith("@" + domain) for domain in WHITELISTED_DOMAINS)


# === OAuth flow ===
if "user_email" not in st.session_state:
    code = st.query_params.get("code")
    if isinstance(code, list):
        code = code[0]

    oauth = OAuth2Session(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        scope=SCOPE,
        redirect_uri=REDIRECT_URI,
    )


    def img_to_base64(path):
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()


    if not code:
        img_b64 = img_to_base64("images/Google.png")
        authorization_url, _ = oauth.create_authorization_url(
            AUTHORIZATION_BASE_URL,
            prompt="consent",
            access_type="offline"
        )
        st.markdown(
            f"""
            <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;height:75vh;">
                <a href="{authorization_url}" target="_self" style="
                    background: #4285F4;
                    color: white;
                    padding: 24px 36px;
                    border-radius: 14px;
                    font-size: 2em;
                    font-weight: bold;
                    text-decoration: none;
                    box-shadow: 0 4px 18px rgba(66,133,244,0.13);
                    display: flex;
                    align-items: center;
                    gap: 26px;
                    transition: background 0.2s;
                " onmouseover="this.style.background='#3367d6';" onmouseout="this.style.background='#4285F4';">
                    <span style="display:flex;align-items:center;justify-content:center;width:54px;height:54px;background:white;border-radius:50%;margin-right:14px;">
                        <img src="data:image/png;base64,{img_b64}" alt="Google Logo" width="38" height="38" style="display:block;" />
                    </span>
                    Přihlásit se Google účtem
                </a>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.stop()

    #   st.write("Code před odesláním:", code)
    #   st.write("Redirect URI:", REDIRECT_URI)
    try:
        token = oauth.fetch_token(
            TOKEN_URL,
            code=code,
            redirect_uri=REDIRECT_URI,
            include_client_id=True
        )
    except Exception as e:
        st.error(f"❌ Chyba při přihlášení: {e}")
        st.stop()

    # === Získání info o uživateli ===
    try:
        userinfo = oauth.get("https://openidconnect.googleapis.com/v1/userinfo").json()
        email = userinfo.get("email")
    except Exception as e:
        st.error(f"❌ Nepodařilo se získat údaje o uživateli: {e}")
        st.stop()

    # === Ověření přístupu ===
    if not email or not is_allowed_email(email):
        st.error("⛔ Tento účet nemá oprávnění k přístupu.")
        st.stop()

    # === Uložení uživatele a refresh stránky ===
    logger.info("LOGIN", extra={"extra": {"event": "login", "user": email}})
    st.session_state.user_email = email
    st.query_params.clear()
    st.rerun()

# === Zobrazení přihlášeného uživatele ===
st.markdown(f"Přihlášen jako: `{st.session_state.user_email}`")

# === Inicializace session_state ===
if "messages_initialized" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant",
         "content": "Ahoj, jsem analytický chatbot Behavio. Ptej se mě na cokoliv ohledně dat – například na faktury, částky, splatnosti nebo zákazníky."}
    ]
    st.session_state.messages_initialized = True

if "query_history" not in st.session_state:
    st.session_state.query_history = []

if "last_query_result" not in st.session_state:
    st.session_state.last_query_result = None

if "last_query_summary" not in st.session_state:
    st.session_state.last_query_summary = None

# === 1. Načtení .env a přihlašovacích údajů ===
if "GOOGLE_APPLICATION_CREDENTIALS" not in os.environ:
    st.error("❌ Proměnná prostředí GOOGLE_APPLICATION_CREDENTIALS není nastavena.")
    st.stop()

PROJECT_ID = os.getenv("GCP_PROJECT_ID")
LOCATION = os.getenv("GCP_VERTEX_LOCATION")
vertexai.init(project=PROJECT_ID, location=LOCATION)

# === 2. Inicializace klientů ===
SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/bigquery"
]

credentials = service_account.Credentials.from_service_account_file(
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"],
    scopes=SCOPES
)
bq_client = bigquery.Client(project=PROJECT_ID, credentials=credentials)

gemini_model = GenerativeModel("gemini-2.0-flash-001")


# === 2.5 Načti schéma a popisy tabulek z YAML ===
def load_tables_config(yaml_path="tables.yaml"):
    with open(yaml_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config["tables"]


tables_config = load_tables_config()


# === 3. Pomocné funkce ===
def run_bigquery_query(sql_query):
    try:
        query_job = bq_client.query(sql_query)
        return query_job.result().to_dataframe()
    except Exception as e:
        error_msg = str(e)
        # Loguj i error do konzole (Cloud Run logy)
        logger.error("BigQuery ERROR", extra={"extra": {
            "event": "bigquery_error",
            "error": error_msg,
            "user": st.session_state.get("user_email", "unknown"),
            "query": sql_query
        }})
        # Specifické chyby
        if "Bad int64 value" in error_msg:
            return "❌ SQL dotaz obsahuje špatně zadanou hodnotu pro číslo/rok (např. 21.1 místo 2021). Zkontrolujte filtraci a formát dat."
        elif "Unrecognized name" in error_msg:
            return "❌ SQL dotaz obsahuje neexistující sloupec – zkontrolujte názvy sloupců podle schématu."
        elif "No matching signature for operator" in error_msg:
            return "❌ SQL dotaz obsahuje chybný typ pro podmínku (např. snažíte se porovnávat text a pole)."
        elif "Access Denied" in error_msg or "permission" in error_msg.lower():
            return "❌ Nedostatečná oprávnění pro práci s daty. Kontaktujte správce nebo si ověřte přístup."
        elif "Not found" in error_msg:
            return "❌ Tabulka nebo zdroj dat nebyl nalezen. Zkontrolujte název tabulky."
        else:
            # Default fallback
            return "❌ Dotaz se nepodařilo provést. Zkuste jej upravit, nebo kontaktujte správce. (Technická chyba: " + error_msg[:200] + "...)"


def extract_sql_block(text):
    match = re.search(r"```sql\n(.*?)```", text, re.DOTALL)
    return match.group(1).strip() if match else None


# === 4. UI ===
st.markdown("""
    <div style="display: table; margin: 2rem auto 2.5rem auto; text-align: center;">
        <h1 style="color: #01AFE2; font-size: 5em; margin-bottom: 0;">Behavio Chatbot</h1>
        <p style="color: #01AFE2; font-size: 1.em; margin-top: 0;">Tvůj pomocník s daty!</p>
    </div>
""", unsafe_allow_html=True)

# === 5. Sidebar s výsledkem a historií ===
with st.sidebar:
    st.markdown("### Výsledek předchozího dotazu")

    if st.session_state.last_query_result is not None and st.session_state.query_history:
        last = st.session_state.query_history[-1]

        with st.container(border=True):
            st.markdown("**Dotaz:**")
            st.markdown(f"*{last['user_question']}*")

            st.markdown("**SQL dotaz:**")
            st.code(last["sql"], language="sql")

            st.markdown("**Výsledky:**")
            st.dataframe(st.session_state.last_query_result)

        with st.container(border=True):
            st.markdown("**Shrnutí:**")
            st.markdown(last["summary"])

        if st.button("Vymazat výsledek"):
            st.session_state.last_query_result = None
            st.session_state.last_query_summary = None
            st.session_state.query_history.pop()
    else:
        st.caption("Zatím žádné výsledky.")

    st.markdown("---")
    st.markdown("### Historie dotazů této session")
    if st.session_state.query_history:
        for i, entry in enumerate(reversed(st.session_state.query_history[-5:]), 1):
            st.markdown(f"""
            <div style="background-color: #181A1B; border-left: 3px solid #01AFE2; padding: 12px; margin-bottom: 16px; border-radius: 14px;">
            <strong style="color: #FFF;">{len(st.session_state.query_history) - i + 1}. Dotaz:</strong><br>
            <em style="color: #CCC;">{entry['user_question']}</em><br><br>
            <strong style="color: #FFF;">SQL dotaz:</strong>
            <pre style="background-color: #23272B; color: #FFF; padding: 10px; border-radius: 12px; font-size: 1em; margin-bottom: 8px;"><code>{entry['sql']}</code></pre>
            """, unsafe_allow_html=True)

            # TADY vykresli dataframe (v HTML bloku to nejde, ale můžeš použít st.container)
            if "data" in entry and isinstance(entry["data"], pd.DataFrame):
                st.dataframe(entry["data"])

            st.markdown(f"""
            <strong style="color: #FFF;">Shrnutí:</strong><br>
            <span style="font-size: 0.95em; color: #CCC;">{entry['summary']}</span>
            </div>
            """, unsafe_allow_html=True)

    else:
        st.caption("Zatím žádná historie.")

# === 6. Zobrazení historie zpráv ===
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "assistant":
            # 1. SQL dotaz
            if "content" in msg:
                st.markdown(msg["content"])
            # 2. Výsledky (tabulka)
            if "data" in msg:
                st.markdown("**Výsledky:**")
                st.dataframe(msg["data"])
            # 3. Shrnutí
            if "summary" in msg:
                st.markdown("**Shrnutí:**")
                st.markdown(msg["summary"])
        else:
            st.markdown(msg["content"])

# === 7. Uživatelský vstup ===
user_input = st.chat_input("Zadejte svůj dotaz zde")


def make_tables_context(tables_config):
    result = ""
    for table in tables_config:
        result += f"TABULKA `{table['name']}`: {table['description']}\n"
        result += f"{table['schema']}\n\n"
    return result


if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)
    logger.info("USER_INPUT", extra={"extra": {
        "event": "user_input",
        "user": st.session_state.user_email,
        "input": user_input
    }})
    lang = get_lang(user_input)
    with st.chat_message("assistant"):
        with st.spinner("Získávám odpověď..."):
            tables_context = make_tables_context(tables_config)

            context = "\n".join([
                f"{msg['role']}: {msg['content']}"
                for msg in st.session_state.messages[-6:]
                if msg["role"] in ("user", "assistant")
            ])

            prompt = f"""
            Jsi analytický chatbot Behavio. Na základě uživatelského dotazu:

            1. Vyber pouze jednu nejvhodnější tabulku ze seznamu níže (viz popis a schéma).
            2. Vygeneruj přesný, platný a optimalizovaný SQL dotaz pro BigQuery.
            3. Práci s Aliasy dělej v detekovaném jazyce na vstupu uživatele: {lang}, Každý alias musí být v tomto jazyce.

            **Pravidla:**
            - Používej pouze názvy sloupců uvedené ve schématu. Nepřidávej žádné jiné sloupce.
            - Pokud je sloupec SQL klíčové slovo (např. End, Group, Order), uzavři jej do zpětných apostrofů (`End`).
            - Nikdy nepoužívej SELECT *. Vždy explicitně vypisuj požadované sloupce.
            - Pokud dotaz odkazuje na “poslední” data a není jasné podle čeho, použij nejvhodnější časový sloupec (např. Start, End, BookingDate, issue_date).
            - SQL dotaz vrať pouze v bloku ```sql ... ```, bez dalších komentářů nebo vysvětlení.
            - Alias (AS ...) piš pouze s písmeny bez diakritiky, čísly a podtržítkem. Nepoužívej mezery ani speciální znaky.
            - Nikdy v SQL aliasu ani jinde v kódu NEPOUŽÍVEJ diakritiku ani jiné než ASCII znaky.
            - Pro sloupce typu ARRAY vždy použij převod na STRING pomocí ARRAY_TO_STRING(...), ale NIKDY nepřeváděj STRING pomocí ARRAY_TO_STRING.
            - Počet řádků počítej jako COUNT(*). COUNT(DISTINCT ...) použij jen, pokud uživatel výslovně chce unikátní hodnoty (např. “unikátních”, “distinct”).
            - Pokud není jasné, co je unikátní, počítej řádky jako COUNT(*).
            - Pokud uživatel chce průměr, medián, percentil nebo jinou agregaci ve skupinách (např. za měsíc a zákazníka), vytvoř SQL pomocí CTE (WITH) nebo subquery, nikdy nekombinuj window funkce (OVER) s GROUP BY ve stejném dotazu. Pro medián použij APPROX_QUANTILES(..., 2)[OFFSET(1)].
            - Nikdy nepoužívej JOIN – tabulky jsou samostatné, nespojuj je.
            - Ověř měnu u všech částkových sloupců a dopiš ji k částkám.
            - Pokud uživatel použije synonymum (například "klient" místo "zákazník" nebo "customer"), vždy vyber odpovídající sloupec podle významu dotazu.
            - Všechny názvy aliasů a odpovědi ve výstupním SQL piš ve stejném jazyce, v jakém byl uživatelský dotaz.
            - Vždy piš přehledné a čitelné SQL (odsazení, aliasy).
            - Pokud uživatel zadá jméno klienta, které se nemusí přesně shodovat s názvem v datech, ve WHERE podmínce vždy použij REGEXP_CONTAINS(LOWER(NORMALIZE_AND_CASEFOLD(<název sloupce>)), r'\\b<uživatelský dotaz>\\b') místo LIKE, abys minimalizoval falešné shody (např. “avori” vs “javorina”); vždy tímto způsobem ignoruj velikost písmen i diakritiku; pokud uživatel výslovně požaduje částečnou shodu, použij REGEXP_CONTAINS bez hranic slova (r'<dotaz>').
            - Ve shrnutí vždy piš čísla ve formátu běžného zápisu s oddělením tisíců, nikdy ne v zápisu jako 1.2e+06. Nikdy nepoužívej zápis 1.2e+06.
            - LIMITUJ počet záznamů v SQL na 30
            - Pokud se uživatel zeptá, za co je faktura u klienta, vycházej z dat o projektech pro daného klienta. TYTO TABULKY NESPOJUJ!.
            - Pokud ve SELECT používáš jak agregaci, tak i sloupce, které nejsou v agregaci, musíš tyto sloupce uvést také v GROUP BY.




            **Tabulky a jejich schémata:**

            {tables_context}

            **Poslední konverzace:**
            {context}

            **Dotaz uživatele:**
            {user_input}

            Vrať pouze SQL v bloku ```sql ... ```.
            
            
            **Důležité:** Vždy odpovídej ve stejném jazyce, v jakém byl uživatelský dotaz. Pokud byl položen anglicky, odpovídej anglicky!
            """

            model_reply = gemini_model.generate_content(prompt, generation_config={"temperature": 0.0})
            sql_query = extract_sql_block(model_reply.text)

            if not sql_query:
                st.markdown("_Nepodařilo se extrahovat SQL dotaz z odpovědi, protože se nevztahuje k datům. Přeformulujte prosím váš dotaz._")
            else:
                st.markdown("**SQL dotaz:**")
                logger.info("SQL_QUERY", extra={"extra": {
                    "event": "sql_query",
                    "user": st.session_state.user_email,
                    "query": sql_query
                }})
                st.code(sql_query, language="sql")
                query_result = run_bigquery_query(sql_query)

                if isinstance(query_result, pd.DataFrame):
                    def serialize_lists(x):
                        if isinstance(x, (list, tuple)):
                            return ', '.join(map(str, x))
                        return x


                    query_result_for_summary = query_result.applymap(serialize_lists)
                    if lang == 'en':
                        summary_prompt = (
                            f"Here are the results of the query:\n"
                            f"{query_result_for_summary.to_markdown(index=False)}\n\n"
                            f"Answer the original question in natural English: {user_input}\n\n"
                            f"**Important:** Answer in the same language as the input question."
                        )
                    else:
                        summary_prompt = (
                            f"Zde jsou výsledky dotazu:\n"
                            f"{query_result_for_summary.to_markdown(index=False)}\n\n"
                            f"Odpověz přirozeným jazykem na původní otázku: {user_input}\n\n"
                            f"**Důležité:** Odpověz ve stejném jazyce, v jakém je dotaz."
                        )
                    summary_reply = gemini_model.generate_content(summary_prompt, generation_config={"temperature": 0.0})

                    # Uložení
                    st.session_state.last_query_result = query_result
                    st.session_state.last_query_summary = summary_reply.text

                    st.session_state.query_history.append({
                        "user_question": user_input,
                        "sql": sql_query,
                        "data": query_result,
                        "summary": summary_reply.text
                    })

                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": f"```sql\n{sql_query}\n```",
                        "data": query_result,
                        "summary": summary_reply.text
                    })
                    st.rerun()
                else:
                    if isinstance(query_result, str) and query_result.startswith("❌"):
                        st.warning(query_result)
                    else:
                        st.error("Nastala neočekávaná chyba. Zkuste změnit dotaz nebo kontaktujte podporu.")
st.markdown("---")
st.caption("Postaveno pomocí Vertex AI + BigQuery + Streamlit")
