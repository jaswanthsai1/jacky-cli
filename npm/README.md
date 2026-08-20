# jacky-cli-agent

npm install shim for **[Jacky CLI](https://github.com/jaswanthsai1/jacky-cli)** — a self-improving AI agent CLI with a built-in bug-bounty/offensive-security hunt-loop methodology. Local model or cloud, your choice of provider.

This package does not contain Jacky itself. It's a small Node.js bootstrap script that:

1. Downloads and installs the real `jacky-cli` Python package into a managed virtual environment under `~/.jacky`
2. Exposes the `jacky` command on your `PATH`
3. Keeps that managed install up to date on subsequent `npm install -g` runs

## Install

```bash
npm install -g jacky-cli-agent
```

Then run:

```bash
jacky
```

## Requirements

- Node.js >= 16 (to run this shim)
- Python 3.11–3.13 (installed automatically by the shim if missing on supported platforms)

## Full documentation

See the [main repository](https://github.com/jaswanthsai1/jacky-cli) and [docs site](https://jaswanthsai1.github.io/jacky-cli/) for setup, configuration, and usage.

## License

MIT — see [LICENSE](https://github.com/jaswanthsai1/jacky-cli/blob/main/LICENSE).
