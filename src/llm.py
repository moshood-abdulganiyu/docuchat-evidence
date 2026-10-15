import os
import time

from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai.errors import APIError

load_dotenv()
MODEL = os.environ.get("LLM_MODEL", "gemini-3.5-flash-lite")
_client = None


def _get_client():
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    return _client


def generate(prompt: str, system: str | None = None, max_retries: int = 4) -> str:
    config = types.GenerateContentConfig(temperature=0, system_instruction=system)
    delay = 5
    for attempt in range(max_retries + 1):
        try:
            resp = _get_client().models.generate_content(
                model=MODEL, contents=prompt, config=config
            )
            return resp.text or ""
        except APIError as e:
            if e.code not in (429, 500, 503) or attempt == max_retries:
                raise
            time.sleep(delay)
            delay *= 2
    return ""
