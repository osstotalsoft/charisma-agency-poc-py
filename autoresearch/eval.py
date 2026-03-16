"""
Evaluation harness for agent001.

Runs each test case in a subprocess to avoid module caching issues
when agent.py is modified between iterations.

Entry point: python -m autoresearch.eval
"""

import json
import math
import os
import re
import subprocess
import sys

DATASET_PATH = os.path.join(os.path.dirname(__file__), "dataset.json")

# Subprocess script that runs a single test case
RUNNER_SCRIPT = r'''
import os
import sys

# Force UTF-8 output on Windows
sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv

load_dotenv(".env.local")

from src.agent001.agent import agent

question = sys.argv[1]
result = agent.invoke({"messages": [("user", question)]})

# Get the last AI message
for msg in reversed(result["messages"]):
    if hasattr(msg, "content") and msg.content and not hasattr(msg, "tool_call_id"):
        print(msg.content)
        break
'''


def extract_number(text: str) -> float | None:
    """Extract the most likely answer number from a text response."""
    # Match integers, decimals, and negative numbers (including comma-separated)
    numbers = re.findall(r'-?[\d,]+\.\d+|-?[\d,]+', text)
    if not numbers:
        return None
    # Prefer decimal numbers (more likely to be precise answers)
    decimals = [n for n in numbers if '.' in n]
    if decimals:
        return float(decimals[-1].replace(",", ""))
    # Fall back to the last integer
    return float(numbers[-1].replace(",", ""))


def score(actual: float | None, expected: float) -> float:
    """Score a single response: 1.0 if within 1% relative tolerance, else 0.0."""
    if actual is None:
        return 0.0
    if expected == 0:
        return 1.0 if abs(actual) < 0.01 else 0.0
    if math.isclose(actual, expected, rel_tol=0.01):
        return 1.0
    return 0.0


def run_single(question: str, timeout: int = 60) -> str:
    """Run a single test case in a subprocess, return the agent's text response."""
    try:
        result = subprocess.run(
            [sys.executable, "-c", RUNNER_SCRIPT, question],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=os.path.dirname(os.path.dirname(__file__)),
            encoding="utf-8",
        )
        if result.returncode != 0:
            print(f"  STDERR: {result.stderr.strip()}", file=sys.stderr)
            return ""
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        print(f"  TIMEOUT for: {question}", file=sys.stderr)
        return ""


def evaluate() -> dict:
    """Run all test cases and return aggregate results."""
    with open(DATASET_PATH) as f:
        dataset = json.load(f)

    scores = []
    details = []

    for i, case in enumerate(dataset):
        question = case["input"]
        expected = case["expected"]

        print(f"  [{i+1}/{len(dataset)}] {question}", file=sys.stderr)
        response = run_single(question)
        actual = extract_number(response)
        s = score(actual, expected)
        scores.append(s)

        detail = {
            "input": question,
            "expected": expected,
            "actual": actual,
            "response": response[:200],
            "score": s,
        }
        details.append(detail)
        status = "OK" if s == 1.0 else "FAIL"
        print(f"         {status} expected={expected} actual={actual}", file=sys.stderr)

    result = {
        "score": sum(scores) / len(scores) if scores else 0.0,
        "passed": sum(1 for s in scores if s == 1.0),
        "total": len(scores),
        "details": details,
    }
    return result


if __name__ == "__main__":
    result = evaluate()
    print(json.dumps(result, indent=2))
