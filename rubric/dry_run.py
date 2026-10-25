"""AI dry run: AI raters from different model families apply the draft rubric to the rubric-check passages.

Run once by hand from the repo root (needs GROQ_API_KEY):
    python -m rubric.dry_run            # 2 models x 3 runs x 10 items x 2 criteria = 120 calls

Writes data/dry_run.json after every call. Calls already in the file are skipped, so a rerun resumes.
The app never calls a model; it only reads data/dry_run.json.
"""
import json
import os
import re
import time
from pathlib import Path

from openai import AuthenticationError, NotFoundError, OpenAI, RateLimitError

ROOT = Path(__file__).resolve().parent.parent
PROFILE_PATH = ROOT / "profiles" / "text_complexity.json"
ITEMS_PATH = ROOT / "data" / "rubric_items.json"
DRY_RUN_PATH = ROOT / "data" / "dry_run.json"

# Two model families, so a shared quirk of one family does not read as a clear rubric.
# llama-3.3-70b-versatile was the planned Meta rater, but Groq no longer serves it.
MODELS = {
    "openai/gpt-oss-120b": "OpenAI",
    "qwen/qwen3.8-27b": "Alibaba",
}
CRITERIA = ["vocabulary", "sentence_structure"]
RUNS = 3
SLEEP_SECONDS = 2.5
MAX_TRIES = 6

PROMPT = """You rate how complex a reading passage is on one criterion, using only the rubric below.

Criterion: {criterion} ({question})
Rubric:
{rubric}

Passage:
\"\"\"{text}\"\"\"

Answer with a JSON object with two keys:
- "label": exactly one of {labels}
- "clause": the rubric line that decided your answer, copied word for word"""


def parse(content: str, levels: list[str]) -> dict:
    """Strip any <think> block, read the JSON, and check the label is a known level."""
    content = re.sub(r"<think>.*?</think>", "", content or "", flags=re.DOTALL).strip()
    answer = json.loads(content)
    label = str(answer.get("label", "")).strip().lower().replace(" ", "_")
    if label not in levels:
        raise ValueError(f"unknown label: {label!r}")
    return {"label": label, "clause": str(answer.get("clause", "")).strip()}


def rate(client: OpenAI, model: str, prompt: str, levels: list[str]) -> dict:
    """One call, with backoff on rate limits and a retry on unreadable answers."""
    wait = SLEEP_SECONDS
    for attempt in range(1, MAX_TRIES + 1):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=1,
                # Qwen thinks by default, which burns the 8k tokens-per-minute free tier in a few calls
                extra_body={"reasoning_effort": "none"} if model.startswith("qwen/") else None,
            )
            return parse(response.choices[0].message.content, levels)
        except RateLimitError:
            wait *= 2
            print(f"  rate limited, waiting {wait:.0f}s")
            time.sleep(wait)
        except (AuthenticationError, NotFoundError):
            raise
        except Exception as error:  # bad JSON, unknown label, or a transient API error
            if attempt == MAX_TRIES:
                raise
            print(f"  retry {attempt}: {error}")
            time.sleep(SLEEP_SECONDS)
    raise RuntimeError(f"{model} kept hitting rate limits")


def load_results() -> list[dict]:
    if DRY_RUN_PATH.exists():
        return json.loads(DRY_RUN_PATH.read_text())["ratings"]
    return []


def save(results: list[dict]) -> None:
    DRY_RUN_PATH.write_text(json.dumps({
        "rubric": PROFILE_PATH.name,
        "rubric_version": json.loads(PROFILE_PATH.read_text())["version"],
        "ratings": results,
    }, indent=2))


def main() -> None:
    profile = json.loads(PROFILE_PATH.read_text())
    items = json.loads(ITEMS_PATH.read_text())["items"]
    levels = profile["levels"]
    models = MODELS
    client = OpenAI(api_key=os.environ["GROQ_API_KEY"], base_url="https://api.groq.com/openai/v1")

    results = load_results()
    done = {(r["model"], r["run"], r["item_id"], r["criterion"]) for r in results}
    total = len(models) * RUNS * len(items) * len(CRITERIA)
    print(f"{len(done)} of {total} calls already in {DRY_RUN_PATH.name}")

    for model, provider in models.items():
        for run in range(1, RUNS + 1):
            for item in items:
                for criterion in CRITERIA:
                    key = (model, run, item["item_id"], criterion)
                    if key in done:
                        continue
                    spec = profile["criteria"][criterion]
                    prompt = PROMPT.format(
                        criterion=criterion.replace("_", " "),
                        question=spec["question"],
                        rubric="\n".join(f"- {level}: {line}" for level, line in spec["levels"].items()),
                        text=item["text"],
                        labels=", ".join(levels),
                    )
                    answer = rate(client, model, prompt, levels)
                    results.append({"model": model, "provider": provider, "run": run,
                                    "item_id": item["item_id"], "criterion": criterion, **answer})
                    save(results)
                    print(f"{len(results):3d}/{total} {model} run {run} {item['item_id']} {criterion}: {answer['label']}")
                    time.sleep(SLEEP_SECONDS)


if __name__ == "__main__":
    main()
