Below is a broad, practical checklist of **tools you can give an AI‑agent** so that it can act on your behalf, fetch information, perform calculations, manipulate data, and interact with the world.  
Think of each entry as a *capability* you expose to the model via an API, a function call, or a plug‑in.  The exact implementation will depend on the platform you’re using (OpenAI Functions, LangChain tools, Auto‑GPT plug‑ins, etc.), but the categories and examples stay the same.

---

## 1️⃣ Information‑Retrieval Tools  

| Tool | What it does | Typical use‑case | Example implementation |
|------|--------------|------------------|------------------------|
| **Web Search** | Query a search engine (Google, Bing, DuckDuckGo) and return snippets or URLs. | Answer up‑to‑date factual questions, find recent news, locate product specs. | `search(query: str) -> List[Result]` |
| **Document Retrieval / RAG** | Vector‑store lookup (e.g., Pinecone, Weaviate, FAISS) over your own knowledge base. | Answer questions that rely on internal docs, policies, manuals. | `retrieve(query: str, top_k: int) -> List[Document]` |
| **Wikipedia API** | Pull the latest article content or summary. | Quick background on a topic. | `wiki_summary(topic: str) -> str` |
| **News Feed** | Pull headlines from RSS or a news API (e.g., NewsAPI). | Provide daily briefings. | `get_latest_news(topic: str, limit: int) -> List[Article]` |
| **Scientific Literature** | Query arXiv, PubMed, Semantic Scholar. | Research assistance. | `search_papers(query: str) -> List[Paper]` |

---

## 2️⃣ Computational & Data‑Processing Tools  

| Tool | What it does | Typical use‑case | Example implementation |
|------|--------------|------------------|------------------------|
| **Calculator / Math Engine** | Perform exact arithmetic, symbolic algebra, calculus, statistics. | Solve equations, generate charts, compute financial metrics. | `calc(expression: str) -> str` (uses Python `sympy` or a dedicated math engine) |
| **Code Interpreter** | Execute Python (or other language) snippets in a sandbox. | Data analysis, quick prototyping, generate plots, transform CSVs. | `run_python(code: str) -> ExecutionResult` |
| **Spreadsheet Engine** | Read/write Excel/CSV, run formulas, pivot tables. | Budget updates, data cleaning. | `excel_read(file_path, sheet) -> DataFrame` |
| **SQL Query Executor** | Run SELECT/INSERT/UPDATE against a relational DB. | Pull sales numbers, update inventory. | `sql_query(query: str) -> Table` |
| **Statistical / ML Model** | Call a pre‑trained model (e.g., sentiment classifier, image recognizer). | Classify feedback, detect anomalies. | `classify_sentiment(text: str) -> str` |
| **Unit Converter** | Convert between measurement systems. | Engineering calculations. | `convert(value, from_unit, to_unit) -> float` |

---

## 3️⃣ Communication & Collaboration Tools  

| Tool | What it does | Typical use‑case | Example implementation |
|------|--------------|------------------|------------------------|
| **Email Sender** | Compose and send email via SMTP / Gmail API. | Follow‑up messages, report generation. | `send_email(to, subject, body, attachments?)` |
| **Chat / Messaging** | Post to Slack, Teams, Discord, WhatsApp, SMS. | Real‑time notifications, task assignments. | `post_message(channel, text)` |
| **Calendar / Scheduler** | Create, update, or query events (Google Calendar, Outlook). | Book meetings, check availability. | `create_event