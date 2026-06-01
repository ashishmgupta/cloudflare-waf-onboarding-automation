"""
Field lists for each Logpush job dataset.

Edit the lists below to control which fields are forwarded to each destination.
Full field reference: https://developers.cloudflare.com/logs/reference/log-fields/
"""

# ── Splunk: HTTP Requests ─────────────────────────────────────────────────────

SPLUNK_HTTP_REQUESTS_FIELDS = [
    "BotScore", "BotScoreSrc", "CacheCacheStatus", "CacheResponseBytes",
    "CacheResponseStatus", "ClientASN", "ClientCountry", "ClientDeviceType",
    "ClientIP", "ClientIPClass", "ClientRequestBytes", "ClientRequestHost",
    "ClientRequestMethod", "ClientRequestPath", "ClientRequestProtocol",
    "ClientRequestReferer", "ClientRequestURI", "ClientRequestUserAgent",
    "ClientSSLCipher", "ClientSSLProtocol", "ClientSrcPort",
    "EdgeColoCode", "EdgeColoID", "EdgeEndTimestamp", "EdgePathingOp",
    "EdgePathingSrc", "EdgePathingStatus", "EdgeRateLimitAction",
    "EdgeRateLimitID", "EdgeRequestHost", "EdgeResponseBytes",
    "EdgeResponseStatus", "EdgeServerIP", "EdgeStartTimestamp",
    "FirewallMatchesActions", "FirewallMatchesRuleIDs", "FirewallMatchesSources",
    "OriginIP", "OriginResponseBytes", "OriginResponseStatus",
    "OriginResponseTime", "OriginSSLProtocol", "RayID",
    "SecurityLevel", "WAFAction", "WAFProfile", "WAFRuleID",
    "WAFRuleMessage", "ZoneName",
]

# ── Splunk: Firewall Events ───────────────────────────────────────────────────

SPLUNK_FIREWALL_EVENTS_FIELDS = [
    "Action", "ClientASN", "ClientASNDescription", "ClientCountry",
    "ClientIP", "ClientIPClass", "ClientRefererHost", "ClientRefererPath",
    "ClientRefererQuery", "ClientRefererScheme", "ClientRequestHost",
    "ClientRequestMethod", "ClientRequestPath", "ClientRequestProtocol",
    "ClientRequestQuery", "ClientRequestScheme", "ClientRequestUserAgent",
    "Datetime", "Description", "EdgeColoCode", "EdgeResponseStatus",
    "FraudUserID", "Kind", "MatchIndex", "Metadata", "OriginResponseStatus",
    "OriginatorRayID", "RayID", "RuleID", "Source", "ZoneName",
]

# ── Splunk: DNS Logs ──────────────────────────────────────────────────────────

SPLUNK_DNS_LOGS_FIELDS = [
    "ColoCode", "EDNSSubnet", "EDNSSubnetLength", "QueryName",
    "QueryType", "RDATAFields", "RRType", "ResponseCached",
    "ResponseCode", "SourceIP", "Timestamp",
]

# ── Dynatrace: HTTP Requests ──────────────────────────────────────────────────

DYNATRACE_HTTP_REQUESTS_FIELDS = [
    "RayID", "ZoneName", "CacheCacheStatus",
    "ClientIP", "ClientRequestHost", "ClientRequestMethod",
    "ClientRequestURI", "ClientRequestUserAgent", "Cookies",
    "EdgeRequestHost", "EdgeEndTimestamp", "EdgeStartTimestamp",
    "EdgeTimeToFirstByteMs", "EdgeColoCode", "EdgeResponseBytes",
    "EdgeResponseStatus",
    "OriginRequestHeaderSendDurationMs", "OriginResponseDurationMs",
    "OriginResponseHeaderReceiveDurationMs",
    "OriginIP", "OriginResponseBytes", "OriginResponseStatus",
]
