"""
Hippocratic AI Coding Assignment
Bedtime Story Generator for ages 5-10

If I had 2 more hours, I would add:
1. A lightweight evaluation harness that runs 20 prompts and summarizes judge/validator pass rates.
2. Better age adaptation for 5-7 vs. 8-10 year olds.
3. A parent/teacher mode for themes like confidence, sharing, first day of school, or grief.
4. More robust safety test cases for scary, intense, or emotionally sensitive prompts.
"""

import json
import os
import re
from typing import Any, Dict, List, Tuple

import openai


# -----------------------------
# Configuration
# -----------------------------

MODEL_NAME = "gpt-3.5-turbo"  # Assignment constraint: do not change this model.

QUALITY_THRESHOLD = 8.0
MAX_REVISION_ROUNDS = 2

MIN_WORDS = 350
MAX_WORDS = 900
TARGET_WORDS = "450-650"
TARGET_AGE_RANGE = "5-10"

HARD_GATE_MINIMUMS = {
    "safety": 9,
    "age_fit": 8,
    "bedtime_quality": 8,
}

DEFAULT_MUST_AVOID = [
    "graphic violence or injury",
    "horror or intense fear",
    "adult or sexual themes",
    "medical, legal, or mental-health advice",
    "bullying, cruelty, or exclusion presented positively",
    "weapons or realistic danger",
    "death, grief, or abandonment as a major focus",
    "sad, scary, or unresolved ending",
]

BEDTIME_REQUIREMENTS = [
    "clear beginning, middle, and end",
    "small gentle conflict",
    "peaceful resolution",
    "calm final paragraph",
    "no cliffhanger",
]

OBVIOUS_UNSAFE_TERMS = [
    "blood",
    "bloody",
    "gore",
    "gory",
    "murder",
    "suicide",
    "corpse",
    "dead body",
    "gun",
    "knife",
    "terror",
    "terrifying",
    "horror",
]

CALM_ENDING_CUES = [
    "sleep",
    "dream",
    "dreams",
    "moon",
    "quiet",
    "cozy",
    "rest",
    "goodnight",
    "stars",
    "pillow",
    "home",
    "blanket",
]

SAFETY_POLICY = """
Safety policy:
- The story is for children ages 5-10.
- Do not include graphic violence, horror, adult themes, medical advice, cruelty, or a frightening ending.
- If the user's request includes scary or intense material, preserve the harmless imaginative idea but make it gentle and child-safe.
- Conflict should be mild, emotionally understandable, and resolved safely.
""".strip()

BEDTIME_POLICY = """
Bedtime policy:
- This is a bedtime story, not a high-energy adventure.
- The ending should become quieter and more reassuring.
- Avoid cliffhangers, sudden danger, chaotic action, or loud final moments.
- End with safety, warmth, rest, home, sleep, moonlight, dreams, or quiet comfort.
""".strip()

STYLE_POLICY = """
Story style:
- Use concrete, child-friendly language.
- Show feelings through small actions, sensory details, and simple dialogue when it helps.
- Use a clear beginning, middle, and end.
- Include one small challenge and one kind or brave choice.
- Keep dialogue brief, warm, and natural; do not force it into every scene.
- Avoid generic moral lines like "the real treasure was friendship."
- Include a short title as the first line, then a blank line, then the story.
""".strip()


# -----------------------------
# OpenAI call
# -----------------------------

def call_model(prompt: str, max_tokens: int = 3000, temperature: float = 0.2) -> str:
    """
    Calls OpenAI with the assignment's required model.

    Supports both older and newer OpenAI Python SDK styles.
    The API key must be provided through OPENAI_API_KEY.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Run: export OPENAI_API_KEY='your_api_key_here'"
        )

    # OpenAI Python >= 1.0 uses an explicit client. Older versions expose
    # ChatCompletion directly, so keep that path as a compatibility fallback.
    if hasattr(openai, "OpenAI"):
        client = openai.OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return (resp.choices[0].message.content or "").strip()

    openai.api_key = api_key
    resp = openai.ChatCompletion.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
        stream=False,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return resp.choices[0].message["content"].strip()  # type: ignore[index]


# -----------------------------
# Utility functions
# -----------------------------

def safe_json_loads(raw: str, fallback: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parses LLM JSON safely.

    First tries normal json.loads.
    If the model wrapped JSON in text, tries extracting the first JSON object.
    If parsing still fails, returns fallback.
    """
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else fallback
    except Exception:
        pass

    if isinstance(raw, str):
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                parsed = json.loads(raw[start : end + 1])
                return parsed if isinstance(parsed, dict) else fallback
            except Exception:
                pass

    return fallback


