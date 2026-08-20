# SSTI (Server-Side Template Injection)

Generic reference notes for this vulnerability class. This is a starting
checklist for a human hunter using Jacky, not an auto-exploit script —
always confirm findings manually before reporting, and stay within
authorized scope.

## How to detect

Any input rendered through a templating engine (Jinja2, Twig, Freemarker, Velocity, Handlebars) is a candidate. Probe with polyglot payloads like `${{<%[%'"}}%\` and observe which characters get evaluated vs. escaped to fingerprint the engine.

## How to escalate

Once the engine is fingerprinted, move from expression evaluation to RCE using engine-specific gadget chains (e.g. Jinja2 `{{ self.__init__.__globals__.__builtins__.__import__('os').popen('id').read() }}`).

## Common tools

tplmap for automated detection/exploitation, manual polyglot fuzzing, PortSwigger's SSTI cheat sheet for engine fingerprinting.

## Validate before reporting

Run every candidate finding through the validation gate in
[`skills/triage-validation/SKILL.md`](../triage-validation/SKILL.md)
before treating it as a confirmed finding.
