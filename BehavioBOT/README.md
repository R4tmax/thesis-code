# Behavio Chatbot

Tento chatbot umožňuje pokládat dotazy v přirozeném jazyce nad tabulkou faktur v BigQuery a získat odpovědi pomocí LLM (Gemini 2.0 Flash). Projekt byl vytvořen jako MVP pro firmu Behavio.

## Funkce

- **Přihlášení přes Google účet** (OAuth 2.0, whitelisting emailů, vlastní stylizované tlačítko)
- **Generování SQL dotazů z textových otázek**
- **Napojení na BigQuery** (např. `dwh_develop.synth_invoices`)
- **Shrnutí výsledků v přirozeném jazyce** (díky LLM)
- **Ukládání historie dotazů a odpovědí** (včetně výsledků a shrnutí)
- **Streamlit chat UI s pamětí** (během session)
- **Nasazení na Google Cloud Run** (serverless hosting)

## Technologie

- Python, Streamlit
- Google OAuth 2.0 (`authlib`)
- Google Cloud BigQuery
- Vertex AI Gemini (GenerativeModel)
- Cloud Run (serverless)
- `.env` + service account pro zabezpečený přístup

## Důležité upozornění k přihlášení

> **Po obnovení stránky nebo delší nečinnosti může být uživatel odhlášen a je nutné se přihlásit znovu.**  
> Důvodem je způsob, jakým Streamlit a Cloud Run spravují session (session není persistentní mezi refreši na cloudu).  
> Pokud je uživatel přihlášený v Google, proběhne login rychle.

## Spuštění lokálně

### 1. `.env` soubor

Vytvořte soubor `.env` s následujícím obsahem (doplňte vlastní údaje):

```
GOOGLE_APPLICATION_CREDENTIALS=credentials/credentials.json
GCP_PROJECT_ID=your-gcp-project
GCP_VERTEX_LOCATION=europe-west4
GOOGLE_OAUTH_CLIENT_ID=...
GOOGLE_OAUTH_CLIENT_SECRET=...
GOOGLE_OAUTH_REDIRECT_URI=...
```

### 2. Instalace a spuštění

```
pip install -r requirements.txt
streamlit run main.py
```

### 3. Struktura projektu

```
/BehavioBOT
├── .streamlit/
│   └── config.toml
├── credentials/
│   └── credentials.json
├── images/
│   └── Google.png
├── .env
├── .gitignore
├── .gcloudignore
├── Dockerfile
├── main.py
├── README.md
└── requirements.txt
```
`.gitignore` obsahuje složku `credentials/` i `.env`

## Nasazení na Google Cloud Run

### Build a deploy:

```
gcloud builds submit --tag gcr.io/behavio-bi-sp/behavio-bot
gcloud run deploy behavio-bot \
  --image gcr.io/behavio-bi-sp/behavio-bot \
  --service-account=sa-nlq-behavio-bot@behavio-bi-sp.iam.gserviceaccount.com \
  --platform managed \
  --region europe-west3 \
  --allow-unauthenticated
```

Po nasazení získáš veřejný odkaz. Aplikace se automaticky uspí při neaktivitě (0 traffic).

## Oprávnění pro Service Account

- **Vertex AI User** (`roles/aiplatform.user`)
- **BigQuery Job User** (`roles/bigquery.jobUser`)
- **BigQuery Data Viewer** (`roles/bigquery.dataViewer`)
- **BigQuery Read Session User** (`roles/bigquery.readSessionUser`) – volitelně pro rychlé načítání přes Storage API

## Nastavení Google OAuth (pro admina projektu)

1. V Google Cloud Console vytvoř OAuth 2.0 Client ID (typ *Web application*).
2. Do povolených redirect URI zadej přesnou adresu:
    - Pro lokální vývoj: `http://localhost:8501`
    - Pro Cloud Run: např. `https://behavio-bot-749895389873.europe-west3.run.app`
3. Přidej e-maily do whitelistu v kódu.
4. Vyplň údaje do `.env` souboru.

## Náklady ([oficiální ceník](https://cloud.google.com/vertex-ai/pricing#generative-ai))

| Operace          | Cena (1K tokenů) |
| ---------------- | ---------------- |
| Input (prompt)   | $0.00010         |
| Output (odpověď) | $0.00040         |

Průměrná interakce: ~\$0.0012–\$0.0015 + BigQuery (např. ~$0.01/GB)

## Známé chyby a řešení

- **403 - 'bigquery.readsessions.create' permission denied:**  
  Přidej roli `BigQuery Read Session User` do service accountu.
- **BigQuery Storage module not found:**  
  Spusť `pip install google-cloud-bigquery-storage`, nebo vypni `bqstorage` při načítání dat.
- **Výsledek obsahuje `f0_` jako název sloupce:**  
  Přidej aliasy (`AS ...`) do SQL výstupu v promptu pro model.
- **Chybí `tabulate` při převodu na Markdown:**  
  Spusť `pip install tabulate`
- **403 Forbidden při přístupu na Cloud Run:**  
  Spusť:  
  `gcloud run services add-iam-policy-binding behavio-bot --region=europe-west3 --member="allUsers" --role="roles/run.invoker"`

## Licence

Projekt je interní pro Behavio. Není určen k veřejnému šíření.
