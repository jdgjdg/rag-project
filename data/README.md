# data/ — Raw Source Material

This directory holds the original, unmodified course content. Nothing in here is read directly by the RAG system — all ingestion uses the cleaned copies in `data_clean/`.

---

## Structure

```
data/
├── pdfs/                        # Lecture slide PDFs (read-only source)
├── transcripts/                 # Raw lecture transcripts (audio-to-text)
└── assignment_questions.txt     # Raw list of assignment questions (one per line)
```

---

## How raw data becomes indexed

1. **Transcripts** are processed by `rewrite_transcripts.py`, which uses an LLM to remove filler words and improve formatting while preserving all technical content. Output goes to `data_clean/transcripts/`.
2. **PDFs** are copied unchanged to `data_clean/pdfs/`.
3. `ingest.py` then reads everything from `data_clean/` and builds the Chroma vector database.

Run the full pipeline once:

```bash
python rewrite_transcripts.py   # cleans transcripts (slow — calls Gemini per file)
python ingest.py                # embeds cleaned data into chroma_db/
```

Both scripts support resuming if interrupted.

---

## Adding new material

Drop PDFs into `data/pdfs/` and/or transcripts into `data/transcripts/`, re-run the pipeline above, and the new content will appear in answers automatically.
