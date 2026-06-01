# Cloudflare WAF Zone Onboarding Automation

Automates the creation and security configuration of a Cloudflare Enterprise zone via the Cloudflare REST API v4. A single command runs 12 sequential steps — from zone creation to WAF deployment and log forwarding — and generates an HTML report on completion.

---

## What it does

Running the script against a domain executes these 12 steps in order:

| Step | What happens |
|------|-------------|
| 1 | Creates the zone under your Cloudflare Enterprise account |
| 2 | Adds a proxied A or CNAME record (required for WAF and all security features) |
| 3 | Sets minimum TLS version to **1.2** |
| 4 | Disables **HTTP/2** between client and Cloudflare edge |
| 5 | Sets origin read timeout to **120 seconds** *(Enterprise only)* |
| 6 | Enables **log retention** for a 72-hour Logpull window *(Enterprise only)* |
| 7 | Deploys the **Cloudflare Managed WAF Ruleset** in **log mode** (observe, not block) |
| 8 | Creates a **cache rule** that disables caching for all requests |
| 9 | Creates a **Logpush job**: HTTP requests → Splunk |
| 10 | Creates a **Logpush job**: Firewall events → Splunk |
| 11 | Creates a **Logpush job**: DNS logs → Splunk |
| 12 | Creates a **Logpush job**: HTTP requests → Dynatrace |

> **Note:** Cloudflare allows a maximum of 4 Logpush jobs per zone. Steps 9–12 use all 4 slots.

After all steps complete, the script reminds you to update your domain registrar's nameservers to point to Cloudflare. That step is manual and cannot be automated via the API.

---

## Prerequisites

