# Enterprise RAG Document Assistant — Projekt-Roadmap

Überarbeitete Version, ausgelegt auf Umsetzung mit Claude Code.

**Ziel:** Ein Portfolio-Repo, das nicht nur „LLM benutzt", sondern Information Retrieval, Evaluation, Agent-Orchestrierung, Backend-Engineering und Deployment demonstriert — mit echten Zahlen.

**Nicht verhandelbar:** Phasen 0–5. Alles danach ist Bonus. Ein zu 100 % fertiges Projekt bis Phase 5 schlägt ein zu 60 % fertiges bis Phase 9.

---

## Arbeitsweise mit Claude Code

**Vor Phase 1: `CLAUDE.md` im Repo-Root anlegen.** Claude Code liest das bei jedem Start. Inhalt:

```markdown
# Projektkontext
Enterprise RAG Document Assistant. Fragen über hochgeladene PDFs
beantworten, mit Quellenangaben (Dokument + Seite).

# Konventionen
- Python 3.12, uv als Package Manager (kein pip/requirements.txt)
- Vollständige Type Hints, mypy strict
- ruff für Lint + Format
- Kein Code in main.py außer App-Startup
- Jede neue Funktion bekommt einen Test
- Deutsche Kommentare vermeiden, Code auf Englisch

# Architektur
FastAPI Backend ist die einzige Schnittstelle. Streamlit spricht
NUR über HTTP mit dem Backend, nie direkt mit RAG-Logik.

# Befehle
uv run pytest
uv run ruff check .
uv run mypy app/
```

**Regeln für die Zusammenarbeit:**
- Arbeite phasenweise, nicht alles auf einmal. Eine Phase = eine Session = ein Branch.
- Lass Claude Code am Anfang jeder Phase einen Plan vorschlagen, bevor Code geschrieben wird.
- Nach jeder Phase: Tests grün, Commit, dann erst weiter.
- Wenn Claude Code eine Abkürzung nimmt (Logik im Endpoint statt im Service-Layer), sofort korrigieren. Technische Schulden in Phase 2 kosten dich in Phase 7 einen Tag.

---

## Phase 0 — Setup

**Ziel:** Leeres, aber professionelles Skeleton mit grüner CI.

Struktur:

```
rag-assistant/
├── app/
│   ├── api/          # FastAPI Router, dünn
│   ├── ingestion/    # PDF → Chunks
│   ├── retrieval/    # Vector, BM25, Hybrid, Rerank
│   ├── generation/   # Prompting, LLM-Client
│   ├── agent/        # Tool-Layer (ab Phase 6)
│   ├── evaluation/   # Eval-Harness
│   ├── config.py     # Pydantic Settings
│   └── models.py     # Pydantic Schemas
├── ui/               # Streamlit
├── tests/
├── eval/
│   ├── dataset/
│   └── results/
├── data/sample_documents/
├── docker/
├── CLAUDE.md
├── README.md
├── pyproject.toml
└── docker-compose.yml
```

Tooling: uv, ruff, mypy, pytest, pre-commit, GitHub Actions (lint + typecheck + test).

**Acceptance:** `uv run pytest` läuft (auch mit 0 Tests), CI ist grün, `.env.example` existiert.

**Startprompt:**
> Erstelle das Skeleton nach der Struktur in CLAUDE.md. pyproject.toml mit uv, ruff und mypy strict konfiguriert, pytest, pre-commit-Hook, GitHub Actions Workflow für lint/typecheck/test. Pydantic-Settings-Config, die API-Keys aus .env liest. Noch keine Businesslogik.

---

## Phase 1 — Ingestion

**Ziel:** PDF rein, saubere Chunks mit Metadaten raus.

- PyMuPDF für Extraktion, Seitenzahl pro Textblock erhalten
- Chunking mit konfigurierbarer Größe und Overlap (wird in Phase 5 variiert, also von Anfang an als Parameter)
- Pydantic-Modell `Chunk`: `chunk_id`, `document_name`, `page_number`, `text`, `char_start`, `char_end`

