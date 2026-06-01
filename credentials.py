"""Loads required credentials from environment variables."""

import os
import sys

REQUIRED_ENV_VARS = [
    "CLOUDFLARE_API_TOKEN",
    "CLOUDFLARE_ACCOUNT_ID",
    "SPLUNK_URL",
    "SPLUNK_TOKEN",
    "DYNATRACE_URL",
]


def load_credentials() -> dict:
    """Returns a dict of credential values from environment variables.

    Exits immediately with a clear error if any variable is missing.
    Run setup_env.py first to populate the environment from credentials.txt.
    """
    creds = {key: os.environ.get(key, "") for key in REQUIRED_ENV_VARS}
    missing = [k for k, v in creds.items() if not v]
    if missing:
        print(f"✗ ERROR: Missing environment variables: {', '.join(missing)}")
        print("  Run  python setup_env.py  first to load credentials from credentials.txt")
        sys.exit(1)
    return creds
