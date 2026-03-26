import time
import shutil
from pathlib import Path
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

from config import LLM_MODEL
load_dotenv()

# ── Config ─────────────────────────────────────────────────────────────────
DATA_DIR       = Path("data")
OUTPUT_DIR     = Path("data_clean")
TXT_OUTPUT  = OUTPUT_DIR / "transcripts"
PDF_OUTPUT  = OUTPUT_DIR / "pdfs"
DELAY_SECONDS  = 6      # delay between API calls to avoid rate limits
MODEL          = LLM_MODEL

PROMPT = """You are cleaning up a university lecture transcript for use in a RAG system.

Your task:
- Remove filler words and spoken language artifacts (right, well, okay, you know, sort of, kind of, I mean, etc.)
- Fix incomplete or run-on sentences
- Add proper punctuation and paragraph breaks
- Organize content into clear logical sections with headings where appropriate
- Preserve ALL technical content, concepts, examples, and terminology exactly
- Do not add any information that was not in the original
- Do not summarize or shorten — keep all the content, just clean it up

Return only the cleaned transcript text, no preamble or explanation.

Transcript:
{text}"""

# ── Setup ──────────────────────────────────────────────────────────────────
TXT_OUTPUT.mkdir(parents=True, exist_ok=True)
PDF_OUTPUT.mkdir(parents=True, exist_ok=True)
llm = ChatGoogleGenerativeAI(model=MODEL, temperature=0)

txt_files = sorted((DATA_DIR / "transcripts").glob("*.txt"))
pdf_files = sorted((DATA_DIR / "pdfs").glob("*.pdf"))

print(f"Found {len(txt_files)} transcript files and {len(pdf_files)} PDF files")

# ── Copy PDFs unchanged ────────────────────────────────────────────────────
print("\nCopying PDFs...")
for pdf in pdf_files:
    dest = PDF_OUTPUT / pdf.name
    shutil.copy2(pdf, dest)
    print(f"  [copied] {pdf.name}")

# ── Rewrite transcripts ────────────────────────────────────────────────────
print("\nRewriting transcripts...")

for i, txt_file in enumerate(txt_files):
    dest = TXT_OUTPUT / txt_file.name

    # Skip if already done — allows resuming after interruption
    if dest.exists():
        print(f"  [skip] {txt_file.name} (already done)")
        continue

    print(f"  [{i+1}/{len(txt_files)}] {txt_file.name}...")

    try:
        text = txt_file.read_text(encoding="utf-8")
        prompt = PROMPT.format(text=text)
        response = llm.invoke([HumanMessage(content=prompt)])
        dest.write_text(response.content, encoding="utf-8")
        print(f"    ✓ done")

    except Exception as e:
        if "429" in str(e):
            print(f"    ✗ rate limit hit — waiting 60 seconds...")
            time.sleep(60)
            # retry once
            try:
                response = llm.invoke([HumanMessage(content=prompt)])
                dest.write_text(response.content, encoding="utf-8")
                print(f"    ✓ done after retry")
            except Exception as e2:
                print(f"    ✗ failed after retry: {e2}")
                continue
        else:
            print(f"    ✗ error: {e}")
            continue

    time.sleep(DELAY_SECONDS)

print(f"\nDone. Rewritten files saved to {OUTPUT_DIR}/")