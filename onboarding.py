"""Zone onboarding orchestration — runs all 12 configuration steps."""

import json
import sys
import uuid
from datetime import datetime
from pathlib import Path

from cf_client import CloudflareClient, CF_MANAGED_RULESET_ID
from logger import LINE, log_step, log_success, log_error, log_warn
from logpush_config import (
    SPLUNK_HTTP_REQUESTS_FIELDS,
    SPLUNK_FIREWALL_EVENTS_FIELDS,
    SPLUNK_DNS_LOGS_FIELDS,
    DYNATRACE_HTTP_REQUESTS_FIELDS,
)
from reporter import Reporter, StepResult

TOTAL_STEPS = 12


class ZoneOnboarding:
    def __init__(self, zone_name: str, record_type: str, origin: str, creds: dict):
        self.zone_name = zone_name
        self.record_type = record_type
        self.origin = origin
        self.creds = creds
        self.cf = CloudflareClient(creds["CLOUDFLARE_API_TOKEN"])
        self.zone_id = ""
        self.reporter = Reporter(zone_name, record_type, origin)

        # Strip scheme — Cloudflare Splunk destination_conf uses splunk:// prefix
        self.splunk_endpoint = (
            creds["SPLUNK_URL"].removeprefix("https://").removeprefix("http://")
        )
        self.splunk_token = creds["SPLUNK_TOKEN"]

        # DYNATRACE_URL must already include the token as a query parameter, e.g.:
        # https://xxx.live.dynatrace.com/api/v2/logs/ingest?header_Authorization=Api-Token%20xxx
        self.dynatrace_url = creds["DYNATRACE_URL"]

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _check(self, step: StepResult, response: dict, id_path: str = "result.id") -> str:
        """Records the step, exits with rollback+report on API failure."""
        step.response = response
        self.reporter.add_step(step)

        if not response.get("success"):
            step.status = "FAILED"
            step.errors = response.get("errors", [])
            self.reporter.overall_status = "FAILED"
            log_error(step.name, response)
            self._rollback()
            self._write_report()
            sys.exit(1)

        step.status = "SUCCESS"
        resource_id: object = response
        for key in id_path.split("."):
            resource_id = resource_id.get(key, "") if isinstance(resource_id, dict) else ""
        step.resource_id = str(resource_id) if resource_id else ""
        return step.resource_id

    def _rollback(self):
        if not self.zone_id:
            return
        self.reporter.rollback_triggered = True
        print(f"\n{LINE}")
        print(f"[ROLLBACK] Deleting zone {self.zone_id}...")
        print(LINE)
        resp = self.cf.delete(f"/zones/{self.zone_id}")
        if resp.get("success"):
            print(f"✓ ROLLBACK: Zone {self.zone_id} deleted successfully")
            self.reporter.rollback_status = "SUCCESS"
        else:
            print(f"✗ ROLLBACK FAILED: Could not delete zone {self.zone_id}")
            print(json.dumps(resp, indent=2))
            self.reporter.rollback_status = "FAILED"
        self.reporter.rollback_response = resp

    def _write_report(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = Path(__file__).parent / f"zone_report_{self.zone_name}_{timestamp}.html"
        self.reporter.write(self.zone_id, report_path)
        print(f"\n{LINE}")
        print(f"HTML Report generated: {report_path}")
        print(LINE)

    def _splunk_dest(self, channel: str) -> str:
        return (
            f"splunk://{self.splunk_endpoint}"
            f"?channel={channel}"
            f"&insecure-skip-verify=false"
            f"&sourcetype=cloudflare:json"
            f"&header_Authorization={self.splunk_token}"
        )

    def _dynatrace_dest(self) -> str:
        sep = "&" if "?" in self.dynatrace_url else "?"
        return (
            self.dynatrace_url
            + sep
            + "header_accept=application/json"
            + "&header_content-type=application/json"
            + "&dt.ingest.origin=cloudflare"
        )

    def _logpush_output(self, fields: list, **extra) -> dict:
        return {"field_names": fields, "timestamp_format": "rfc3339", **extra}

    # ── Steps ─────────────────────────────────────────────────────────────────

    def _step1_create_zone(self):
        log_step(1, TOTAL_STEPS, f"Creating Zone: {self.zone_name}")
        resp = self.cf.post("/zones", {
            "name": self.zone_name,
            "account": {"id": self.creds["CLOUDFLARE_ACCOUNT_ID"]},
            "jump_start": False,
            "type": "full",
        })
        step = StepResult("Create Zone", "POST /zones")
        self.zone_id = self._check(step, resp)
        log_success(f"Zone created: {self.zone_name}", self.zone_id)

    def _step2_create_dns_record(self):
        log_step(2, TOTAL_STEPS, f"Creating {self.record_type} DNS Record → {self.origin}")
        endpoint = f"POST /zones/{self.zone_id}/dns_records"
        resp = self.cf.post(f"/zones/{self.zone_id}/dns_records", {
            "type": self.record_type,
            "name": self.zone_name,
            "content": self.origin,
            "ttl": 1,
            "proxied": True,
        })
        step = StepResult(f"Create DNS Record ({self.record_type})", endpoint)
        dns_id = self._check(step, resp)
        log_success(f"DNS record: {self.record_type} {self.zone_name} → {self.origin}", dns_id)

    def _step3_set_min_tls(self):
        log_step(3, TOTAL_STEPS, "Setting Minimum TLS Version to 1.2")
        endpoint = f"PATCH /zones/{self.zone_id}/settings/min_tls_version"
        resp = self.cf.patch(f"/zones/{self.zone_id}/settings/min_tls_version", {"value": "1.2"})
        step = StepResult("Set Min TLS Version 1.2", endpoint)
        self._check(step, resp, id_path="result.id")
        step.resource_id = ""
        log_success("Minimum TLS version set to 1.2")

    def _step4_disable_http2(self):
        log_step(4, TOTAL_STEPS, "Disabling HTTP/2 (Client → Edge)")
        endpoint = f"PATCH /zones/{self.zone_id}/settings/http2"
        resp = self.cf.patch(f"/zones/{self.zone_id}/settings/http2", {"value": "off"})
        step = StepResult("Disable HTTP/2", endpoint)
        self._check(step, resp, id_path="result.id")
        step.resource_id = ""
        log_success("HTTP/2 disabled (Client → Cloudflare edge)")

    def _step5_set_origin_timeout(self):
        log_step(5, TOTAL_STEPS, "Setting Origin Read Timeout to 120 Seconds")
        endpoint = f"PATCH /zones/{self.zone_id}/settings/proxy_read_timeout"
        resp = self.cf.patch(f"/zones/{self.zone_id}/settings/proxy_read_timeout", {"value": 120})
        step = StepResult("Set Origin Read Timeout (120s)", endpoint)
        self._check(step, resp, id_path="result.id")
        step.resource_id = ""
        log_success("Origin read timeout set to 120 seconds (Enterprise only)")

    def _step6_enable_log_retention(self):
        log_step(6, TOTAL_STEPS, "Enabling Log Retention (72-hour Logpull window)")
        endpoint = f"PUT /zones/{self.zone_id}/logs/received/settings"
        resp = self.cf.put(f"/zones/{self.zone_id}/logs/received/settings", {"retention": True})
        step = StepResult("Enable Log Retention", endpoint)
        self._check(step, resp, id_path="result.retention")
        step.resource_id = ""
        log_success("Log retention enabled")

    def _step7_deploy_waf(self):
        log_step(7, TOTAL_STEPS, "Deploying WAF Managed Ruleset in Log Mode")
        endpoint = f"PUT /zones/{self.zone_id}/rulesets/phases/http_request_firewall_managed/entrypoint"
        resp = self.cf.put(
            f"/zones/{self.zone_id}/rulesets/phases/http_request_firewall_managed/entrypoint",
            {
                "name": "Zone WAF Managed Rules",
                "description": "Deploy Cloudflare Managed Ruleset in log mode",
                "rules": [{
                    "action": "execute",
                    "action_parameters": {
                        "id": CF_MANAGED_RULESET_ID,
                        "overrides": {
                            "rulesets": [{"action": "log", "enabled": True}]
                        },
                    },
                    "expression": "true",
                    "description": "Execute Cloudflare Managed Ruleset in log mode",
                    "enabled": True,
                }],
            },
        )
        step = StepResult("Deploy WAF Managed Rules (Log Mode)", endpoint)
        waf_id = self._check(step, resp)
        log_success("WAF Managed Ruleset deployed in log mode", waf_id)

    def _step8_disable_cache(self):
        log_step(8, TOTAL_STEPS, "Creating Cache Rule: Disable All Caching")
        endpoint = f"PUT /zones/{self.zone_id}/rulesets/phases/http_request_cache_settings/entrypoint"
        resp = self.cf.put(
            f"/zones/{self.zone_id}/rulesets/phases/http_request_cache_settings/entrypoint",
            {
                "name": "Disable caching for all file types",
                "description": "Disable caching for all file types",
                "rules": [{
                    "action": "set_cache_settings",
                    "action_parameters": {"cache": False},
                    "expression": "true",
                    "description": "Disable caching for all file types",
                    "enabled": True,
                }],
            },
        )
        step = StepResult("Cache Rule: Disable All Caching", endpoint)
        cache_id = self._check(step, resp)
        log_success("Cache rule created — all caching disabled", cache_id)

    def _step9_logpush_splunk_http(self):
        log_step(9, TOTAL_STEPS, "Creating Logpush Job: HTTP Requests → Splunk")
        endpoint = f"POST /zones/{self.zone_id}/logpush/jobs"
        resp = self.cf.post(f"/zones/{self.zone_id}/logpush/jobs", {
            "name": "splunk-http-requests",
            "destination_conf": self._splunk_dest(str(uuid.uuid4())),
            "dataset": "http_requests",
            "output_options": self._logpush_output(SPLUNK_HTTP_REQUESTS_FIELDS),
            "enabled": True,
        })
        step = StepResult("Logpush: HTTP Requests → Splunk", endpoint)
        job_id = self._check(step, resp)
        log_success("Logpush job created: HTTP Requests → Splunk", job_id)

    def _step10_logpush_splunk_firewall(self):
        log_step(10, TOTAL_STEPS, "Creating Logpush Job: Firewall Events → Splunk")
        endpoint = f"POST /zones/{self.zone_id}/logpush/jobs"
        resp = self.cf.post(f"/zones/{self.zone_id}/logpush/jobs", {
            "name": "splunk-firewall-events",
            "destination_conf": self._splunk_dest(str(uuid.uuid4())),
            "dataset": "firewall_events",
            "output_options": self._logpush_output(SPLUNK_FIREWALL_EVENTS_FIELDS),
            "enabled": True,
        })
        step = StepResult("Logpush: Firewall Events → Splunk", endpoint)
        job_id = self._check(step, resp)
        log_success("Logpush job created: Firewall Events → Splunk", job_id)

    def _step11_logpush_splunk_dns(self):
        log_step(11, TOTAL_STEPS, "Creating Logpush Job: DNS Logs → Splunk")
        endpoint = f"POST /zones/{self.zone_id}/logpush/jobs"
        resp = self.cf.post(f"/zones/{self.zone_id}/logpush/jobs", {
            "name": "splunk-dns-logs",
            "destination_conf": self._splunk_dest(str(uuid.uuid4())),
            "dataset": "dns_logs",
            "output_options": self._logpush_output(SPLUNK_DNS_LOGS_FIELDS),
            "enabled": True,
        })
        step = StepResult("Logpush: DNS Logs → Splunk", endpoint)
        job_id = self._check(step, resp)
        log_success("Logpush job created: DNS Logs → Splunk", job_id)

    def _step12_logpush_dynatrace_http(self):
        log_step(12, TOTAL_STEPS, "Creating Logpush Job: HTTP Requests → Dynatrace")
        endpoint = f"POST /zones/{self.zone_id}/logpush/jobs"
        resp = self.cf.post(f"/zones/{self.zone_id}/logpush/jobs", {
            "name": "dynatrace-http-requests",
            "destination_conf": self._dynatrace_dest(),
            "dataset": "http_requests",
            "output_options": self._logpush_output(
                DYNATRACE_HTTP_REQUESTS_FIELDS,
                output_type="ndjson",
                batch_prefix="[",
                batch_suffix="]",
                record_delimiter=",",
            ),
            "enabled": True,
        })
        step = StepResult("Logpush: HTTP Requests → Dynatrace", endpoint)
        job_id = self._check(step, resp)
        log_success("Logpush job created: HTTP Requests → Dynatrace", job_id)

    # ── Orchestrator ──────────────────────────────────────────────────────────

    def run(self):
        self._step1_create_zone()
        self._step2_create_dns_record()
        self._step3_set_min_tls()
        self._step4_disable_http2()
        self._step5_set_origin_timeout()
        self._step6_enable_log_retention()
        self._step7_deploy_waf()
        self._step8_disable_cache()

        log_warn(
            "Cloudflare limits zones to a maximum of 4 Logpush jobs.\n"
            "  Steps 9–12 create exactly 4 jobs. Do not exceed this limit."
        )

        self._step9_logpush_splunk_http()
        self._step10_logpush_splunk_firewall()
        self._step11_logpush_splunk_dns()
        self._step12_logpush_dynatrace_http()

        print(f"\n{LINE}")
        print("✓ ALL 12 STEPS COMPLETED SUCCESSFULLY")
        print(f"  Zone:    {self.zone_name}")
        print(f"  Zone ID: {self.zone_id}")
        print()
        print("  NEXT STEP (manual): Update your domain registrar's nameservers")
        print("  to point to Cloudflare. Find assigned nameservers in the")
        print("  Cloudflare dashboard under DNS → Nameservers.")
        print(LINE)

        self._write_report()
