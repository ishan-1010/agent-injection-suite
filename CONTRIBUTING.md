# Contributing

Thanks for your interest. This is a small, focused tool; contributions that keep
it small and honest are very welcome — especially **new scenarios**.

## Development setup

```bash
git clone https://github.com/ishan-1010/agent-injection-suite
cd agent-injection-suite
pip install -e ".[dev]"
pytest -q          # all tests run offline; no model or network required
```

## Adding a scenario (the easiest, highest-value contribution)

Scenarios are plain YAML under [`scenarios/`](scenarios/) — no Python required.
Each is one injection test case with a `detection` rule describing what
*compliance* looks like. Copy an existing entry in the relevant category file,
keep payloads minimal and standard (no novel weaponization — see below), and run
`pytest -q` to confirm it loads and validates.

## Adding an agent adapter

To test your own agent, implement one method. See
[`docs/adding-an-adapter.md`](docs/adding-an-adapter.md).

## Ground rules

- **Defensive only.** Scenarios use standard, documented injection patterns to
  *measure resistance*. We do not accept novel, weaponized exploits.
- **No real secrets.** Never commit real keys or tokens.
- **Keep detection inspectable.** Detection stays rule-based and readable; the
  rules are the product.
- **Tests pass offline.** `pytest -q` must stay green without a network or model.

## Pull requests

Keep PRs focused, describe what changed and why, and make sure CI is green.
