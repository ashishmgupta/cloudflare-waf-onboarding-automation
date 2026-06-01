#!/usr/bin/env python3
"""
Reads credentials.txt and sets each key as a persistent environment variable.

Windows : writes to HKCU\\Environment in the registry (no admin required).
          Open a new terminal after running — or run 'refreshenv' if using Chocolatey.

macOS   : appends / updates export statements in ~/.zshrc (zsh) or ~/.bash_profile (bash).
          Run  source ~/.zshrc  (or open a new terminal) after running.

Usage:
    python setup_env.py
    python setup_env.py --file /path/to/other/credentials.txt
"""

import argparse
import os
import platform
import sys
from pathlib import Path

REQUIRED_KEYS = [
    "CLOUDFLARE_API_TOKEN",
    "CLOUDFLARE_ACCOUNT_ID",
    "SPLUNK_URL",
    "SPLUNK_TOKEN",
    "DYNATRACE_URL",
]


# ─── Credentials file parser ──────────────────────────────────────────────────

def load_credentials_file(creds_path: Path) -> dict:
    if not creds_path.exists():
        print(f"✗ ERROR: credentials file not found: {creds_path}")
        sys.exit(1)

    creds: dict[str, str] = {}
    for line in creds_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        creds[key.strip()] = value.strip()

    missing = [k for k in REQUIRED_KEYS if not creds.get(k)]
    if missing:
        print(f"✗ ERROR: Missing keys in credentials file: {', '.join(missing)}")
        sys.exit(1)

    return {k: creds[k] for k in REQUIRED_KEYS}


# ─── Windows ──────────────────────────────────────────────────────────────────

def set_windows(creds: dict):
    try:
        import winreg
    except ImportError:
        print("✗ ERROR: winreg module not available (are you on Windows?)")
        sys.exit(1)

    print("Platform: Windows")
    print("Writing to HKEY_CURRENT_USER\\Environment ...\n")

    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_SET_VALUE
    ) as reg_key:
        for name, value in creds.items():
            # REG_EXPAND_SZ supports %VAR% expansion; safe for plain strings too
            winreg.SetValueEx(reg_key, name, 0, winreg.REG_EXPAND_SZ, value)
            print(f"  ✓  {name}")

    # Notify running processes (Explorer, etc.) that the environment changed
    _broadcast_windows_env_change()

    print()
    print("✓ Environment variables set permanently for your user account.")
    print("  Open a new terminal for the changes to take effect.")
    print("  (PowerShell users can also run: $env:VAR = [System.Environment]::GetEnvironmentVariable('VAR','User'))")


def _broadcast_windows_env_change():
    """Sends WM_SETTINGCHANGE so Explorer and shells pick up the new values."""
    try:
        import ctypes
        HWND_BROADCAST = 0xFFFF
        WM_SETTINGCHANGE = 0x001A
        SMTO_ABORTIFHUNG = 0x0002
        ctypes.windll.user32.SendMessageTimeoutW(
            HWND_BROADCAST, WM_SETTINGCHANGE, 0, "Environment",
            SMTO_ABORTIFHUNG, 5000, None,
        )
    except Exception:
        pass  # best-effort; not critical


# ─── macOS / Linux ────────────────────────────────────────────────────────────

def set_unix(creds: dict):
    profile = _detect_shell_profile()
    system = "macOS" if platform.system() == "Darwin" else "Linux"
    print(f"Platform: {system}")
    print(f"Shell profile: {profile}\n")

    existing_text = profile.read_text(encoding="utf-8") if profile.exists() else ""
    updated_text = existing_text
    added: list[str] = []
    updated: list[str] = []

    for name, value in creds.items():
        # Wrap value in single quotes to handle special characters safely;
        # escape any single quotes already present in the value.
        safe_value = value.replace("'", "'\\''")
        export_line = f"export {name}='{safe_value}'"

        if f"export {name}=" in updated_text:
            # Replace the existing line in-place
            new_lines = []
            for line in updated_text.splitlines():
                if line.startswith(f"export {name}="):
                    new_lines.append(export_line)
                else:
                    new_lines.append(line)
            updated_text = "\n".join(new_lines)
            updated.append(name)
        else:
            added.append(export_line)

    # Append new keys under a labelled block
    if added:
        if updated_text and not updated_text.endswith("\n"):
            updated_text += "\n"
        updated_text += "\n# Cloudflare WAF onboarding credentials\n"
        updated_text += "\n".join(added) + "\n"

    profile.write_text(updated_text, encoding="utf-8")

    for name in updated:
        print(f"  ✓  {name}  (updated)")
    for line in added:
        name = line.split("=")[0].replace("export ", "")
        print(f"  ✓  {name}  (added)")

    print()
    print("✓ Export statements written.")
    print(f"  Apply in the current terminal with:")
    print(f"    source {profile}")


def _detect_shell_profile() -> Path:
    shell = os.environ.get("SHELL", "")
    home = Path.home()

    if "zsh" in shell:
        return home / ".zshrc"
    if "bash" in shell:
        # macOS: .bash_profile is sourced for login shells; Linux: .bashrc
        candidate = home / ".bash_profile" if platform.system() == "Darwin" else home / ".bashrc"
        return candidate
    # Fallback
    return home / ".profile"


# ─── Entry point ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--file", "-f",
        default=str(Path(__file__).parent / "credentials.txt"),
        help="Path to credentials file (default: credentials.txt next to this script)",
    )
    args = parser.parse_args()

    creds = load_credentials_file(Path(args.file))

    system = platform.system()
    if system == "Windows":
        set_windows(creds)
    elif system in ("Darwin", "Linux"):
        set_unix(creds)
    else:
        print(f"✗ ERROR: Unsupported platform: {system}")
        sys.exit(1)


if __name__ == "__main__":
    main()
