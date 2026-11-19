"""AI step: read the ETL knowledge document (or raw ETL script) of each MT staging table and describe, per source table,
the extraction condition and the business scope. Only table names, source names and counts
are sent to the AI - no client data."""
import json
import logging
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

KNOWLEDGE_DIR = Path(__file__).parent / "knowledge"
# For Azure OpenAI the "model" is the DEPLOYMENT name
MAX_WORKERS = int(os.getenv("AI_MAX_WORKERS", "6"))
MAX_SCRIPT_CHARS = 150_000

SYSTEM_PROMPT = (
    "You are a data migration reconciliation analyst. You read an ETL SQL script that loads one "
    "MT staging table and explain how each Vpoint source table is used. "
    "Answer with valid JSON only - no markdown, no commentary."
)

USER_PROMPT = """MT staging table: {table}

<glossary>
{glossary}
</glossary>

<etl_knowledge>
{script}
</etl_knowledge>

Source tables / branches to describe (name exactly as given):
{sources}

For EACH source table return:
- "condition": the extraction conditions the ETL script applies to that source (WHERE filters, join conditions,
  DISTINCT / UNION behaviour, in-scope filter). Concise and technical, one to three sentences.
- "scope": one or two sentences in business terms: what is migrated and why. No SQL jargon.

Rules:
- Use only what is in the knowledge document (the exact-source table gives the extraction condition and business scope; reuse its wording, shortened if needed). If a source cannot be found in the script write "Not found in ETL script".
- Type "Lookup" = the source only supplies values to MT columns (no staging rows): describe the join and what it populates.
- Names such as "Duplicates removed across UNION branches" are adjustment rows, not tables: explain that the
  ETL uses UNION so identical rows collapse into one.
- Never include client, entity or owner names or any data values.

Return exactly:
{{"sources":[{{"source_table":"<name as given>","condition":"...","scope":"..."}}]}}"""


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


# ---- Knowledge base: Azure Blob container (container/<source>/<module>/<document>.md) ------------------
# Settings: KNOWLEDGE_STORAGE_CONNECTION (connection string)  OR  KNOWLEDGE_STORAGE_ACCOUNT_URL (managed identity,
# role "Storage Blob Data Reader"). KNOWLEDGE_CONTAINER (default "knowledge"),
# KNOWLEDGE_PREFIX (default "vpoint/Entity Administration/"). If no storage setting exists the local
# ./knowledge folder is used (local testing).
KNOWLEDGE_CONTAINER = os.getenv("KNOWLEDGE_CONTAINER", "knowledge")
DEFAULT_PREFIX = os.getenv("KNOWLEDGE_PREFIX", "vpoint/Entity Administration/")
CACHE_SECONDS = int(os.getenv("KNOWLEDGE_CACHE_SECONDS", "300"))
_cache = {}  # prefix -> (loaded_at, docs, glossary)


def _index_name(filename: str) -> str:
    key = _norm(Path(filename).stem)
    return key[len("insert"):] if key.startswith("insert") else key


def _read_blobs(prefix: str) -> list:
    """Returns [(file name, text)] of every .md / .sql blob under the prefix."""
    conn = os.getenv("KNOWLEDGE_STORAGE_CONNECTION")
    account_url = os.getenv("KNOWLEDGE_STORAGE_ACCOUNT_URL")
    if not conn and not account_url:
        return []
    from azure.storage.blob import ContainerClient
    if conn:
        container = ContainerClient.from_connection_string(conn, KNOWLEDGE_CONTAINER)
    else:
        from azure.identity import DefaultAzureCredential
        container = ContainerClient(account_url, KNOWLEDGE_CONTAINER, credential=DefaultAzureCredential())
    files = []
    for blob in container.list_blobs(name_starts_with=prefix):
        if blob.name.lower().endswith((".md", ".sql")):
            data = container.download_blob(blob.name).readall()
            files.append((blob.name.rsplit("/", 1)[-1], data.decode("utf-8-sig", errors="ignore")))
    return files


def _read_local() -> list:
    return [(f.name, f.read_text(encoding="utf-8-sig", errors="ignore"))
            for pattern in ("*.sql", "*.md") for f in KNOWLEDGE_DIR.rglob(pattern)]


def load_knowledge(prefix: str = "") -> tuple:
    """Returns ({normalised table key: document text}, glossary text). Cached for CACHE_SECONDS per prefix.
    Document files starting with '_' are shared files (glossary, index), not table documents; a .md document
    wins over a raw .sql file of the same name."""
    prefix = (prefix or DEFAULT_PREFIX).strip()
    if prefix and not prefix.endswith("/"):
        prefix += "/"
    cached = _cache.get(prefix)
    if cached and time.time() - cached[0] < CACHE_SECONDS:
        return cached[1], cached[2]

    files = _read_blobs(prefix) or _read_local()
    docs, glossary = {}, ""
    for name, text in sorted(files, key=lambda f: f[0].lower().endswith(".md")):  # .md last -> overrides .sql
        if name.lower() == "_glossary.md":
            glossary = text
        elif not name.startswith("_"):
            docs[_index_name(name)] = text
    logging.info("Knowledge loaded: %d documents (prefix '%s')", len(docs), prefix)
    _cache[prefix] = (time.time(), docs, glossary)
    return docs, glossary


def _extract_json(text: str) -> dict:
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < 0:
        raise ValueError("No JSON in AI response")
    return json.loads(text[start:end + 1])


def _describe_table(client, table: dict, script: str, glossary: str = "") -> dict:
    """Returns {source_table: (condition, scope)} for one staging table."""
    sources = [{"source_table": s["source_table"], "source_type": s["source_type"]} for s in table["sources"]]
    prompt = USER_PROMPT.format(
        table=table["mig_staging_table"],
        glossary=glossary,
        script=script[:MAX_SCRIPT_CHARS],
        sources=json.dumps(sources, indent=1),
    )
    last_error = None
    for _ in range(2):  # one retry if the answer is not valid JSON
        try:
            resp = client.chat.completions.create(
                model=os.environ["AZURE_OPENAI_DEPLOYMENT"],
                temperature=0,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
            )
            data = _extract_json(resp.choices[0].message.content or "")
            return {
                s["source_table"]: (s.get("condition", ""), s.get("scope", ""))
                for s in data.get("sources", [])
            }
        except Exception as ex:  # noqa: BLE001 - report must still be produced
            last_error = ex
    logging.warning("AI failed for %s: %s", table["mig_staging_table"], last_error)
    return {}


def generate_descriptions(tables: list, knowledge_prefix: str = "") -> dict:
    """Returns {(staging_table, source_table): (condition, scope)}. Missing entries mean 'leave blank'."""
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    if not endpoint or not api_key or not os.getenv("AZURE_OPENAI_DEPLOYMENT"):
        logging.warning("AZURE_OPENAI_* settings not set - Condition and Scope will be blank")
        return {}

    from openai import AzureOpenAI  # imported here so the function still starts if AI is not configured

    client = AzureOpenAI(azure_endpoint=endpoint, api_key=api_key, api_version="2024-08-01-preview")
    scripts, glossary = load_knowledge(knowledge_prefix)
    result = {}

    def work(table):
        script = scripts.get(_norm(table["mig_staging_table"]))
        if not script:
            logging.warning("No knowledge document for %s", table["mig_staging_table"])
            return table["mig_staging_table"], {}
        return table["mig_staging_table"], _describe_table(client, table, script, glossary)

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        for staging_table, described in pool.map(work, tables):
            for source_table, texts in described.items():
                result[(staging_table, source_table)] = texts
    return result
