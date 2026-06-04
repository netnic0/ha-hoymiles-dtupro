# Contributing to ha-hoymiles-dtupro

Thanks for your interest! This is a small solo-maintained project, so the
ground rules are deliberately light.

## Bug reports & feature requests

Open an [issue](https://github.com/netnic0/ha-hoymiles-dtupro/issues/new/choose)
using the matching template. For bugs, please include:

- Your DTU-Pro firmware version (`Settings → About` in the DTU web UI).
- The exact error message or unexpected behaviour.
- Whether `ArekKubacki/Hoymiles-Plant-DTU-Pro` works on the same hardware.

## Pull requests

1. Fork the repo and create a feature branch from `main`:
   `git checkout -b feat/short-description`.
2. Install dev dependencies: `pip install -e ".[dev]"`.
3. Set up the pre-commit hooks: `pre-commit install`.
4. Write code + tests. Aim for ≥ 80 % coverage on the pure api package
   (`custom_components/hoymiles_dtupro/api/`).
5. Run the full check suite locally:
   ```bash
   ruff check .
   ruff format --check .
   mypy custom_components/hoymiles_dtupro/api
   pytest --cov=custom_components.hoymiles_dtupro.api
   ```
6. Use [Conventional Commits](https://www.conventionalcommits.org/) for commit
   messages — release-please uses them to compute the next version and
   generate the changelog. Examples:
   - `feat(api): support DTU-type 2 (OpenDTU)`
   - `fix(decoder): handle short payloads from firmware V00.08.x`
   - `docs: clarify HACS install instructions`
7. Push and open a PR against `main`.

## Code style

- All artifacts (code, comments, docstrings, Markdown, commit messages) must
  be in **English**, except internationalisation files (`translations/*.json`)
  and YAML examples whose content is end-user facing.
- Match the surrounding code's idiom — frozen dataclasses, type-hinted
  signatures, lazy imports inside HA-only modules, `pragma: no cover` for HA
  imports that the offline test suite cannot exercise.
- Lint with `ruff` (config in `pyproject.toml`); type-check with `mypy --strict`
  on `custom_components/hoymiles_dtupro/api/` only — the HA layer is exercised
  by HA-native tests in milestone M2.

## License & attribution

By contributing, you agree that your contributions will be licensed under the
MIT License (see [`LICENSE`](LICENSE)). If your contribution incorporates code
or design from another project, please add the attribution to
[`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md).
