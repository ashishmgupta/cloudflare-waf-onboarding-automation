"""Console output helpers for step progress and API error reporting."""

import json

LINE = "═" * 66
DIVIDER = "─" * 66


def log_step(num: int, total: int, description: str):
    print(f"\n{LINE}")
    print(f"[STEP {num}/{total}] {description}")
    print(LINE)


def log_success(message: str, resource_id: str = ""):
    suffix = f" (ID: {resource_id})" if resource_id else ""
    print(f"✓ SUCCESS: {message}{suffix}")


def log_error(step_name: str, response: dict):
    print(f"✗ ERROR: {step_name} failed")
    print("─── Full API Response ───")
    print(json.dumps(response, indent=2))
    print("────────────────────────")


def log_warn(message: str):
    print(f"\n{DIVIDER}")
    print(f"⚠  {message}")
    print(DIVIDER)
