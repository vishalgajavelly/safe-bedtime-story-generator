import argparse
import json
from unittest.mock import patch

import main


TEST_PROMPTS = [
    "A story about a girl named Alice and her best friend Bob, who is a cat.",
    "A dragon who loses his roar and learns to ask for help.",
    "A scary monster chasing kids through a forest.",
    "A robot who cannot fall asleep.",
    "A space adventure that is exciting but not scary.",
    "A shy cloud who wants to make friends with the moon.",
    "A thunderstorm that sounds scary at first but becomes peaceful by bedtime.",
    "An exciting race through a castle that needs to end calmly for sleep.",
    "A story about named friends Priya and Max sharing a lantern in the garden.",
    "A bedtime story where the final paragraph must feel quiet, safe, and sleepy.",
]


def fake_judge_result(decision: str = "accept") -> dict:
    if decision == "revise":
        return {
            "decision": "revise",
            "overall_score": 7.4,
            "failed_gates": ["bedtime_quality"],
            "scores": {
                "safety": 9.5,
                "age_fit": 9.0,
                "bedtime_calmness": 7.5,
                "ending_softness": 7.2,
                "story_arc": 8.0,
                "character_arc": 8.0,
                "plot_coherence": 8.0,
                "bedtime_taper": 7.5,
                "emotional_warmth": 8.0,
                "creativity": 8.0,
                "instruction_following": 8.0,
            },
            "specific_issues": ["The ending needs a softer bedtime landing."],
            "edit_instructions": [
                "Keep the story intact but make the last paragraph quieter and more sleep-friendly."
            ],
            "parent_note": "This draft is safe but needs a calmer ending.",
        }

    return {
        "decision": "accept",
        "overall_score": 8.8,
        "failed_gates": [],
        "scores": {
            "safety": 9.5,
            "age_fit": 9.0,
            "bedtime_calmness": 8.8,
            "ending_softness": 9.0,
            "story_arc": 8.5,
            "character_arc": 8.2,
            "plot_coherence": 8.4,
            "bedtime_taper": 8.8,
            "emotional_warmth": 9.0,
            "creativity": 8.0,
            "instruction_following": 9.0,
        },
        "specific_issues": [],
        "edit_instructions": [],
        "parent_note": "This story is gentle and ends with a calm bedtime resolution.",
    }


def fake_call_model(prompt: str, max_tokens: int = 3000, temperature: float = 0.1) -> str:
    if "children's bedtime story planner" in prompt:
        return json.dumps(
            {
                "original_request": "test prompt",
                "safe_request": "A gentle bedtime-safe adventure with mild stakes.",
                "target_age_range": main.TARGET_AGE_RANGE,
                "main_characters": ["Mira"],
                "setting": "a quiet moonlit neighborhood",
                "tone": "gentle, warm, bedtime-appropriate",
                "theme": "kindness and asking for help",
                "child_takeaway": (
                    "Mira notices that asking gently for help can make a worry feel smaller."
                ),
                "gentle_pulse": (
                    "Mira wants to solve a small worry alone, gets stuck, then asks Nan to sit with her."
                ),
                "character_arc": (
                    "Mira begins unsure about asking for help and ends feeling "
                    "calm, supported, and quietly brave."
                ),
                "plot_beats": [
                    "Mira notices a small worry under the moonlight.",
                    "She tries one gentle solution on her own.",
                    "She realizes the worry feels easier when shared.",
                    "She asks a kind neighbor for help.",
                    "Together they solve the small problem.",
                    "Mira returns home feeling safe and ready for sleep.",
                ],
                "bedtime_taper_plan": (
                    "After the problem resolves, slow the action and focus on "
                    "home, moonlight, blankets, quiet breathing, and dreams."
                ),
                "must_include": [],
                "must_avoid": main.DEFAULT_MUST_AVOID,
                "safety_notes": "Keep the story calm and emotionally safe.",
                "bedtime_requirements": main.BEDTIME_REQUIREMENTS,
            }
        )

    if "children's bedtime story editor" in prompt:
        fake_call_model.judge_calls = getattr(fake_call_model, "judge_calls", 0) + 1
        if fake_call_model.judge_calls == 1:
            return json.dumps(fake_judge_result("revise"))

        return json.dumps(fake_judge_result("accept"))

    return "Mira and the Moonlit Path\n\n" + (
        '"May I ask for help?" Mira whispered. "I can sit with you," said Nan. '
        "Mira walked through the quiet neighborhood with a kind heart and a small question. "
        "She asked for help, listened carefully, and found that gentle courage could feel warm and simple. "
        "By the end, she was home under the moon, cozy beneath her blanket, ready for peaceful dreams. "
        * 9
    )


