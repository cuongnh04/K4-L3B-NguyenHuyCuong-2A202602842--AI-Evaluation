"""Run a reproducible, API-free retrieval baseline for the evaluation lab.

This is a deterministic baseline, not a substitute for the OpenAI-backed
DomainAssistant run. It uses the production BM25 retriever and returns the
retrieved evidence verbatim so the evaluation pipeline can be smoke-tested.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from domain_assistant import BM25Retriever, load_corpus


def run(dataset_path: Path, corpus_dir: Path, output: Path, top_k: int) -> None:
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    corpus_id, chunks = load_corpus(corpus_dir)
    if dataset["corpus_id"] != corpus_id:
        raise ValueError("Dataset and corpus corpus_id do not match")
    retriever = BM25Retriever(chunks)
    answers = []
    for item in dataset["qa_pairs"]:
        retrieved = retriever.retrieve(item["question"], top_k)
        answer = " ".join(chunk.text for chunk in retrieved)
        answers.append(
            {
                "id": item["id"],
                "question": item["question"],
                "actual_answer": answer or "The corpus contains no matching evidence.",
                "retrieved_contexts": [
                    {
                        "source_doc": chunk.source_doc,
                        "chunk_id": chunk.chunk_id,
                        "text": chunk.text,
                        "score": round(chunk.score, 6),
                    }
                    for chunk in retrieved
                ],
                "error": None,
            }
        )
    artifact = {
        "schema_version": "1.0",
        "corpus_id": corpus_id,
        "generated_at": datetime.now(UTC).isoformat(),
        "agent": {
            "name": "offline-extractive-baseline",
            "model": "deterministic-bm25-extractive",
            "top_k": top_k,
            "prompt_version": "offline-baseline-1.0",
        },
        "answers": answers,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Generated {len(answers)} offline baseline answers: {output}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=Path("golden_dataset.json"))
    parser.add_argument("--corpus-dir", type=Path, default=Path("data/technology_store"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/actual_answers_offline.json"))
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()
    run(args.dataset, args.corpus_dir, args.output, args.top_k)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
