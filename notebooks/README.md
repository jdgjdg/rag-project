# notebooks/ — Experimentation

Jupyter notebooks used for prototyping and exploring the RAG pipeline. Not part of the production system.

---

## Vectorizer.ipynb

Early-stage notebook for experimenting with embedding strategies, chunk sizes, and retrieval quality before those decisions were moved into `config.py` and `ingest.py`. Useful as a scratchpad for:

- Testing different chunk sizes / overlaps
- Inspecting retrieved document quality interactively
- Trying out new embedding models

---

## Running

```bash
# from project root with venv active
jupyter notebook notebooks/Vectorizer.ipynb
```

Requires `jupyter` to be installed (`pip install jupyter`). The notebook shares the same `.env` and Python environment as the rest of the project.