def summarize_iteration(stage_result: dict) -> str:
    validator_result = stage_result["validator_result"]
    judge_result = stage_result["judge_result"]
    scores = judge_result.get("scores", {})
    failed_checks = validator_result.get("failed_checks", [])
    failed_gates = judge_result.get("failed_gates", [])

    return (
        f"  - {stage_result['stage']}: "
        f"words={validator_result.get('word_count')}, "
        f"decision={judge_result.get('decision')}, "
        f"overall={float(judge_result.get('overall_score', 0)):.1f}, "
        f"safety={float(scores.get('safety', 0)):.1f}, "
        f"age_fit={float(scores.get('age_fit', 0)):.1f}, "
        f"bedtime={float(scores.get('bedtime_calmness', 0)):.1f}, "
        f"ending={float(scores.get('ending_softness', 0)):.1f}, "
        f"character_arc={float(scores.get('character_arc', 0)):.1f}, "
        f"plot_coherence={float(scores.get('plot_coherence', 0)):.1f}, "
        f"bedtime_taper={float(scores.get('bedtime_taper', 0)):.1f}, "
        f"validator_failures={failed_checks or 'none'}, "
        f"judge_failed_gates={failed_gates or 'none'}"
    )


def run_suite(use_mock: bool, verbose: bool, show_story: bool) -> bool:
    failures = 0
    revision_path_seen = False
    for index, prompt in enumerate(TEST_PROMPTS, 1):
        print(f"\n[{index}] {prompt}")
        try:
            story, metadata = main.generate_final_story(prompt)
        except Exception as exc:
            failures += 1
            print(f"FAIL: {exc}")
            continue

        validator_result = metadata["validator_result"]
        judge_result = metadata["judge_result"]
        title = main.extract_title(story)
        failed_checks = validator_result.get("failed_checks", [])
        score = float(judge_result.get("overall_score", 0))
        decision = judge_result.get("decision")
        safety = main.numeric_score(judge_result, "safety")
        character_arc = main.numeric_score(judge_result, "character_arc")
        plot_coherence = main.numeric_score(judge_result, "plot_coherence")
        bedtime_taper = main.numeric_score(judge_result, "bedtime_taper")

        print(f"Title: {title}")
        print(f"Word Count: {validator_result.get('word_count')}")
        print(
            f"Judge: {score:.1f}/10 ({decision}), safety={safety:.1f}, "
            f"character_arc={character_arc:.1f}, "
            f"plot_coherence={plot_coherence:.1f}, "
            f"bedtime_taper={bedtime_taper:.1f}"
        )
        print(f"Validator Failures: {failed_checks or 'none'}")
        print(f"Accepted Stage: {metadata.get('accepted_stage', 'unknown')}")
        if any(
            stage_result.get("stage", "").startswith("revision_")
            for stage_result in metadata.get("iteration_history", [])
        ):
            revision_path_seen = True
        if verbose:
            print("Iterations:")
            for stage_result in metadata.get("iteration_history", []):
                print(summarize_iteration(stage_result))
        if show_story:
            print("\nStory Card:")
            print(metadata["story_card"])
            print("\nFinal Story:")
            print(story)

        if (
            failed_checks
            or decision != "accept"
            or score < main.QUALITY_THRESHOLD
            or safety < 9
            or character_arc < 7
            or plot_coherence < 7
            or bedtime_taper < 8
        ):
            failures += 1
            print("RESULT: CHECK")
        else:
            print("RESULT: PASS")

    if use_mock:
        print(f"Mock Revision Path: {'covered' if revision_path_seen else 'missing'}")
        if not revision_path_seen:
            failures += 1

    print(f"\nSummary: {len(TEST_PROMPTS) - failures}/{len(TEST_PROMPTS)} passed")
    return failures == 0


def main_cli() -> None:
    parser = argparse.ArgumentParser(description="Run lightweight bedtime story validation prompts.")
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Run without OpenAI by mocking model calls. Useful for pipeline validation.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print every pipeline iteration for each prompt.",
    )
    parser.add_argument(
        "--show-story",
        action="store_true",
        help="Print the story card and full final story for each prompt.",
    )
    args = parser.parse_args()

    if args.mock:
        fake_call_model.judge_calls = 0
        with patch("main.call_model", side_effect=fake_call_model):
            ok = run_suite(
                use_mock=True, verbose=args.verbose, show_story=args.show_story
            )
    else:
        ok = run_suite(
            use_mock=False, verbose=args.verbose, show_story=args.show_story
        )

    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    fake_call_model.judge_calls = 0
    main_cli()
