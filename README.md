# lambda-cloud-cli

[![CI](https://github.com/mrprokl/lambda-cloud-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/mrprokl/lambda-cloud-cli/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](pyproject.toml)

Unofficial community command-line interface for the
[Lambda Cloud](https://cloud.lambda.ai) API.

> **Disclaimer**: this project is **not** affiliated with, endorsed by, or
> supported by Lambda, Inc. It is built against the
> [public Lambda Cloud API](https://docs.lambda.ai/public-cloud/).

## Installation

Requires Python 3.10+.

```bash
# Option 1 — uv (recommended)
uv tool install lambda-cloud-cli

# Option 2 — pipx
pipx install lambda-cloud-cli

# Option 3 — plain pip
pip install lambda-cloud-cli

# Option 4 — straight from GitHub (bleeding edge)
uv tool install git+https://github.com/mrprokl/lambda-cloud-cli
```

From source, for development:

```bash
git clone https://github.com/mrprokl/lambda-cloud-cli.git
cd lambda-cloud-cli
uv venv
uv pip install -e '.[dev]'
```

## Quickstart

```bash
# 1. Authenticate (get your key at https://cloud.lambda.ai/api-keys)
lambda-cloud login

# 2. See what's available
lambda-cloud regions list
lambda-cloud types list
lambda-cloud images list

# 3. Launch a GPU instance
lambda-cloud instances launch \
    --type gpu_1x_a10 \
    --region us-west-1 \
    --ssh-key my-key

# 4. Watch it boot
lambda-cloud instances list
lambda-cloud instances get <instance-id>

# 5. Clean up
lambda-cloud instances terminate <instance-id>
```

Output is human-friendly tables by default; add `--output json` (or `-o json`)
to any command for scripting:

```bash
lambda-cloud -o json instances list | jq '.[].ip'
```

## Authentication

The API key is resolved in this order:

1. `--api-key` flag
2. `LAMBDA_API_KEY` environment variable
3. Config file written by `lambda-cloud login`
   (`$XDG_CONFIG_HOME/lambda-cloud/config.json`, default
   `~/.config/lambda-cloud/config.json`, mode `0600`)

```bash
lambda-cloud login               # interactive prompt, key is validated
lambda-cloud login --api-key X   # non-interactive
lambda-cloud whoami              # which key is in use? is it valid?
lambda-cloud logout              # remove stored key
lambda-cloud config show         # inspect configuration & defaults
```

## Commands

| Command | Description |
| --- | --- |
| `instances list` | List running instances |
| `instances get <id>` | Instance details |
| `instances launch` | Launch an on-demand instance |
| `instances restart <id>...` | Restart instances |
| `instances terminate <id>...` | Terminate instances (destructive!) |
| `instances rename <id> --name X` | Rename an instance |
| `types list` | Instance types, specs, prices, regional capacity |
| `ssh-keys list` / `add` / `delete` | Manage SSH keys (can generate a pair) |
| `filesystems list` / `create` / `delete` | Manage shared filesystems |
| `images list [--region R] [--family F]` | List machine images |
| `regions list` | List regions |
| `firewall rulesets ...` | CRUD on regional firewall rulesets |
| `firewall global get` / `update` | Global firewall ruleset |
| `audit list [--all]` | Account audit events (paginated) |
| `config show` | Show CLI configuration |
| `login` / `logout` / `whoami` | Credential management |

### Launching instances

```bash
lambda-cloud instances launch \
    --type gpu_8x_h100_sxm5 \
    --region us-south-1 \
    --ssh-key my-key \
    --name training-run \
    --filesystem shared-data \
    --tag env=prod --tag team=ml \
    --image-family lambda-stack \
    --user-data ./cloud-init.yaml
```

### Firewall rules files

`firewall rulesets create --rules-file rules.json` expects a JSON list:

```json
[
  {"protocol": "tcp", "port_range": [22, 22], "source_network": "0.0.0.0/0", "description": "SSH"},
  {"protocol": "tcp", "port_range": [8888, 8888], "source_network": "203.0.113.0/24", "description": "Jupyter"},
  {"protocol": "icmp", "source_network": "0.0.0.0/0", "description": "Ping"}
]
```

Rules are validated locally before submission: `icmp` must not define
`port_range`, every other protocol must.

## Environment variables

| Variable | Purpose |
| --- | --- |
| `LAMBDA_API_KEY` | API key (overrides stored config) |
| `LAMBDA_CLOUD_CONFIG_DIR` | Override the config directory |
| `LAMBDA_CLOUD_API_URL` | Override the API base URL (useful for testing) |
| `LAMBDA_CLOUD_MIN_INTERVAL` | Min seconds between API calls (default `1.05`, per documented rate limit) |

## Rate limits

Per the API documentation: 1 request/second in general, and 1 request per
12 seconds on `instance-operations/launch`. The client throttles requests
client-side and retries `429` responses honouring `Retry-After`.

## Development

```bash
uv venv
uv pip install -e '.[dev]'
uv run ruff check src tests
uv run pytest
```

Layout follows a strict layered architecture:

```
src/lambda_cloud/
├── cli/        # interface: commands, state, ui (console/tables/formatters)
├── api/        # http client + service layer (request shaping, validation)
├── core/       # foundations: config, errors
└── mngr/       # pydantic resource models
```

Dependencies flow strictly downward: `cli → api → core/mngr`.

## Contributing

Issues and pull requests are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT — see [LICENSE](LICENSE).
