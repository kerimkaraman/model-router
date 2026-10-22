"""Create fixed stratified development/evaluation splits without API calls."""
import hashlib
import json
import random
from collections import defaultdict
from pathlib import Path
from eval.question import Question

DATA_DIR = Path(__file__).parent / "data"
SEED = 42


def split_questions(questions: list[Question], forced_dev_ids: set[str] | None = None):
    ids = [q.question_id for q in questions]
    prompts = [q.prompt.strip() for q in questions]
    if len(set(ids)) != len(ids) or len(set(prompts)) != len(prompts):
        raise ValueError("Duplicate question IDs or prompts in source dataset")
    forced = forced_dev_ids or set()
    if not forced.issubset(ids):
        raise ValueError("Unknown forced development IDs")
    groups = defaultdict(list)
    for q in questions:
        groups[(q.source, q.subject, q.answer_type)].append(q)
    rng = random.Random(SEED)
    dev, test = [], []
    for key in sorted(groups):
        group = sorted(groups[key], key=lambda q: q.question_id)
        rng.shuffle(group)
        count = int(len(group) * 0.6)
        selected = [q for q in group if q.question_id in forced]
        if not 0 < count < len(group) or len(selected) > count:
            raise ValueError("Stratum too small or too many forced development cases")
        remaining = [q for q in group if q.question_id not in forced]
        dev.extend(selected + remaining[:count - len(selected)])
        test.extend(remaining[count - len(selected):])
    rng.shuffle(dev)
    rng.shuffle(test)
    return dev, test


def main():
    source = DATA_DIR / "test_set.jsonl"
    raw = source.read_bytes()
    questions = [Question.model_validate_json(line) for line in raw.decode().splitlines() if line.strip()]
    # The three smoke-test questions have already been reviewed; keep them in dev.
    forced = {f"mmlu-elementary_mathematics-{i:03d}" for i in range(3)}
    dev, test = split_questions(questions, forced)
    manifest = {
        "version": "split-v1", "seed": SEED, "source_sha256": hashlib.sha256(raw).hexdigest(),
        "dev_count": len(dev), "test_count": len(test), "forced_dev_ids": sorted(forced),
        "evaluation_status": "Previously evaluated source pool; not a pristine holdout.",
        "note": "Historical model outputs and aggregate scores existed before this split. Use new unseen questions for final generalization claims.",
    }
    outputs = {DATA_DIR / "dev.jsonl": "".join(q.model_dump_json() + "\n" for q in dev),
               DATA_DIR / "test.jsonl": "".join(q.model_dump_json() + "\n" for q in test),
               DATA_DIR / "split_manifest.json": json.dumps(manifest, indent=2) + "\n"}
    for path, content in outputs.items():
        if path.exists() and path.read_text() != content:
            raise ValueError(f"Refusing to change frozen split: {path}")
    for path, content in outputs.items():
        if not path.exists():
            path.write_text(content)
    print(f"Frozen split: {len(dev)} dev / {len(test)} evaluation. Source pool was previously evaluated.")


if __name__ == "__main__":
    main()
