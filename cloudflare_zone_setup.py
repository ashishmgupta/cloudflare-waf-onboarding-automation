#!/usr/bin/env python3
"""
Cloudflare Enterprise Zone Onboarding Automation

Usage:
    python cloudflare_zone_setup.py --zone example.com --record-type A --origin 1.2.3.4
    python cloudflare_zone_setup.py --zone example.com --record-type CNAME --origin origin.example.com

Run  python setup_env.py  first to load credentials from credentials.txt into
environment variables. Dependencies: pip install requests
"""

import argparse

from credentials import load_credentials
from onboarding import ZoneOnboarding


def main():
    parser = argparse.ArgumentParser(
        description="Cloudflare Enterprise Zone Onboarding Automation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cloudflare_zone_setup.py --zone example.com --record-type A --origin 1.2.3.4
  python cloudflare_zone_setup.py --zone example.com --record-type CNAME --origin origin.example.com
        """,
    )
    parser.add_argument("--zone", required=True, help="Domain name, e.g. example.com")
    parser.add_argument("--record-type", required=True, choices=["A", "CNAME"],
                        help="DNS record type: A or CNAME")
    parser.add_argument("--origin", required=True,
                        help="IP address (for A record) or hostname (for CNAME)")
    args = parser.parse_args()

    creds = load_credentials()
    ZoneOnboarding(
        zone_name=args.zone,
        record_type=args.record_type,
        origin=args.origin,
        creds=creds,
    ).run()


if __name__ == "__main__":
    main()
