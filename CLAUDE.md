# Projektkontext

Enterprise RAG Document Assistant. Fragen über hochgeladene PDFs beantworten,
mit Quellenangaben (Dokument + Seite). Deutsche Dokumente sind der Regelfall,
nicht die Ausnahme.

Der Kern des Projekts ist die **Evaluation** (Phase 5): reproduzierbare
Retrieval-Ablationen mit echten Zahlen. Alles andere existiert, um diese Zahlen
zu ermöglichen.

# Konventionen

- Python 3.12, uv als Package Manager (kein pip/requirements.txt)
- Vollständige Type Hints, mypy strict
- ruff für Lint + Format
- Kein Code in main.py außer App-Startup
- Jede neue Funktion bekommt einen Test
- Deutsche Kommentare vermeiden, Code auf Englisch

# Architektur

FastAPI Backend ist die einzige Schnittstelle. Streamlit spricht NUR über HTTP
mit dem Backend, nie direkt mit RAG-Logik.

Businesslogik gehört in den Service-Layer (`app/ingestion`, `app/retrieval`,
`app/generation`), nicht in FastAPI-Endpoints. Endpoints sind dünn: validieren,
delegieren, serialisieren.

Retrieval ist hinter einem `Protocol` abstrahiert, damit BM25/Hybrid/Rerank
ohne Umbau andocken.

# Invarianten (nicht verhandelbar)

Diese Regeln existieren, weil ihr Bruch erst Phasen später sichtbar wird.

## 1. Gold-Labels sind Character-Spans, niemals Chunk-IDs

Eval-Gold-Labels referenzieren `(document_name, char_start, char_end)` — einen
Span im **Quelldokument**. Niemals eine Chunk-ID.

Grund: Phase 5 variiert die Chunk-Größe (500/100, 700/100, 1000/200). Bei jeder
Variante ändern sich alle Chunk-IDs. Ein Chunk-ID-Gold-Label wäre nach der
ersten Ablation wertlos — und damit der Kern des Projekts.

`Recall@K` heißt entsprechend: "überlappt mindestens einer der Top-K Chunks mit
dem Gold-Span?"

## 2. char_start/char_end sind Offsets im Gesamtdokument

Nicht im Chunk, nicht auf der Seite. Ein Offset, der nur relativ zum Chunk
gilt, macht Invariante 1 unmöglich.

## 3. Chunk-IDs sind deterministisch

`chunk_id = sha256(document_name | char_start | char_end)[:16]`

Gleiche Datei + gleiche Chunking-Config muss dieselben IDs erzeugen.
Re-Indexing darf keine Diffs produzieren, sonst ist nichts reproduzierbar.

## 4. Seitenzahlen sind eine Liste, kein Skalar

Chunks überschreiten Seitengrenzen. `page_numbers: list[int]`, sortiert.
Die Seitenangabe ist das Feature des Projekts — geht sie beim Chunking
verloren, ist alles danach wertlos.

## 5. Chunking-Parameter sind immer Parameter

Chunk-Größe und Overlap werden nie hardcodiert, auch nicht "erstmal".
Phase 5 variiert sie.

## 6. Embeddings brauchen Prefixe

Bei e5-Modellen: Queries mit `"query: "`, Passagen mit `"passage: "`.
Ohne Prefix sinkt der Recall messbar, ohne dass etwas kaputt aussieht.

## 7. Alles Teure wird gecacht

Embeddings (`hash(text) -> vector`) und LLM-Responses
(`hash(model + prompt) -> response`) auf Disk. Der Eval-Harness wird oft
wiederholt; ohne Cache kostet jede Iteration Zeit und Geld, und die
Reproduzierbarkeit aus Phase 5 ist nicht gegeben.

# Befehle

```
uv sync                    # Dependencies installieren
uv run pytest              # Tests
uv run ruff check .        # Lint
uv run ruff format .       # Format
uv run mypy app/           # Typecheck
```

# Arbeitsweise

- Eine Phase = eine Session = ein Branch. Phase 5 wird gesplittet
  (5a: Metriken + Harness-Gerüst, 5b: Ablationen).
- Am Anfang jeder Phase erst einen Plan vorschlagen, dann Code.
- Nach jeder Phase: Tests grün, Commit, dann erst weiter.
- Keine Abkürzungen (Logik im Endpoint statt im Service-Layer). Technische
  Schulden in Phase 2 kosten in Phase 7 einen Tag.

# Bekannte Limitationen (ins README, nicht stillschweigend ignorieren)

- Tabellen: PyMuPDF extrahiert Tabellen als Textsuppe. Bei Geschäftsberichten
  und Normen zielen viele Fragen genau darauf.
- Gescannte PDFs: kein OCR. Nur Text-Layer-PDFs werden unterstützt.
