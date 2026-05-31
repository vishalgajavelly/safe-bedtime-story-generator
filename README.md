# Bedtime Story Generator

A Python command-line app that turns a simple story idea into a gentle bedtime story for children ages 5-10.

The app uses OpenAI's `gpt-3.5-turbo` model and wraps generation in a small review pipeline so the final story is age-appropriate, calm, coherent, and sleep-friendly.

## Features

- Accepts a free-form bedtime story request from the user.
- Converts the request into a structured child-safe story plan.
- Softens scary or intense ideas into gentle, age-appropriate premises.
- Generates a complete story with a title, clear arc, and calm ending.
- Uses deterministic checks for word count, title, unsafe terms, character coverage, and bedtime cues.
- Uses an LLM judge to score safety, age fit, bedtime quality, and story quality.
- Revises weak drafts once, then applies a final bedtime polish.
- Prints a short story card with quality scores and parent-facing context.

## Project Files

```text
main.py                 Main CLI and story generation pipeline
tests.py                Validation runner with mock and live OpenAI modes
test_prompts.txt        Sample prompts for manual testing
validation_results.txt  Saved live validation output
.env.example            Example environment variable file
```

## Setup

Install the OpenAI Python package:

```bash
pip install openai
```

Set your OpenAI API key:

```bash
export OPENAI_API_KEY=your_api_key_here
```

Do not commit a real API key.

## Run

Start the interactive CLI:

```bash
python main.py
```

Example prompt:

```text
A dragon who loses his roar and learns to ask for help.
```

The app prints a story card followed by the final bedtime story.

## Validate

Run the local mock validation suite without using API credits:

```bash
python tests.py --mock --verbose
```

Run the same validation prompts against OpenAI:

```bash
python tests.py --verbose --show-story
```

The validation runner reports each prompt's title, word count, judge score, safety score, validator failures, accepted pipeline stage, and pass/fail result.

## Architecture

```text
User request
    |
    v
Story spec builder
    |
    v
Safe story plan
    |
    v
Story generator
    |
    v
Deterministic validators
    |
    v
LLM judge
    |
    +--> accepted draft
    |
    +--> targeted revision, if needed
             |
             v
Final bedtime polish
    |
    v
Story card + final story
```

## How It Works

1. `build_story_spec` turns the user request into a structured plan with characters, tone, theme, safety notes, and bedtime requirements.
2. `generate_story` writes the first story from that plan.
3. `run_validators` checks objective constraints in Python.
4. `judge_story` asks the LLM to review the story and return structured JSON scores.
5. `revise_story` makes one targeted revision if the draft fails validation or judge gates.
6. `apply_bedtime_taper` softens the ending so the story lands quietly.

The model name remains `gpt-3.5-turbo` as required by the assignment.

## Validation Summary

The included validation run passed all six sample prompts:

```text
Summary: 6/6 passed
```

Sample prompts include friendship stories, a gentle dragon story, a scary premise converted into a safe version, a sleepless robot, a calm space adventure, and a shy cloud befriending the moon.

## Future Improvements

- Add age-specific modes for younger and older children within the 5-10 range.
- Add an optional parent/teacher theme selector.
- Expand the validation suite with more safety and quality edge cases.
- Add a lightweight feedback loop so users can ask for a softer, sillier, shorter, or more magical revision.
