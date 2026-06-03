# Security Policy

## Scope

`agent-injection-suite` is a **defensive** evaluation tool. It runs standard,
documented prompt-injection patterns against an agent **you own or are
authorized to test**, and reports whether the agent resisted or complied. It
ships no real secrets (the planted token is an obvious fake) and its mock tools
have no real side effects (`run_command` never executes, `send_message` never
sends).

## Reporting a vulnerability

If you find a security issue in this tool itself (for example, a way the harness
could be made to perform a real side effect, or a scenario that leaks something
sensitive), please report it privately rather than opening a public issue:

- Use GitHub's **"Report a vulnerability"** (Security → Advisories) on this repo, or
- email the maintainer listed on the GitHub profile.

Please include steps to reproduce and the affected version. I aim to acknowledge
reports within **7 days**.

## Out of scope

- Findings produced *about a target agent* you tested — those are the tool's
  normal output, not a vulnerability in the tool.
- Using this tool against systems you do not own or have permission to test.
  That is misuse and is not supported.
