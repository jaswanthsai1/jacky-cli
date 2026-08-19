# When Blocked: Tools First, Pivot Second, Ask Third

A checklist for the moment a hunt hits a wall — CAPTCHA, rate limit, login
gate, WAF challenge, 403, MFA prompt. The default reaction should be "what
do I have available to get past this?", not "I can't" or an immediate
hand-off to the human.

Work through this in order before escalating:

1. **CAPTCHA / login gates.** Consider: a stealth/anti-detection browser
   profile (disabling automation-detection flags), an alternate protocol
   that doesn't route through the challenged web flow (e.g. IMAP/SMTP for
   an account that also exposes a web login), or simply a different,
   slower, more human-like interaction pattern. Many challenges are tuned
   to catch obviously-automated traffic, not a careful one-off request.

2. **Rate limits / 403s.** Try verb tricks (HEAD vs GET vs POST), header
   tricks (`X-Forwarded-For`, `X-Original-URL`), path normalization, and a
   different IP/User-Agent profile. Confirm whether the block is IP-based,
   session-based, or fingerprint-based before picking a bypass.

3. **Session-bound anti-bot protections.** Some sites bind auth tokens to
   the specific TCP/TLS/browser fingerprint that established the session —
   a perfectly valid token replayed from a different client (e.g. a proxy
   tool instead of the browser) will fail even though the token itself is
   fine. If authenticated requests fail with a generic "session invalid"
   error despite a fresh, valid token, replay the request from the *same*
   browser context that created the session instead of a separate HTTP
   client.

4. **MFA prompts.** Check whether there's a session/API endpoint that
   doesn't re-trigger the MFA challenge, whether a session token can be
   reused directly, or whether the MFA gate only protects one entry point
   while others are reachable with the same underlying session.

5. **Missing permissions.** Check for alternate API versions, admin
   subdomains, cross-tenant access with the same credentials, and internal
   endpoints surfaced in JS bundles that might not enforce the same checks
   as the primary UI flow.

6. **Binary/asset download failures.** Check official help pages for
   correct download URLs, app-store listings, GitHub releases, and package
   registries (npm/PyPI/etc.) as alternate distribution channels.

If all of the relevant checks above genuinely fail after real effort, then
— and only then — escalate to a human or move on to a different lead. The
point isn't infinite persistence on a single dead end; it's exhausting the
tools you actually have before concluding something is impossible.

## General persistence discipline

A task is not "done" until it's proven done, one way or the other:

- Try alternate encodings, ports, HTTP verbs, and roles before giving up
  on a lead.
- Re-enumerate — a first pass often misses something a second pass catches.
- If one attack class stalls, switch to a different class on the same
  target and come back later with fresh context, rather than staring at
  the same wall.
- Complexity is not a reason to stop; it's the job. But persistence must
  stay inside the authorized scope — never let "don't give up" turn into
  testing something you weren't authorized to test.
