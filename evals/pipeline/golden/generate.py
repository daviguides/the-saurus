"""Generate golden evaluation dataset from test PDFs.

Uses RAGAS TestsetGenerator to create synthetic evaluation
questions from scientific papers, then saves as golden dataset.

Usage:
    uv run python -m pipeline.golden.generate
"""

import json
import os
from pathlib import Path

GOLDEN_DIR = Path(__file__).parent
PAPERS_DIR = GOLDEN_DIR / "papers"
OUTPUT_PATH = GOLDEN_DIR / "dataset.json"


def generate():
    """Generate golden dataset from papers in golden/papers/."""
    from google import genai
    from ragas.llms import llm_factory
    from ragas.testset import TestsetGenerator

    if not PAPERS_DIR.exists() or not list(PAPERS_DIR.glob("*.pdf")):
        print(f"No PDFs found in {PAPERS_DIR}")
        print("Add 3-5 test PDFs to evals/pipeline/golden/papers/")
        return

    api_key = os.environ.get(
        "GOOGLE_API_KEY",
        os.environ.get("PIPELINE_LLM_API_KEY", ""),
    )
    client = genai.Client(api_key=api_key)
    llm = llm_factory("gemini-2.5-flash", provider="google", client=client)

    # Load papers as documents
    from langchain_community.document_loaders import PyPDFLoader

    docs = []
    for pdf_path in sorted(PAPERS_DIR.glob("*.pdf")):
        loader = PyPDFLoader(str(pdf_path))
        docs.extend(loader.load())
        print(f"Loaded {pdf_path.name} ({len(docs)} pages total)")

    # Generate test set
    generator = TestsetGenerator(llm=llm)
    testset = generator.generate_with_langchain_docs(
        docs,
        testset_size=20,
    )

    # Convert to JSON-serializable format
    dataset = []
    for row in testset.to_pandas().to_dict("records"):
        dataset.append({
            "input": row.get("user_input", ""),
            "expected_output": row.get("reference", ""),
            "contexts": row.get("reference_contexts", []),
            "metadata": {
                "evolution_type": row.get("evolution_type", ""),
                "source": "ragas_synthetic",
            },
        })

    OUTPUT_PATH.write_text(json.dumps(dataset, indent=2, ensure_ascii=False))
    print(f"Generated {len(dataset)} test cases -> {OUTPUT_PATH}")


if __name__ == "__main__":
    generate()
