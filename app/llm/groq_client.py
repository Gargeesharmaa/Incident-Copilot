import os
import time

from dotenv import load_dotenv
from groq import Groq, RateLimitError

load_dotenv()

MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
_client = None

def get_client() -> Groq:
    global _client
    if _client is None:
        key = os.getenv("GROQ_API_KEY")
        if not key:
            raise RuntimeError("GROQ_API_KEY is missing. Add it to .env")
        _client = Groq(api_key=key)
    return _client


def chat_json(messages: list[dict], temperature: float = 0.0, max_tokens: int = 800):
    """Call the model in JSON mode. Returns (text, usage_dict)."""
    for attempt in range(3):
        try:
            resp = get_client().chat.completions.create(
                model=MODEL,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
            )
            u = resp.usage
            usage = {
                "prompt_tokens": u.prompt_tokens,
                "completion_tokens": u.completion_tokens,
                "total_tokens": u.total_tokens,
            }
            return resp.choices[0].message.content, usage
        except RateLimitError:
            time.sleep(2 * (attempt + 1))  # free tier is rate limited
    raise RuntimeError("Groq rate limit hit 3 times. Wait a minute and retry.")
