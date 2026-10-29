import logging

from src.llm import generate

log = logging.getLogger("docuchat")

MAX_HISTORY = 6

SYSTEM = (
    "Rewrite the follow-up question so it can be understood without the chat "
    "history. Use the history only to resolve references such as 'it', 'that "
    "paper' or 'the second one'. Do not answer the question. Keep file names, "
    "numbers and technical terms exactly. If the question is already "
    "standalone, return it unchanged. Output only the question, on one line."
)


def rewrite_question(question: str, history: list) -> str:
    if not history:
        return question
    lines = [f"{t.role.capitalize()}: {t.content[:300]}" for t in history]
    prompt = (
        "Chat history:\n"
        + "\n".join(lines)
        + f"\n\nFollow-up question: {question}\n\nStandalone question:"
    )
    try:
        out = (generate(prompt, system=SYSTEM) or "").strip()
    except Exception:
        log.exception("rewrite failed, using the original question")
        return question
    first_line = out.splitlines()[0].strip() if out else ""
    return first_line[:500] or question