Die Seitenzahl ist das Feature des Projekts. Wenn sie beim Chunking über Seitengrenzen verloren geht, ist alles danach wertlos. Bei seitenübergreifenden Chunks: Liste von Seiten speichern, nicht nur eine.

**Acceptance:** Test, der ein Sample-PDF lädt und prüft, dass jeder Chunk eine plausible Seitenzahl hat.

---

## Phase 2 — Vector Store + Baseline Retrieval

**Ziel:** Bewusst naives, aber funktionierendes Retrieval.

- Qdrant über docker-compose (nicht FAISS — du willst eine echte DB mit Metadata-Filtering)
- Embeddings über ein multilingual-fähiges Modell (deutsche Dokumente!), z. B. `intfloat/multilingual-e5-large` oder ein API-Embedding
- Retrieval-Interface als Protocol definieren, damit BM25/Hybrid/Rerank später ohne Umbau andocken

**Acceptance:** `retrieve(query, k=5)` liefert Chunks mit Score und Metadaten.

---

## Phase 3 — Generation + Citations

**Ziel:** Erste End-to-End-Antwort mit Quellen, über FastAPI.

- Prompt: nur aus dem Kontext antworten, Chunks nummeriert übergeben
- Modell zitiert Chunk-IDs, Backend mappt diese auf Dokument + Seite
- Provider-agnostischer LLM-Client (ein Interface, austauschbare Implementierung)
- Endpoints: `POST /documents/upload`, `POST /query`, `GET /documents`, `DELETE /documents/{id}`

**Wichtig:** FastAPI ab hier, nicht erst später. Wenn du zuerst Streamlit baust, refaktorierst du dich in Phase 8 tot.

**Acceptance:** `POST /query` liefert Antwort + strukturierte Quellenliste. Erster sichtbarer Erfolg.

---

## Phase 4 — Eval-Dataset

**Ziel:** Messbarkeit, bevor du optimierst.

- 3–5 echte PDFs mit inhaltlicher Substanz (technische Handbücher, Geschäftsberichte, Normen)
- Fragen **synthetisch generieren**: LLM erzeugt aus jedem Chunk 1–2 Fragen, der Quell-Chunk ist automatisch das Gold-Label
- Davon 30–40 manuell verifizieren und als `verified: true` markieren
- Ziel: 100–150 Fragen, davon ein verifizierter Kern
- Bewusst auch 10–15 **unbeantwortbare** Fragen einbauen (für Phase 7)

Das Vorgehen offen ins README schreiben — synthetische Eval-Daten mit menschlicher Stichprobe sind Industriestandard, kein Makel.

**Acceptance:** `eval/dataset/questions.jsonl` mit Feldern `question`, `expected_document`, `expected_page`, `expected_chunk_id`, `answerable`, `verified`.

---

## Phase 5 — Eval-Harness + Retrieval-Ablation

**Das ist der Kern des Projekts.** Hier entstehen die Zahlen, wegen denen jemand das Repo ernst nimmt.

Metriken: Recall@K, MRR, Citation Accuracy (zeigt die Quelle auf die Stelle, aus der die Antwort stammt?).

Ablationen, jeweils als CSV/Markdown-Report:

1. **Chunking:** 500/100, 700/100, 1000/200 Token
2. **Retriever:** BM25 vs. Vector vs. Hybrid (RRF-Fusion)
3. **Reranking:** Cross-Encoder über 20 Kandidaten → Top 5

Der Harness muss per CLI laufen und reproduzierbar sein:
`uv run python -m app.evaluation.run --config configs/hybrid_rerank.yaml`

**Acceptance:** Ergebnistabelle mit echten Zahlen, die ins README kann. Wenn Hybrid schlechter abschneidet als Vector — schreib es trotzdem rein und erkläre warum. Das wirkt kompetenter als geschönte Zahlen.

---

*Ab hier: Bonus. Erst starten, wenn 0–5 sitzen.*

---

## Phase 6 — Agent-Layer

