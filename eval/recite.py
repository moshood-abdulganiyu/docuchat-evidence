import json
import re
from pathlib import Path

from src.rag import MIN_SCORE

P = Path("eval/rag_answers.jsonl")


def cited_numbers(text: str) -> list[int]:
    groups = re.findall(r"\[([\d,\s]+)\]", text)
    return [int(n) for g in groups for n in re.findall(r"\d+", g)]


def main() -> None:
    rows = [
        json.loads(x) for x in P.read_text(encoding="utf-8").splitlines() if x.strip()
    ]
    for r in rows:
        if not r["found"]:
            continue
        used = [h for h in r["retrieved"] if h["score"] >= MIN_SCORE]
        nums = cited_numbers(r["answer"])
        valid = sorted({n for n in nums if 1 <= n <= len(used)})
        seen, cites = set(), []
        for n in valid:
            key = (used[n - 1]["file"], used[n - 1]["page"])
            if key not in seen:
                seen.add(key)
                cites.append({"n": n, "file": key[0], "page": key[1]})
        r["citations"] = cites
        r["invalid_citations"] = sorted({n for n in nums if n not in valid})
        r["uncited"] = not nums
    P.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
        encoding="utf-8",
    )
    print("recomputed citations for", sum(r["found"] for r in rows), "answered rows")


if __name__ == "__main__":
    main()