- **Cloudflare Enterprise account** — steps 5 and 6 require Enterprise entitlements
- **Python 3.9+**
- **`requests` library** — `pip install requests`
- A **Cloudflare API token** with the permissions listed in [API Token Permissions](#api-token-permissions)

---

## Project structure

```
cloudflare_zone_setup.py   ← entry point (CLI)
onboarding.py              ← orchestrates all 12 steps + rollback
cf_client.py               ← Cloudflare HTTP client
credentials.py             ← reads credentials from environment variables
logger.py                  ← console output helpers
reporter.py                ← HTML report generation
logpush_config.py          ← field lists for each Logpush job
setup_env.py               ← loads credentials.txt into environment variables
credentials.txt.example    ← template — copy to credentials.txt and fill in
```

---

## Setup

### 1. Install dependency

```bash
pip install requests
```

### 2. Create your credentials file

```bash
cp credentials.txt.example credentials.txt
```

Fill in `credentials.txt`:

```
CLOUDFLARE_API_TOKEN=your-cloudflare-bearer-token
CLOUDFLARE_ACCOUNT_ID=your-account-id
SPLUNK_URL=https://your-splunk-instance:8088/services/collector/raw
SPLUNK_TOKEN=Splunk your-hec-token-here
DYNATRACE_URL=https://your-environment-id.live.dynatrace.com/api/v2/logs/ingest?header_Authorization=Api-Token%20your-dynatrace-token-here
```

> `credentials.txt` is listed in `.gitignore` and will never be committed.

### 3. Load credentials into environment variables

**Run once per terminal session** (or permanently — see below):

```bash
python setup_env.py
```

- **Windows**: writes to `HKCU\Environment` in the registry (permanent for your user). Open a new terminal after running.
- **macOS / Linux**: appends `export` statements to `~/.zshrc` or `~/.bash_profile`. Run `source ~/.zshrc` after running (or open a new terminal).

---

## Usage

```bash
# A record (IP origin)
python cloudflare_zone_setup.py --zone example.com --record-type A --origin 1.2.3.4

# CNAME record (hostname origin)
python cloudflare_zone_setup.py --zone example.com --record-type CNAME --origin origin.example.com
```

| Argument | Required | Description |
|---|---|---|
| `--zone` | Yes | Domain to onboard, e.g. `example.com` |
| `--record-type` | Yes | `A` or `CNAME` |
| `--origin` | Yes | IP address (A) or hostname (CNAME) |

### Example output

```
══════════════════════════════════════════════════════════════════
[STEP 1/12] Creating Zone: example.com
══════════════════════════════════════════════════════════════════
✓ SUCCESS: Zone created: example.com (ID: abc123...)

[STEP 2/12] Creating A DNS Record → 1.2.3.4
══════════════════════════════════════════════════════════════════
✓ SUCCESS: DNS record: A example.com → 1.2.3.4 (ID: def456...)

...

✓ ALL 12 STEPS COMPLETED SUCCESSFULLY
  Zone:    example.com
  Zone ID: abc123...

  NEXT STEP (manual): Update your domain registrar's nameservers
  to point to Cloudflare. Find assigned nameservers in the
  Cloudflare dashboard under DNS → Nameservers.

HTML Report generated: zone_report_example.com_20260601_143022.html
```

---

## Rollback

If **any step fails**, the script automatically rolls back before exiting:

1. Logs the full Cloudflare API error response to the terminal
2. Calls `DELETE /zones/{zone_id}` to remove the partially-configured zone
3. Prints rollback status (success or failure)
4. Generates the HTML report (including the error and rollback details)
5. Exits with code `1`

**Rollback is safe by design:**

- `zone_id` is set only after Step 1 succeeds — if Step 1 itself fails, there is nothing to delete and rollback is a no-op
- The `DELETE` call targets only the zone ID created during the current run — no other zones in your account are touched
- The HTML report is always generated, even after a failed rollback, so you have a full record of what happened

**What rollback does not undo:**

- Any nameserver changes you made manually at your domain registrar
- Other zones in your account are never affected

---

## HTML Report

A report file named `zone_report_{zone}_{timestamp}.html` is written to the same directory as the script on every run — success or failure.

The report includes:

- **Header** — zone name, zone ID, record type, origin, timestamp, overall status (green / red)
- **Step summary table** — one row per step: status, API endpoint called, resource ID
- **Step details** — collapsible section per step showing the full raw API response JSON
- **Error details** — highlighted in red if a step failed, with the full API error
- **Rollback section** — shown if rollback was triggered, with its own API response

---

## API Token Permissions

Create a **Custom Token** in the Cloudflare dashboard (My Profile → API Tokens → Create Token → Custom Token) with these permissions:

| Category | Permission | Level |
|---|---|---|
| Zone | Zone | Edit |
| Zone | DNS | Edit |
| Zone | Zone Settings | Edit |
| Zone | Firewall Services | Edit |
| Zone | Cache Rules | Edit |
| Zone | Logs | Edit |
| Account | Account Settings | Read |

Set **Zone Resources** to "All zones" (or restrict to specific zones).

---

## Customising Logpush fields

The fields forwarded to each Logpush destination are defined in [`logpush_config.py`](logpush_config.py). Edit the lists there to add or remove fields without touching any other file.

```python
# logpush_config.py
DYNATRACE_HTTP_REQUESTS_FIELDS = [
    "RayID", "ZoneName", "ClientIP", ...
]
```

Full field reference: https://developers.cloudflare.com/logs/reference/log-fields/

---

## Known limitations

- **4 Logpush jobs maximum per zone** — this script uses all 4 slots. Adding more requires deleting an existing job first.
- **Nameserver delegation is manual** — zone creation via API does not activate the zone. You must update your registrar.
- **Enterprise plan required** — `proxy_read_timeout` (step 5) and log retention (step 6) will fail on non-Enterprise zones.
- **WAF starts in log mode** — rules observe traffic but do not block. Change `"action": "log"` to `"action": "block"` in [`onboarding.py`](onboarding.py) when ready to enforce.
- **DNS logs require active traffic** — the DNS Logpush job (step 11) only produces data after nameserver delegation is complete.
