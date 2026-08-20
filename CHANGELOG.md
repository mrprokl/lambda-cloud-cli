# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-08-20

Initial release of the community Lambda Cloud CLI.

### Added

- Authentication flow: `login`, `logout`, `whoami`, `config show`
  (API key from flag > `LAMBDA_API_KEY` > config file with 0600 permissions).
- `instances`: list, get, launch (tags, filesystems, image, user-data,
  firewall rulesets), restart, terminate (with confirmation), rename.
- `types list`: instance types with specs, hourly price and live capacity.
- `ssh-keys`: list, add (upload existing key or generate a pair — private key
  written with 0600 permissions), delete.
- `filesystems`: list, create, delete.
- `images list` with `--region` / `--family` filters.
- `regions list`.
- `firewall rulesets` (list/get/create/update/delete) and
  `firewall global` (get/update) with local rule validation.
- `audit list` with pagination support (`--all`).
- Global options: `--output table|json`, `--api-key`, `--verbose`,
  `--version`, `--show-completion`.
- HTTP client honouring the documented API rate limits (1 req/s), retrying
  `429` responses with `Retry-After`, and surfacing the API's structured
  error codes.
- Test suite (pytest + respx) and CI (ruff, pytest on Python 3.10–3.13,
  package build).

[Unreleased]: https://github.com/mrprokl/lambda-cloud-cli/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/mrprokl/lambda-cloud-cli/releases/tag/v0.1.0