**Ziel:** Die Lücke zwischen deiner Low-Code-Agent-Erfahrung und Code-Agents schließen.

Weg von „immer retrieven" hin zu „Agent entscheidet". Framework: LangGraph (Marktstandard) oder Pydantic AI (typsicherer).

Mindestens drei Tools:
- `search_documents(query, document_filter)`
- `list_documents()` — für Fragen wie „welche Dokumente hast du?"
- `compare_across_documents(query)` — Multi-Hop, mehrere Retrieval-Runden

Query-Decomposition bei komplexen Fragen, Self-Correction wenn das erste Retrieval nichts Brauchbares liefert.

**Wichtig für die Evaluation:** Agent vs. reines RAG auf demselben Eval-Set vergleichen. Wenn der Agent bei einfachen Fragen schlechter oder langsamer ist, ist genau das ein interessantes README-Ergebnis.

---

## Phase 7 — Groundedness statt Threshold

Ein fester Similarity-Threshold ist brüchig (Scores sind nicht kalibriert und domänenabhängig). Stattdessen:

- **Groundedness-Check:** Zweiter LLM-Call prüft, ob jede Aussage vom zitierten Kontext gedeckt ist
- **Citation-Verification:** Verweist die Quelle tatsächlich auf die Textstelle?
- **Abstention:** Bei fehlender Deckung „In den Dokumenten nicht gefunden" statt Halluzination

Messbar über die unbeantwortbaren Fragen aus Phase 4: Abstention Rate und False-Answer Rate.

Das ist auch die bessere Interview-Antwort auf „wie verhindern Sie Halluzinationen?".

---

## Phase 8 — Frontend

Streamlit, spricht ausschließlich über HTTP mit FastAPI. Upload links, Chat rechts, Quellen unter der Antwort. Klick auf Seitenzahl öffnet das PDF an der Stelle.

Streamlit signalisiert „Prototyp" — akzeptabel, solange das Backend sauber getrennt ist. Wenn Zeit bleibt, ist ein schlankes React-Frontend das stärkere Signal.

---

## Phase 9 — Observability + Deployment

- Tracing der Retrieval- und Agent-Runs (LangSmith oder Phoenix/OpenTelemetry). Kein MLflow — das ist für klassische ML-Experimente, nicht für LLM-Pipelines
- Prompt-Injection-Guardrail auf Uploads (Dokumenteninhalt ist untrusted input)
- `docker compose up` startet Qdrant + FastAPI + Streamlit
- Optional: Deploy auf Azure Container Apps (passt zum DACH-Enterprise-Markt und zu deinem Microsoft-Umfeld)

---

## README

Wird zuletzt geschrieben, ist aber das Wichtigste. Kein Recruiter liest deinen Code, alle lesen das README.

Struktur:
1. Ein Satz, was es tut
2. Demo-GIF oder Screenshot — ganz oben
3. Architektur-Diagramm (Mermaid)
4. **Evaluation Results** als Tabelle, prominent platziert
5. Tech-Entscheidungen begründet: warum Hybrid, warum Reranking, warum Agent statt reinem RAG
6. Quickstart: `docker compose up`
7. Limitations, ehrlich

Die Eval-Tabellen und die begründeten Entscheidungen sind der Unterschied zwischen deinem Repo und den Tausenden „Chat with your PDF"-Klonen. Alles andere ist austauschbar.

---

## Zeitplanung

Realistisch neben Werkstudentenjob, Kolloquium und IJCLR-Talk am 17. September: **10–12 Wochen**, nicht 6.

| Block | Phasen | Aufwand |
|---|---|---|
| MVP | 0–3 | 3 Wochen |
| Messbarkeit | 4–5 | 3 Wochen |
| Erweiterung | 6–7 | 2–3 Wochen |
| Polish | 8–9 + README | 2–3 Wochen |

**Wenn die Zeit knapp wird:** Phasen 0–5 plus README fertigstellen und dabei bleiben. Ein sauber evaluiertes RAG-System ohne Agent ist stärker als ein Agent-System ohne Zahlen.
