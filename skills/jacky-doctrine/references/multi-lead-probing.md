# Multi-Lead Parallel Probing Technique

A technique for testing several attack leads at once, inferring endpoint
existence from response-code and header differences, and exploiting
anomalies in backend behavior instead of walking past them.

## Core principle

**Don't pick one lead and exhaust it before trying the others.** Batch
requests — multiple attack vectors, multiple endpoints, multiple HTTP
methods — and compare response codes, bodies, and headers to infer what
exists, what's protected, and what's deprecated.

## Response-code inference

When you can't directly access an endpoint, the response code + body
pattern usually tells you whether it exists:

| Status | Pattern | Meaning |
|--------|---------|---------|
| 403 with a structured error body / gateway-specific error header | Endpoint EXISTS, requires valid auth. A 403 from an API gateway is not the same signal as a 404. |
| 403 with a CAPTCHA/challenge page | Endpoint EXISTS, bot-protected. Real service. |
| 404 with a generic "route not found" JSON body | Route does not exist at the gateway level. |
| 404 via redirect to a generic error handler | Path recognized by the web server but routed to a 404 handler — worth double-checking with alternate casing/encoding. |
| 410 Gone | Endpoint existed previously, now removed. Don't keep retesting it. |
| 200 with a generic catch-all body | No specific route matched — default/catch-all handler, not a real endpoint. |
| 200 with a distinct body shape and unique headers | Real endpoint with its own handler — compare headers against other endpoints for upstream differences. |

## Header fingerprinting for backend architecture

Response headers often reveal more than the body:

- **Rate-limit headers that differ between endpoints** → they're hitting
  different upstreams. Probe further on the less-restrictive one.
- **Upstream-status headers that disagree with the outer response code**
  (e.g. a gateway header reporting `upstream-status: 500` while the outer
  response is `200`) → the upstream is failing but the gateway is masking
  it. Worth probing for debug/internal paths on that upstream.
- **Custom headers naming an internal proxy or service** → tells you which
  component is gatekeeping, which helps you target bypasses correctly.
- **CORS `access-control-allow-headers` listing unusual custom headers** →
  those headers are accepted by the endpoint; try sending them.
- **CORS `access-control-expose-headers` naming an unusual header** → try
  injecting that header and see if it changes behavior.

## "Think differently" — exploit anomalies, don't shrug at them

When something is unusual, don't accept it as noise — ask why:

1. Why does this endpoint have a different response format from its
   siblings? → Probably a different upstream.
2. Why does it have a different rate limit? → Probably different upstream
   configuration — potentially less hardened.
3. Why does an internal status header disagree with the outer HTTP code?
   → The gateway is normalizing/masking an upstream failure.
4. Can you reach other paths on the same (weaker) upstream via path
   normalization tricks (`//path`, `/./path`, trailing encoded characters)?
5. What CORS/auth headers does the anomalous endpoint accept that its
   siblings don't?

## Checklist for each lead

Run this minimum set before moving on to the next lead:

- [ ] GET — does the endpoint exist? (200 vs 403 vs 404 vs 410)
- [ ] POST — does it accept data? Does a different body change the response?
- [ ] OPTIONS — what methods/CORS headers are allowed?
- [ ] PUT/PATCH/DELETE — idempotency check
- [ ] 403-bypass headers — `X-Forwarded-For`, `X-Real-IP`, `X-Original-URL`
- [ ] Header fingerprint — rate limits, upstream-status headers, custom headers
- [ ] Path normalization — `//path`, `/./path`, `/path%20`
- [ ] Internal-IP spoofing — `10.x`, `172.16-31.x`, `192.168.x`, `127.x`
- [ ] Content-type switching — JSON vs form vs XML vs plain text
- [ ] Auth-method switching — cookie vs Bearer vs custom header vs query param
