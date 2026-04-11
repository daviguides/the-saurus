"""Direct Gemini API test — bypasses Agno to debug why adhd_asd_comorbidity.pdf fails.

Usage:
    cd pipeline
    uv run python scripts/test_gemini_direct.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

# Load .env
from dotenv import load_dotenv
load_dotenv()

import google.genai as genai

# --- Config ---

API_KEY = os.environ.get("PIPELINE_LLM_API_KEY") or os.environ.get("GOOGLE_API_KEY")
if not API_KEY:
    print("ERROR: No API key. Set PIPELINE_LLM_API_KEY or GOOGLE_API_KEY")
    sys.exit(1)

MODEL = "gemini-2.5-flash"
PDF_FILENAME = "adhd_asd_comorbidity.pdf"
PAPERS_DIR = Path(__file__).parent.parent.parent / "docs" / "papers"

# --- Find the PDF and its markdown ---

pdf_path = PAPERS_DIR / PDF_FILENAME
if not pdf_path.exists():
    print(f"PDF not found: {pdf_path}")
    sys.exit(1)

# Check if there's an existing markdown from a job
jobs_dir = Path(__file__).parent.parent / "jobs"
md_content = None
for job_dir in sorted(jobs_dir.iterdir(), reverse=True) if jobs_dir.exists() else []:
    for md_file in job_dir.glob("*.md"):
        # Read first line to check if it's this paper
        first_line = md_file.read_text()[:200]
        if "ASD and ADHD" in first_line or "837424" in first_line:
            md_content = md_file.read_text()
            print(f"Found existing markdown: {md_file} ({len(md_content)} chars)")
            break
    if md_content:
        break

if not md_content:
    # Ingest fresh
    print(f"No existing markdown found, ingesting {pdf_path}...")
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from pipeline.ingestion import ingest_pdf
    md_content = ingest_pdf(pdf_path.read_bytes()).to_annotated_markdown()
    print(f"Ingested: {len(md_content)} chars")

print(f"\nMarkdown: {len(md_content)} chars, ~{len(md_content)//4} tokens")
print(f"First 200 chars: {md_content[:200]}")
print()

# --- Prompt (same as PaperAnalyzer) ---

PROMPT = """\
You are a scientific literature analyst. Extract the KEY thematic groups from this research paper AND the specific claims for each theme.

INSTRUCTIONS:
1. Identify 5-12 major themes (max 15).
2. For each theme, extract specific claims.
3. Positions are marked as [p.X,§Y] in the text.

Return JSON inside a ```json code block:
```json
{
  "themes": [
    {
      "name": "Theme Name",
      "description": "One sentence",
      "positions": [{"page": 1, "paragraph": 3}],
      "claims": [
        {
          "text": "Exact claim",
          "position": {"page": 1, "paragraph": 3},
          "deep": "Full paragraph context",
          "summary": "One sentence summary"
        }
      ]
    }
  ]
}
```

Paper:
"""

# --- Test 1: Direct genai client ---

print("=" * 60)
print("TEST 1: google.genai client (same as Qdrant embeddings use)")
print("=" * 60)

client = genai.Client(api_key=API_KEY)

t0 = time.monotonic()
try:
    response = client.models.generate_content(
        model=MODEL,
        contents=PROMPT + md_content,
    )
    elapsed = time.monotonic() - t0

    print(f"Status: OK")
    print(f"Elapsed: {elapsed:.1f}s")
    print(f"Candidates: {len(response.candidates) if response.candidates else 0}")

    if response.candidates:
        candidate = response.candidates[0]
        print(f"Finish reason: {candidate.finish_reason}")
        print(f"Safety ratings: {candidate.safety_ratings}")

        if candidate.content and candidate.content.parts:
            text = candidate.content.parts[0].text
            print(f"Response length: {len(text)} chars")
            print(f"First 500 chars:\n{text[:500]}")
            print(f"Last 200 chars:\n{text[-200:]}")

            # Try to parse JSON
            import re
            json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
            if json_match:
                try:
                    data = json.loads(json_match.group(1))
                    themes = data.get("themes", [])
                    total_claims = sum(len(t.get("claims", [])) for t in themes)
                    print(f"\nParsed OK: {len(themes)} themes, {total_claims} claims")
                except json.JSONDecodeError as e:
                    print(f"\nJSON parse error: {e}")
                    print(f"Raw JSON (first 500): {json_match.group(1)[:500]}")
            else:
                print("\nNo JSON code block found in response")
        else:
            print("No content in candidate")
            print(f"Candidate: {candidate}")
    else:
        print("No candidates in response")
        print(f"Prompt feedback: {response.prompt_feedback}")

except Exception as e:
    elapsed = time.monotonic() - t0
    print(f"Status: FAILED after {elapsed:.1f}s")
    print(f"Error type: {type(e).__name__}")
    print(f"Error: {e}")

# --- Test 2: With safety settings relaxed ---

print()
print("=" * 60)
print("TEST 2: With relaxed safety settings")
print("=" * 60)

from google.genai.types import GenerateContentConfig, SafetySetting, HarmCategory, HarmBlockThreshold

t0 = time.monotonic()
try:
    response = client.models.generate_content(
        model=MODEL,
        contents=PROMPT + md_content,
        config=GenerateContentConfig(
            safety_settings=[
                SafetySetting(category=HarmCategory.HARM_CATEGORY_HARASSMENT, threshold=HarmBlockThreshold.OFF),
                SafetySetting(category=HarmCategory.HARM_CATEGORY_HATE_SPEECH, threshold=HarmBlockThreshold.OFF),
                SafetySetting(category=HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, threshold=HarmBlockThreshold.OFF),
                SafetySetting(category=HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, threshold=HarmBlockThreshold.OFF),
            ],
        ),
    )
    elapsed = time.monotonic() - t0

    print(f"Status: OK")
    print(f"Elapsed: {elapsed:.1f}s")

    if response.candidates:
        candidate = response.candidates[0]
        print(f"Finish reason: {candidate.finish_reason}")
        print(f"Safety ratings: {candidate.safety_ratings}")

        if candidate.content and candidate.content.parts:
            text = candidate.content.parts[0].text
            print(f"Response length: {len(text)} chars")

            import re
            json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
            if json_match:
                try:
                    data = json.loads(json_match.group(1))
                    themes = data.get("themes", [])
                    total_claims = sum(len(t.get("claims", [])) for t in themes)
                    print(f"Parsed OK: {len(themes)} themes, {total_claims} claims")
                except json.JSONDecodeError as e:
                    print(f"JSON parse error: {e}")
            else:
                print("No JSON code block found")
        else:
            print("No content — likely blocked by safety")
            print(f"Candidate: {candidate}")
    else:
        print("No candidates")
        print(f"Prompt feedback: {response.prompt_feedback}")

except Exception as e:
    elapsed = time.monotonic() - t0
    print(f"Status: FAILED after {elapsed:.1f}s")
    print(f"Error: {e}")

print("\nDone.")
