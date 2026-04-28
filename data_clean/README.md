# data_clean/ — Processed Data (Ingestion Source)

This is the directory that `ingest.py` actually reads from. Its contents are cleaned, properly formatted versions of the raw material in `data/`.

---

## Structure

```
data_clean/
├── pdfs/                               # PDFs copied unchanged from data/pdfs/
├── transcripts/                        # LLM-cleaned transcript files
└── assignment_questions_clean.txt      # Deduplicated, normalised assignment questions
```

---

## How files get here

| File type | Source | How |
|---|---|---|
| PDFs | `data/pdfs/` | `shutil.copy2` — no modification |
| Transcripts | `data/transcripts/` | `rewrite_transcripts.py` — LLM rewrites for clarity |
| Assignment questions | `data/assignment_questions.txt` | Manual review and normalisation |

Run `rewrite_transcripts.py` to regenerate the transcripts folder. It skips files that already exist, so it's safe to re-run after adding new transcripts.

---

## What the LLM cleaning does (transcripts only)

- Removes filler words (right, okay, you know, sort of, etc.)
- Fixes run-on and incomplete sentences
- Adds paragraph breaks and section headings
- **All technical content is preserved verbatim** — no summarisation

---

## Assignment questions file

`assignment_questions_clean.txt` is used to build a separate Chroma index (`chroma_assignment/`). When a student query is too similar to one of these questions (cosine similarity ≥ 0.80), the assistant switches to a Socratic prompt that asks the student what they've already tried, rather than providing guidance.
