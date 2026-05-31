# Bedtime Story Safety Pipeline

This is a compact Python CLI for generating child-safe bedtime stories for ages 5-10. It keeps the original assignment's `gpt-3.5-turbo` model, while using the current OpenAI Python client with a legacy SDK fallback. Story generation is wrapped in a small quality and safety pipeline.

The goal is not just to produce a creative story. The system should preserve harmless user intent while making the final story age-appropriate, calm, emotionally warm, and sleep-friendly.

## How to Run

1. Install the OpenAI Python package if needed:

```bash
pip install openai
```

2. Set your API key:

```bash
export OPENAI_API_KEY=your_api_key_here
```

3. Run the CLI:

```bash
python main.py
```

The program asks:

```text
What kind of bedtime story would you like?
```

It then prints a story card followed by the final bedtime story.

## Batch Validation

Run the lightweight mock suite without spending API calls:

```bash
python tests.py --mock --verbose
```

Run the same prompts against OpenAI after setting `OPENAI_API_KEY`:

```bash
python tests.py --verbose --show-story
```

The validation runner prints each prompt's title, word count, judge score, safety score, story-quality scores, validator failures, and pass/check result.
Use `--show-story` when you want the full story card and final story text for every prompt.
It also prints which pipeline stage was accepted, so a broken final taper can be seen falling back to the last passing full story.

## Environment Setup

Copy `.env.example` if you use a shell or environment loader:

```bash
OPENAI_API_KEY=your_api_key_here
```

Do not commit a real API key.

## Architecture

```text
+--------------------+
| User Story Request |
+---------+----------+
          |
          v
+-----------------------------+
| Story Spec Builder          |
| Extracts characters, theme, |
| tone, constraints, age fit  |
+-------------+---------------+
              |
              v
+-----------------------------+
| Safety Transformer          |
| Converts risky premises into|
| child-safe story specs      |
+-------------+---------------+
              |
              v
+-----------------------------+
| Storyteller                 |
| Writes bedtime story        |
| from the safe spec          |
+-------------+---------------+
              |
              v
+-----------------------------+
| Deterministic Validators    |
| Word count, title, required |
| characters, ending cues     |
+-------------+---------------+
              |
              v
+-----------------------------+
| LLM Judge                   |
| Scores safety, age fit,     |
| bedtime tone, story arc     |
+-------------+---------------+
              |
              v
+-----------------------------+
| Targeted Rewriter           |
| Fixes failed gates only     |
+-------------+---------------+
              |
              v
+-----------------------------+
| Final Bedtime Taper         |
| Softens ending for sleep    |
+-------------+---------------+
              |
              v
+-----------------------------+
| Story Card + Final Story    |
+-----------------------------+
```

## Design Decisions

The pipeline starts by building a structured story spec instead of passing the raw request directly to the storyteller. This lets the system preserve harmless user intent while transforming risky ideas, such as scary monsters or intense danger, into gentle bedtime-safe premises. The spec also includes a compact story spine: child takeaway, gentle pulse, character arc, connected plot beats, and a bedtime taper plan.

I avoided relying only on a single LLM score because scores can be noisy. The deterministic validators handle checks Python can do reliably: word count, title shape, requested character presence, obvious banned terms, and calm ending cues.

The LLM judge uses hard gates for safety, age appropriateness, bedtime calmness, and ending softness. A story can be imaginative and still fail if it is too intense for bedtime. It also scores character arc, plot coherence, and bedtime taper so safe-but-random stories can be revised. The prompts use structural references to classic bedtime books, such as narrowing attention, gentle repetition, quiet sensory detail, homecoming, and earned stillness. They do not copy copyrighted text. The prompts and validators discourage moral-summary language, so the child takeaway has to appear through a small action or image instead of being announced. The judge returns targeted edit instructions instead of generic feedback, which makes the revision pass focused and easy to explain.

Revision rounds are capped to control latency, cost, and prevent infinite loops. The final bedtime taper is specific to the use case: a bedtime story should become calmer near the end, not more exciting. If that taper produces an invalid shortened fragment, the pipeline falls back to the last passing full story.

## Why This Is Better Than Simple Score-Threshold Judging

A simple "score the story and retry if below 8" loop is brittle. It does not explain what failed, and it can waste retries rewriting good parts of the story. This implementation separates responsibilities:

- Deterministic validators check objective constraints.
- The judge evaluates subjective quality and child safety.
- Hard gates prevent a high creativity score from masking safety or bedtime-tone issues.
- The targeted rewriter fixes only the failed gates and requested edits.
- The bedtime taper polishes the final emotional landing.

That combination makes the system more trustworthy and easier to debug in a review.

## What I Would Build Next With 2 More Hours

1. A small automated evaluation harness that runs 20 story prompts and summarizes judge and validator pass rates.
2. Better age-level adaptation for 5-7 vs. 8-10 year olds.
3. A parent/teacher mode that can request themes like confidence, grief, sharing, or first day of school.
4. More robust safety testing for scary or emotionally intense prompts.

## Example Prompts to Test

```text
A story about a girl named Alice and her best friend Bob, who is a cat.
A dragon who loses his roar and learns to ask for help.
A scary monster chasing kids through a forest.
A robot who cannot fall asleep.
A space adventure that is exciting but not scary.
A shy cloud who wants to make friends with the moon.
```