def count_words(text: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b", text))


def extract_title(story: str) -> str:
    """
    Uses the first non-empty line as title if it looks title-like.
    """
    lines = [line.strip() for line in story.splitlines() if line.strip()]
    if not lines:
        return "Untitled Bedtime Story"

    first = lines[0].replace("Title:", "").strip()
    words = first.split()

    if 1 <= len(words) <= 10 and not first.endswith("."):
        return first

    return "Untitled Bedtime Story"


def lower_text_contains_any(text: str, terms: List[str]) -> List[str]:
    lower = text.lower()
    return [term for term in terms if term.lower() in lower]


def normalize_score_aliases(judge_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Keeps the core pipeline score names and validation-harness score names aligned.
    """
    scores = judge_result.get("scores", {}) or {}

    alias_groups = [
        ("bedtime_quality", "bedtime_calmness", "ending_softness", "bedtime_taper"),
        ("story_quality", "story_arc", "character_arc", "plot_coherence"),
    ]

    for names in alias_groups:
        positive_alias_values = [
            scores.get(name)
            for name in names
            if scores.get(name) is not None and float(scores.get(name) or 0) > 0
        ]
        value = positive_alias_values[0] if positive_alias_values else None
        if value is not None:
            for name in names:
                if scores.get(name) is None or float(scores.get(name) or 0) <= 0:
                    scores[name] = value

    judge_result["scores"] = scores
    return judge_result


def numeric_score(judge_result: Dict[str, Any], key: str) -> float:
    return float((judge_result.get("scores", {}) or {}).get(key, 0) or 0)


# -----------------------------
# Story spec builder
# -----------------------------

def default_story_spec(user_request: str) -> Dict[str, Any]:
    return {
        "original_request": user_request,
        "safe_request": user_request,
        "target_age_range": TARGET_AGE_RANGE,
        "main_characters": [],
        "setting": "",
        "tone": "gentle, warm, bedtime-appropriate",
        "theme": "kindness and gentle courage",
        "must_include": [],
        "must_avoid": DEFAULT_MUST_AVOID,
        "safety_notes": "",
        "bedtime_requirements": BEDTIME_REQUIREMENTS,
    }


def build_story_spec(user_request: str) -> Dict[str, Any]:
    """
    Converts the user's request into a structured, child-safe story contract.

    This makes the rest of the system easier to judge:
    the story is not just evaluated as "good" or "bad";
    it is evaluated against a clear spec.
    """
    fallback = default_story_spec(user_request)

    prompt = f"""
You are a careful children's bedtime story planner.

Turn the user's request into a safe story specification for children ages {TARGET_AGE_RANGE}.

{SAFETY_POLICY}

Return JSON only. Do not include markdown.

Required JSON shape:
{{
  "original_request": "...",
  "safe_request": "...",
  "target_age_range": "{TARGET_AGE_RANGE}",
  "main_characters": ["..."],
  "setting": "...",
  "tone": "gentle, warm, bedtime-appropriate",
  "theme": "...",
  "must_include": ["..."],
  "must_avoid": ["graphic violence", "horror", "adult themes", "medical advice", "sad or frightening ending"],
  "safety_notes": "...",
  "bedtime_requirements": ["clear beginning, middle, and end", "small gentle conflict", "peaceful resolution", "calm final paragraph", "no cliffhanger"]
}}

Guidance:
- Preserve harmless user intent.
- If the request is scary, violent, or intense, convert it into a gentle version.
- Keep the story premise simple enough for ages {TARGET_AGE_RANGE}.

User request:
{user_request}
""".strip()

    raw = call_model(prompt, max_tokens=1200, temperature=0.1)
    spec = safe_json_loads(raw, fallback)

    # Ensure required fields exist even if model omits them.
    merged = fallback.copy()
    merged.update(spec)
    return merged


# -----------------------------
# Story generation
# -----------------------------

def generate_story(spec: Dict[str, Any]) -> str:
    """
    Generates the first story draft from the safe spec.
    """
    prompt = f"""
You are a warm bedtime storyteller for children ages {TARGET_AGE_RANGE}.

Write a bedtime story using this story specification:

{json.dumps(spec, indent=2)}

{SAFETY_POLICY}

{BEDTIME_POLICY}

{STYLE_POLICY}

Length:
- Aim for {TARGET_WORDS} words.
- Minimum {MIN_WORDS}, maximum {MAX_WORDS}.

Return only the title and story. Do not include analysis, metadata, rubric scores, or notes.
""".strip()

    return call_model(prompt, max_tokens=2200, temperature=0.45)


# -----------------------------
# Deterministic validators
# -----------------------------

def run_validators(story: str, spec: Dict[str, Any]) -> Dict[str, Any]:
    """
    Runs lightweight deterministic checks.

    These are not a complete safety system.
    They only catch simple issues that Python can check more reliably than an LLM:
    word count, title presence, obvious unsafe terms, and whether requested characters appear.
    """
    failed_checks: List[str] = []
    warnings: List[str] = []

    word_count = count_words(story)

    if word_count < MIN_WORDS:
        failed_checks.append(f"word_count_too_short:{word_count}")

    if word_count > MAX_WORDS:
        failed_checks.append(f"word_count_too_long:{word_count}")

    title = extract_title(story)
    if title == "Untitled Bedtime Story":
        warnings.append("title_missing_or_unclear")

    unsafe_hits = lower_text_contains_any(story, OBVIOUS_UNSAFE_TERMS)
    if unsafe_hits:
        failed_checks.append(f"obvious_unsafe_terms:{', '.join(unsafe_hits)}")

    # Main character check is useful but should not be too strict.
    characters = spec.get("main_characters") or []
    if characters:
        story_lower = story.lower()
        mentioned = False

        for character in characters:
            if not isinstance(character, str):
                continue

            # Check full character phrase and capitalized name-like pieces.
            character_lower = character.lower()
            name_parts = re.findall(r"[A-Za-z]+", character_lower)

            if character_lower in story_lower:
                mentioned = True
                break

            if any(len(part) > 2 and part in story_lower for part in name_parts):
                mentioned = True
                break

        if not mentioned:
            failed_checks.append("main_character_not_mentioned")

    ending = story[-700:].lower()
    if not any(cue in ending for cue in CALM_ENDING_CUES):
        warnings.append("ending_may_need_stronger_bedtime_cue")

    return {
        "passed": len(failed_checks) == 0,
        "failed_checks": failed_checks,
        "warnings": warnings,
        "word_count": word_count,
        "title": title,
    }


# -----------------------------
# LLM judge
# -----------------------------

def default_judge_result() -> Dict[str, Any]:
    return {
        "decision": "revise",
        "overall_score": 0,
        "failed_gates": ["judge_json_parse_failed"],
        "scores": {
            "safety": 0,
            "age_fit": 0,
            "bedtime_quality": 0,
            "story_quality": 0,
        },
        "specific_issues": ["The judge response could not be parsed as valid JSON."],
        "edit_instructions": [
            "Return a safe, age-appropriate, calm bedtime story with a clear ending."
        ],
        "parent_note": "Judge output could not be parsed.",
    }


def judge_story(
    story: str,
    spec: Dict[str, Any],
    validator_result: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Uses the LLM as an editor/judge.

    The judge returns a decision and targeted edit instructions.
    It is not just a generic score.
    """
    fallback = default_judge_result()

    prompt = f"""
You are a strict but fair children's bedtime story editor and safety reviewer.

Evaluate the story against the story specification, validator results, and bedtime requirements.

Story specification:
{json.dumps(spec, indent=2)}

Validator result:
{json.dumps(validator_result, indent=2)}

Story:
\"\"\"
{story}
\"\"\"

Judge using only these four score dimensions:
1. safety: Is it safe and appropriate for ages {TARGET_AGE_RANGE}?
2. age_fit: Is the language and plot suitable for ages {TARGET_AGE_RANGE}?
3. bedtime_quality: Is it calm, reassuring, and sleep-friendly, especially near the end?
4. story_quality: Is it coherent, warm, imaginative, and satisfying?

Hard gates:
- safety must be >= {HARD_GATE_MINIMUMS["safety"]}
- age_fit must be >= {HARD_GATE_MINIMUMS["age_fit"]}
- bedtime_quality must be >= {HARD_GATE_MINIMUMS["bedtime_quality"]}
- overall_score must be >= {QUALITY_THRESHOLD}

Return JSON only. Do not include markdown.

Required JSON shape:
{{
  "decision": "accept" or "revise",
  "overall_score": 0-10,
  "failed_gates": ["..."],
  "scores": {{
    "safety": 0-10,
    "age_fit": 0-10,
    "bedtime_quality": 0-10,
    "story_quality": 0-10
  }},
  "specific_issues": ["..."],
  "edit_instructions": ["..."],
  "parent_note": "One short sentence for a parent explaining the theme and bedtime suitability."
}}

Rules:
- If any hard gate fails, decision must be "revise".
- If validator_result has failed_checks, decision should usually be "revise".
- Warnings do not automatically require revision unless they affect bedtime quality.
- Edit instructions must be specific and actionable.
- Do not rewrite the story.
""".strip()

    raw = call_model(prompt, max_tokens=1400, temperature=0.1)
    result = safe_json_loads(raw, fallback)

    # Normalize missing fields.
    normalized = fallback.copy()
    normalized.update(result)

    scores = fallback["scores"].copy()
    scores.update(normalized.get("scores", {}))
    normalized["scores"] = scores

    return normalize_score_aliases(normalized)


def needs_revision(
    judge_result: Dict[str, Any],
    validator_result: Dict[str, Any],
) -> bool:
    """
    Decides whether to revise.

    Deterministic failed checks are hard failures.
    Validator warnings are soft signals and do not automatically trigger revision.
    """
    if validator_result.get("failed_checks"):
        return True

    decision = str(judge_result.get("decision", "")).lower()
    if decision == "revise":
        return True

    overall = float(judge_result.get("overall_score", 0) or 0)
    if overall < QUALITY_THRESHOLD:
        return True

    scores = judge_result.get("scores", {}) or {}

    for gate, minimum in HARD_GATE_MINIMUMS.items():
        score = float(scores.get(gate, 0) or 0)
        if score < minimum:
            return True

    return False


# -----------------------------
# Revision and bedtime taper
# -----------------------------

def revise_story(
    story: str,
    spec: Dict[str, Any],
    judge_result: Dict[str, Any],
    validator_result: Dict[str, Any],
) -> str:
    """
    Revises the story using targeted judge instructions.
    """
    prompt = f"""
You are revising a children's bedtime story for ages {TARGET_AGE_RANGE}.

Revise the story only as much as needed to fix the issues below.

Story specification:
{json.dumps(spec, indent=2)}

Validator result:
{json.dumps(validator_result, indent=2)}

Judge result:
{json.dumps(judge_result, indent=2)}

Original story:
\"\"\"
{story}
\"\"\"

{SAFETY_POLICY}

{BEDTIME_POLICY}

{STYLE_POLICY}

Revision rules:
- Preserve the same main characters, setting, and core idea.
- Fix failed validator checks and judge gates.
- Do not add new danger, conflict, or high-energy action.
- Keep the story between {MIN_WORDS} and {MAX_WORDS} words.
- Return only the revised title and story.
""".strip()

    return call_model(prompt, max_tokens=2400, temperature=0.25)


def apply_bedtime_taper(story: str, spec: Dict[str, Any]) -> str:
    """
    Final use-case-specific polish.

    A bedtime story should lower emotional energy near the end.
    This pass asks the model to soften only the ending while preserving the story.
    """
    prompt = f"""
You are doing a final bedtime polish for a children's story.

Keep the story mostly unchanged.
Only soften the final 20-25% so the ending feels calmer and more sleep-friendly.

Story specification:
{json.dumps(spec, indent=2)}

Story:
\"\"\"
{story}
\"\"\"

{BEDTIME_POLICY}

Rules:
- Preserve the plot, title, characters, and meaning.
- Do not add new conflict or new events.
- Reduce suspense, loud excitement, or exclamation-heavy language near the end.
- End with quiet comfort, safety, rest, home, sleep, moonlight, or dreams.
- Return only the polished title and story.
""".strip()

    return call_model(prompt, max_tokens=2400, temperature=0.2)


# -----------------------------
# Output formatting
# -----------------------------

def make_story_card(
    story: str,
    spec: Dict[str, Any],
    judge_result: Dict[str, Any],
    validator_result: Dict[str, Any],
    revision_rounds: int,
    accepted_stage: str,
) -> str:
    title = extract_title(story)
    scores = judge_result.get("scores", {}) or {}

    parent_note = judge_result.get(
        "parent_note",
        "This story is designed to be gentle, age-appropriate, and sleep-friendly.",
    )

    return f"""
STORY CARD
Title: {title}
Age Range: {spec.get("target_age_range", TARGET_AGE_RANGE)}
Tone: {spec.get("tone", "Gentle bedtime")}
Theme: {spec.get("theme", "Kindness and gentle courage")}
Judge Score: {judge_result.get("overall_score", "N/A")}/10
Safety: {scores.get("safety", "N/A")}/10
Age Fit: {scores.get("age_fit", "N/A")}/10
Bedtime Quality: {scores.get("bedtime_quality", "N/A")}/10
Story Quality: {scores.get("story_quality", "N/A")}/10
Revision Rounds: {revision_rounds}
Accepted Stage: {accepted_stage}
Word Count: {validator_result.get("word_count", "N/A")}
Parent Note: {parent_note}
""".strip()


def candidate_passes(
    judge_result: Dict[str, Any],
    validator_result: Dict[str, Any],
) -> bool:
    return not needs_revision(judge_result, validator_result)


# -----------------------------
# Main pipeline
# -----------------------------

def generate_final_story(user_request: str) -> Tuple[str, Dict[str, Any]]:
    """
    Full generation pipeline.

    The system keeps the best passing candidate so that a final polish step
    cannot accidentally degrade an already acceptable story.
    """
    spec = build_story_spec(user_request)

    story = generate_story(spec)
    validators = run_validators(story, spec)
    judge = judge_story(story, spec, validators)
    iteration_history = [
        {
            "stage": "initial_draft",
            "validator_result": validators,
            "judge_result": judge,
        }
    ]

    best_passing_story = None
    best_passing_judge = None
    best_passing_validators = None
    best_passing_stage = None

    if candidate_passes(judge, validators):
        best_passing_story = story
        best_passing_judge = judge
        best_passing_validators = validators
        best_passing_stage = "initial_draft"

    revision_rounds = 0

    while revision_rounds < MAX_REVISION_ROUNDS and needs_revision(judge, validators):
        revision_rounds += 1

        story = revise_story(story, spec, judge, validators)
        validators = run_validators(story, spec)
        judge = judge_story(story, spec, validators)
        iteration_history.append(
            {
                "stage": f"revision_{revision_rounds}",
                "validator_result": validators,
                "judge_result": judge,
            }
        )

        if candidate_passes(judge, validators):
            best_passing_story = story
            best_passing_judge = judge
            best_passing_validators = validators
            best_passing_stage = f"revision_{revision_rounds}"

    # Final bedtime-specific polish.
    tapered_story = apply_bedtime_taper(story, spec)
    tapered_validators = run_validators(tapered_story, spec)
    tapered_judge = judge_story(tapered_story, spec, tapered_validators)
    iteration_history.append(
        {
            "stage": "bedtime_taper",
            "validator_result": tapered_validators,
            "judge_result": tapered_judge,
        }
    )

    if candidate_passes(tapered_judge, tapered_validators):
        final_story = tapered_story
        final_validators = tapered_validators
        final_judge = tapered_judge
        accepted_stage = "bedtime_taper"
    elif best_passing_story is not None:
        final_story = best_passing_story
        final_validators = best_passing_validators or validators
        final_judge = best_passing_judge or judge
        accepted_stage = best_passing_stage or "best_passing_candidate"
    else:
        # If nothing fully passes, return the latest version honestly.
        final_story = tapered_story
        final_validators = tapered_validators
        final_judge = tapered_judge
        accepted_stage = "latest_candidate_with_warnings"

    story_card = make_story_card(
        final_story,
        spec,
        final_judge,
        final_validators,
        revision_rounds,
        accepted_stage,
    )

    metadata = {
        "spec": spec,
        "judge": final_judge,
        "judge_result": final_judge,
        "validators": final_validators,
        "validator_result": final_validators,
        "revision_rounds": revision_rounds,
        "accepted_stage": accepted_stage,
        "story_card": story_card,
        "iteration_history": iteration_history,
    }

    return final_story, metadata


# -----------------------------
# CLI
# -----------------------------

def main() -> None:
    print("Bedtime Story Generator for ages 5-10")
    print("-" * 45)

    user_request = input("What kind of bedtime story would you like? ").strip()

    if not user_request:
        print("Please provide a story idea.")
        return

    try:
        story, metadata = generate_final_story(user_request)
    except Exception as exc:
        print(f"\nSorry, something went wrong: {exc}")
        return

    print("\n" + metadata["story_card"])
    print("\n" + "=" * 45 + "\n")
    print(story)


if __name__ == "__main__":
    main()
