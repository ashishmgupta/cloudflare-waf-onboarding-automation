"""HTML report generation for zone onboarding runs."""

import html
import json
from datetime import datetime, timezone
from pathlib import Path


class StepResult:
    def __init__(self, name: str, endpoint: str):
        self.name = name
        self.endpoint = endpoint
        self.status = "SKIPPED"
        self.resource_id = ""
        self.response: dict = {}
        self.errors: list = []


class Reporter:
    def __init__(self, zone_name: str, record_type: str, origin: str):
        self.zone_name = zone_name
        self.record_type = record_type
        self.origin = origin
        self.steps: list[StepResult] = []
        self.overall_status = "SUCCESS"
        self.rollback_triggered = False
        self.rollback_status = ""
        self.rollback_response: dict = {}

    def add_step(self, step: StepResult):
        self.steps.append(step)

    def write(self, zone_id: str, output_path: Path):
        output_path.write_text(self._render(zone_id), encoding="utf-8")

    def _render(self, zone_id: str) -> str:
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        status_color = "#3fb950" if self.overall_status == "SUCCESS" else "#ff4444"
        status_bg = "#0f2417" if self.overall_status == "SUCCESS" else "#2d0f0f"

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Cloudflare Zone Report — {html.escape(self.zone_name)}</title>
{self._styles(status_color, status_bg)}
</head>
<body>
<div class="header">
  <h1>Cloudflare Zone Report</h1>
  <div class="status-badge">{self.overall_status}</div>
  <div class="meta">
    <strong>Zone:</strong> {html.escape(self.zone_name)} &nbsp;|&nbsp;
    <strong>Zone ID:</strong> {html.escape(zone_id) if zone_id else 'N/A'} &nbsp;|&nbsp;
    <strong>Record Type:</strong> {html.escape(self.record_type)} &nbsp;|&nbsp;
    <strong>Origin:</strong> {html.escape(self.origin)}<br>
    <strong>Generated:</strong> {timestamp}
  </div>
</div>

<h2>Step Summary</h2>
<table>
  <thead>
    <tr><th>#</th><th>Step</th><th>Status</th><th>Endpoint</th><th>Resource ID</th></tr>
  </thead>
  <tbody>{self._summary_rows()}</tbody>
</table>

<h2>Step Details</h2>
{self._detail_sections()}
{self._error_section()}
{self._rollback_section()}
</body>
</html>"""

    def _summary_rows(self) -> str:
        rows = ""
        for i, step in enumerate(self.steps):
            if step.status == "SUCCESS":
                badge = '<span class="badge-success">✓ SUCCESS</span>'
            elif step.status == "FAILED":
                badge = '<span class="badge-failed">✗ FAILED</span>'
            else:
                badge = '<span class="badge-skipped">— SKIPPED</span>'
            rid = html.escape(step.resource_id) if step.resource_id else "—"
            rows += f"""
    <tr>
      <td>{i + 1}</td>
      <td>{html.escape(step.name)}</td>
      <td>{badge}</td>
      <td class="endpoint">{html.escape(step.endpoint)}</td>
      <td class="resource-id">{rid}</td>
    </tr>"""
        return rows

    def _detail_sections(self) -> str:
        sections = ""
        for i, step in enumerate(self.steps):
            pretty = json.dumps(step.response, indent=2) if step.response else "{}"
            sections += f"""
<details>
  <summary>Step {i + 1}: {html.escape(step.name)} — {step.status}</summary>
  <pre>{html.escape(pretty)}</pre>
</details>"""
        return sections

    def _error_section(self) -> str:
        if self.overall_status != "FAILED":
            return ""
        failed = next((s for s in self.steps if s.status == "FAILED"), None)
        name = html.escape(failed.name if failed else "unknown")
        errors = html.escape(json.dumps(failed.errors if failed else [], indent=2))
        return f"""
<div class="error-section">
  <h2>✗ Error Details</h2>
  <p>The automation failed at step: <strong>{name}</strong></p>
  <details open>
    <summary>API Error Response</summary>
    <pre>{errors}</pre>
  </details>
</div>"""

    def _rollback_section(self) -> str:
        if not self.rollback_triggered:
            return ""
        rb_color = "#3fb950" if self.rollback_status == "SUCCESS" else "#ff4444"
        rb_json = html.escape(json.dumps(self.rollback_response, indent=2))
        return f"""
<div class="rollback-section">
  <h2>↩ Rollback</h2>
  <p>Status: <strong style="color:{rb_color}">{self.rollback_status}</strong></p>
  <details>
    <summary>Rollback API Response</summary>
    <pre>{rb_json}</pre>
  </details>
</div>"""

    @staticmethod
    def _styles(status_color: str, status_bg: str) -> str:
        return f"""<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: #0d1117; color: #c9d1d9; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; padding: 24px; }}
  h1 {{ font-size: 1.8rem; color: #58a6ff; margin-bottom: 8px; }}
  h2 {{ font-size: 1.1rem; color: #8b949e; margin: 24px 0 12px; border-bottom: 1px solid #30363d; padding-bottom: 8px; }}
  .header {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 20px; margin-bottom: 24px; }}
  .status-badge {{ display: inline-block; padding: 6px 18px; border-radius: 20px; font-weight: bold;
                   background: {status_bg}; color: {status_color}; border: 1px solid {status_color}; margin-top: 10px; }}
  .meta {{ color: #8b949e; font-size: 0.88rem; margin-top: 10px; line-height: 1.7; }}
  table {{ width: 100%; border-collapse: collapse; margin-bottom: 24px; font-size: 0.88rem; }}
  th {{ background: #161b22; color: #8b949e; text-align: left; padding: 10px 12px;
        border: 1px solid #30363d; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.04em; }}
  td {{ padding: 10px 12px; border: 1px solid #30363d; vertical-align: top; }}
  tr:nth-child(odd) td {{ background: #161b22; }}
  tr:nth-child(even) td {{ background: #0d1117; }}
  .badge-success {{ color: #3fb950; font-weight: bold; }}
  .badge-failed {{ color: #ff4444; font-weight: bold; }}
  .badge-skipped {{ color: #8b949e; }}
  .endpoint {{ font-family: 'Courier New', monospace; font-size: 0.78rem; color: #79c0ff; }}
  .resource-id {{ font-family: 'Courier New', monospace; font-size: 0.78rem; color: #a5d6ff; }}
  details {{ background: #161b22; border: 1px solid #30363d; border-radius: 6px; margin-bottom: 10px; }}
  summary {{ padding: 10px 14px; cursor: pointer; color: #8b949e; font-size: 0.88rem; user-select: none; }}
  summary:hover {{ color: #c9d1d9; }}
  pre {{ background: #0d1117; color: #a5d6ff; padding: 14px; border-radius: 0 0 6px 6px;
         font-family: 'Courier New', monospace; font-size: 0.78rem; overflow-x: auto;
         white-space: pre-wrap; word-wrap: break-word; max-height: 500px; overflow-y: auto; }}
  .error-section {{ background: #2d0f0f; border: 1px solid #ff4444; border-radius: 8px; padding: 16px; margin-bottom: 24px; }}
  .error-section h2 {{ color: #ff4444; border-color: #ff4444; }}
  .rollback-section {{ background: #0f1d2d; border: 1px solid #58a6ff; border-radius: 8px; padding: 16px; margin-bottom: 24px; }}
  .rollback-section h2 {{ color: #58a6ff; border-color: #58a6ff; }}
</style>"""
