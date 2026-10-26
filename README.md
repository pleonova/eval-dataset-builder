# Expert Eval Builder

**Live prototype:** https://eval-dataset-builder-pkk6a.ondigitalocean.app/

A Streamlit app that checks expert ratings before you use them to tune or score an LLM judge. It answers two questions:

1. **Which expert labels are safe to tune against?** It sorts each label into Trusted, Re-rate, or No expert consensus, and says what to do next.
2. **Is the rubric clear enough to send to experts?** AI raters from different providers apply the draft rubric first. Where they flip or disagree, the wording is probably unclear.

The idea: an AI judge is no better than the humans it is checked against. Before tuning, find out whether experts truly disagree, read the rubric differently, or just need more ratings.

> **All ratings and findings are simulated.** Only the four levels and three criteria names follow the [Learning Commons text complexity evaluators](https://github.com/learning-commons-org/evaluators). The ratings, the rubric wording, and every pattern the app finds (including "the vocabulary rule is unclear") were made up for this demo.

## Run it

Python 3.11.

```
pip install -r requirements.txt
streamlit run app.py
pytest -q
```

The data is committed, so the app needs no API keys. To regenerate it:

```
python simulate.py                       # data/ratings.csv, data/truth.json (seed 42)
GROQ_API_KEY=... python -m rubric.dry_run   # data/dry_run.json, about 120 calls, resumes if stopped
```

## What's in the app

| Tab | Status | What it shows |
|---|---|---|
| **Overview** | Built | Go or no go on tuning, with next steps and cost. Where labels stand (bucket bar and item table), whether the rubric looks clear, and how sure we are (Trusted share with a 95% range). The "Can the AI stand in?" card is an early read, grayed out until running the AI is a feature. |
| **Rubric** | Built | Results of a live AI dry run (GPT-OSS 120B and Qwen 3.8 27B on Groq, 3 runs each on 10 passages). A Clear? check per criterion with the suggested fix. The rubric is our own draft wording (`profiles/text_complexity.json`), not Learning Commons' rubric, so its Vocabulary ✗ is about our draft only. |
| **Statistics** | Draft | Alpha by criterion with ranges grouped by passage, confusion between levels, per-rater kappa. Not yet checked. |
| **Details** | Placeholder | Layout for the analyst view, filled with example values. |
| **Cost** | Stub | Coming next. |

## Data

`data/ratings.csv` is long format, one row per rating: `item_id`, `criterion`, `rater_id`, `label`, `round`.

- 60 passages × 3 criteria (`sentence_structure`, `vocabulary`, `background_knowledge`) = 180 labels.
- 4 levels, in order: `slightly_complex`, `moderately_complex`, `very_complex`, `exceedingly_complex`.
- Round 1: 4 experts. Round 2: 2 new experts on about half the split labels. The AI judge is 3 runs (`judge_run1` to `judge_run3`).

The simulation plants patterns so the engine has a known answer to find, checked against `data/truth.json`. **These patterns are invented settings in `simulate.py`. None of them come from the Learning Commons dataset.**

- Experts are right about 80% of the time, and their misses are one level off.
- Vocabulary is set up to be confusing: simulated experts mix up `moderately_complex` and `very_complex` far more than on the other criteria.
- About 15% of items are truly subjective and split 2-2 between neighboring levels.
- About half the split labels are left without a round 2, so Re-rate is a real slice and the next steps are worth taking. Subjective labels without a round 2 sit in Re-rate too, since it isn't known yet that experts will keep splitting.

Why simulated: the public Learning Commons Text Complexity dataset holds one consolidated score per passage, not each expert's rating. The agreement checks here need per-expert labels, so the app can't be run on that dataset as-is.

## How labels are sorted

For each item and criterion:

- **Trusted:** at least 3 of 4 round-1 experts agree. Or, after a split, both round-2 experts give the same label, and it's one of the labels tied at the top in round 1.
- **Re-rate:** round 1 split and there's no round 2 yet. Next step: add 2 new experts.
- **No expert consensus:** round 2 split the same way. Also used when round 2 agrees on a label no round-1 expert gave, since experts then span three levels.

The judge is compared to expert consensus on Trusted labels only. On No expert consensus labels it is never scored right or wrong.

## Thresholds

All thresholds are in `config.py`.

| Setting | Value | Source |
|---|---|---|
| Alpha good / fair | ≥ 0.80 / ≥ 0.67 | Krippendorff's usual cutoffs |
| Trusted share good / fair | ≥ 80% / ≥ 60% | Judgment call |
| Flag a criterion as unclear | Round 1 split on ≥ 45% of its items | Judgment call, set to catch the confusing criterion and not the subjective slice |
| AI self-consistency good / fair | ≥ 90% / ≥ 75% of labels same on all 3 runs | Judgment call |
| Rubric rule is clear | AI alpha ≥ 0.67 and flip rate ≤ 20% | Judgment call |
| Cost inputs | 6 min per label, $60 per expert hour, 2 experts per re-rate | Example values |

## Not built yet

- Uploading your own CSV (the button is there; it shows "coming soon").
- Cost page: items needed for a target margin, plus expert hours and cost.
- Expert pilot step after the AI dry run, and comparing rubric versions.
- Running the AI judge live instead of reading it from the CSV.
- Editable thresholds, Dawid-Skene consensus, rater-group breakdowns, more evaluator profiles.

## Layout

```
app.py          header and tabs
engine/         stats: load, consensus, alpha, buckets, ai_checks, statistics
rubric/         dry_run.py (calls models), analyze.py (Clear? per criterion)
views/          one file per tab; views only render engine results
profiles/       rubric text per criterion and level
simulate.py     writes the simulated ratings
config.py       thresholds and example values
```

Every engine module returns a `ModuleResult` (value, status, one-line reading, details). The pages display these results and never compute stats themselves.

## Deploy

DigitalOcean App Platform from GitHub. The run command is in `Procfile`.
