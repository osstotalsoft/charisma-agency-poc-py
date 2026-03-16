"""
Autoresearch optimization loop for agent001.

Uses an LLM (via OpenAI API) to iteratively propose improvements
to agent001's code, evaluates them, and keeps only improvements.

Entry point: uv run python -m autoresearch.loop
"""

import json
import os
import py_compile
import subprocess
import sys
import tempfile

from dotenv import load_dotenv

load_dotenv(".env.local")

from openai import OpenAI

AGENT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "src", "agent001", "agent.py"
)
PROGRAM_PATH = os.path.join(os.path.dirname(__file__), "program.md")
RESULTS_PATH = os.path.join(os.path.dirname(__file__), "results.tsv")
MAX_ITERATIONS = 20


def read_file(path: str) -> str:
    with open(path) as f:
        return f.read()


def write_file(path: str, content: str) -> None:
    with open(path, "w") as f:
        f.write(content)


def read_results_history() -> str:
    if not os.path.exists(RESULTS_PATH):
        return "No previous iterations."
    with open(RESULTS_PATH) as f:
        return f.read()


def append_result(iteration: int, score: float, passed: int, total: int, action: str, summary: str) -> None:
    header_needed = not os.path.exists(RESULTS_PATH)
    with open(RESULTS_PATH, "a") as f:
        if header_needed:
            f.write("iteration\tscore\tpassed\ttotal\taction\tsummary\n")
        f.write(f"{iteration}\t{score:.4f}\t{passed}\t{total}\t{action}\t{summary}\n")


def propose_improvement(client: OpenAI, current_code: str, history: str, program: str) -> str | None:
    """Ask the optimizer LLM to propose an improved agent.py."""
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": program},
            {
                "role": "user",
                "content": (
                    f"## Current agent.py\n\n```python\n{current_code}\n```\n\n"
                    f"## Results History\n\n```\n{history}\n```\n\n"
                    "Propose an improved version of agent.py. Return the complete file in a ```python code fence."
                ),
            },
        ],
        temperature=0.7,
    )

    text = response.choices[0].message.content or ""

    # Extract code from python fence
    import re
    match = re.search(r'```python\n(.*?)```', text, re.DOTALL)
    if not match:
        print("  ERROR: No python code fence found in optimizer response", file=sys.stderr)
        return None
    return match.group(1).strip() + "\n"


def validate_syntax(code: str) -> bool:
    """Check if code has valid Python syntax."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        tmp_path = f.name
    try:
        py_compile.compile(tmp_path, doraise=True)
        return True
    except py_compile.PyCompileError as e:
        print(f"  SYNTAX ERROR: {e}", file=sys.stderr)
        return False
    finally:
        os.unlink(tmp_path)


def run_eval() -> dict:
    """Run the evaluation harness and return parsed results."""
    result = subprocess.run(
        [sys.executable, "-m", "autoresearch.eval"],
        capture_output=True,
        text=True,
        timeout=1800,
        cwd=os.path.dirname(os.path.dirname(__file__)),
    )
    if result.returncode != 0:
        print(f"  EVAL ERROR:\n{result.stderr}", file=sys.stderr)
        return {"score": 0.0, "passed": 0, "total": 0, "details": []}
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        print(f"  EVAL OUTPUT PARSE ERROR:\n{result.stdout}", file=sys.stderr)
        return {"score": 0.0, "passed": 0, "total": 0, "details": []}


def git_commit(message: str) -> None:
    """Commit the current agent.py changes."""
    subprocess.run(["git", "add", AGENT_PATH], cwd=os.path.dirname(os.path.dirname(__file__)))
    subprocess.run(
        ["git", "commit", "-m", message],
        cwd=os.path.dirname(os.path.dirname(__file__)),
    )


def git_revert() -> None:
    """Revert agent.py to the last committed version."""
    subprocess.run(
        ["git", "checkout", "--", AGENT_PATH],
        cwd=os.path.dirname(os.path.dirname(__file__)),
    )


def summarize_failures(details: list[dict]) -> str:
    """One-line summary of what failed."""
    failures = [d["input"][:40] for d in details if d["score"] == 0.0]
    if not failures:
        return "all passed"
    return f"failed: {'; '.join(failures[:3])}" + (f" (+{len(failures)-3} more)" if len(failures) > 3 else "")


def main():
    client = OpenAI()
    program = read_file(PROGRAM_PATH)

    # Establish baseline
    print("=" * 60)
    print("AUTORESEARCH: Establishing baseline...")
    print("=" * 60)
    baseline = run_eval()
    best_score = baseline["score"]
    print(f"\nBaseline: {baseline['passed']}/{baseline['total']} = {best_score:.4f}")
    append_result(0, best_score, baseline["passed"], baseline["total"], "baseline", summarize_failures(baseline.get("details", [])))

    for iteration in range(1, MAX_ITERATIONS + 1):
        print(f"\n{'=' * 60}")
        print(f"ITERATION {iteration}/{MAX_ITERATIONS} (best={best_score:.4f})")
        print(f"{'=' * 60}")

        current_code = read_file(AGENT_PATH)
        history = read_results_history()

        # Propose improvement
        print("  Proposing improvement...")
        new_code = propose_improvement(client, current_code, history, program)
        if new_code is None:
            append_result(iteration, best_score, 0, 0, "skip", "no code proposed")
            continue

        # Validate syntax
        if not validate_syntax(new_code):
            append_result(iteration, best_score, 0, 0, "skip", "syntax error")
            continue

        # Write new code
        original_code = current_code
        write_file(AGENT_PATH, new_code)

        # Evaluate
        print("  Evaluating...")
        result = run_eval()
        new_score = result["score"]
        summary = summarize_failures(result.get("details", []))

        print(f"  Score: {new_score:.4f} (best={best_score:.4f})")

        if new_score > best_score:
            print(f"  IMPROVED! {best_score:.4f} -> {new_score:.4f}")
            best_score = new_score
            git_commit(f"autoresearch: iteration {iteration}, score {new_score:.4f} ({result['passed']}/{result['total']})")
            append_result(iteration, new_score, result["passed"], result["total"], "keep", summary)
        else:
            print(f"  No improvement, reverting.")
            write_file(AGENT_PATH, original_code)
            append_result(iteration, new_score, result["passed"], result["total"], "revert", summary)

        if best_score >= 1.0:
            print(f"\n{'=' * 60}")
            print("PERFECT SCORE! Stopping.")
            print(f"{'=' * 60}")
            break

    print(f"\nFinal best score: {best_score:.4f}")
    print(f"Results log: {RESULTS_PATH}")


if __name__ == "__main__":
    main()
