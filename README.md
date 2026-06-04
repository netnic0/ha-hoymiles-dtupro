# Hoymiles DTU-Pro — Home Assistant integration

[![HACS Custom Repository][hacs-shield]][hacs-url]
[![GitHub Release][release-shield]][release-url]
[![License: MIT][license-shield]](LICENSE)
[![Conventional Commits][cc-shield]][cc-url]

> Modern Home Assistant custom integration for the **Hoymiles DTU-Pro** monitoring
> gateway. Speaks Modbus TCP. Built with `asyncio`, typed dataclasses, multi-language
> UI (EN / FR / ES / DE), and 96 % library test coverage.

---

## ⚠️ Experimental status — alpha

This is the **first alpha release**. The pure decoder library is fully unit-tested
against synthetic Modbus payloads, but the integration has **not yet been validated
end-to-end against real DTU-Pro hardware in async mode** at the time of release.

A wired-Modbus DTU-Pro running firmware **V00.07.04** is the reference target.
Earlier or later firmwares may need adjustments to the `apply_data_size_fix`
hook (currently implemented as a pure function but not yet wired into pymodbus).

Until milestone **v0.1.0** stable is published, please report any issue you hit
on the [issue tracker][issues-url] — your feedback is what will make this stable.

---

## What this integration does

- Polls a Hoymiles **DTU-Pro** gateway over **Modbus TCP** (port 502 by default).
- Exposes one **plant device** for the DTU and one **sub-device per inverter**
  (linked via `via_device` so the HA UI shows a clean tree).
- Per inverter: PV power, voltage, current, today / total production, grid
  voltage and frequency, temperature, alarm code, alarm count, RF link status.
- Diagnostics platform included (download a redacted JSON report from the
  device page for bug reports).
- Polling cadence is configurable; default is 30 s for live data.

### Compared to the existing ecosystem

| Project | Transport | Async | Status |
|---|---|---|---|
| **`netnic0/ha-hoymiles-dtupro`** *(this repo)* | Modbus TCP (DTU-Pro wired gateway) | Yes — `pymodbus.AsyncModbusTcpClient` | Alpha |
| [`ArekKubacki/Hoymiles-Plant-DTU-Pro`][arek-url] | Modbus TCP (DTU-Pro wired gateway) | No — sync | Stable, MIT |
| [`suaveolent/ha-hoymiles-wifi`][suav-url] | Protobuf TCP (HMS-WiFi inverters) | Yes | Stable, MIT |

Both are credited in [`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md).

---

## Hardware requirements

- **DTU-Pro** running firmware V00.07.04 or later (sticker on the device, or
  via the DTU's web UI → *About*).
- Wired Modbus TCP exposure on port 502 (the default for unmodified DTU-Pro
  firmwares; verify with `nc -vz <DTU_IP> 502` from a machine on the same LAN
  as the DTU).
- Up to **100 inverters** (sentinel-terminated scan; the integration caches
  the inverter count after the first scan to keep cycles short).
- Tested against an HMS-1000-2T plant (7 inverters / 14 panels). Other Hoymiles
  HM/MI-series inverters connected to a DTU-Pro should work; please report
  back so the compatibility list can be expanded.

---

## Installation

### Via HACS (custom repository — current path while in alpha)

1. In Home Assistant: **HACS → ⋮ → Custom repositories**.
2. Add `https://github.com/netnic0/ha-hoymiles-dtupro` with category
   **Integration**.
3. Find **Hoymiles DTU-Pro** in the HACS list and install.
4. Restart Home Assistant.
5. **Settings → Devices & services → Add integration → "Hoymiles DTU-Pro"**.
6. Enter the DTU host (IP or hostname) and Modbus port (default `502`).

### Manual install (without HACS)

1. Copy `custom_components/hoymiles_dtupro/` into your Home Assistant
   `<config>/custom_components/` directory.
2. Restart Home Assistant.
3. Add the integration via *Settings → Devices & services* as above.

---

## Configuration

All configuration is done through the Home Assistant UI (Config Flow).
No YAML required.

| Field | Default | Notes |
|---|---|---|
| Host / IP | — | The DTU's local IP, e.g. `192.0.2.1` |
| Port | `502` | Modbus TCP port |
| Unit ID | `1` | Modbus slave ID; rarely needs to change |
| Live data scan interval | `30 s` | Minimum 10 s to avoid stressing the DTU |

Reconfiguring (host changed, scan interval tuning) is done via the
*"Configure"* button on the integration card — entities are preserved.

---

## Entities created

For a DTU `<DTU_SN>` and inverters `<INV_SN_1>` … `<INV_SN_N>`:

| Entity | Domain | Notes |
|---|---|---|
| `sensor.<dtu>_pv_power` | sensor | Plant total live power (W) |
| `sensor.<dtu>_today_production` | sensor | Plant total today (Wh) |
| `sensor.<dtu>_total_production` | sensor | Plant lifetime (Wh, `state_class: total_increasing`) |
| `binary_sensor.<dtu>_alarm` | binary_sensor | Aggregated alarm flag |
| `sensor.<inv>_pv_power` | sensor | Per-inverter live PV power (W) |
| `sensor.<inv>_pv_voltage` | sensor | Per-inverter PV voltage (V) |
| `sensor.<inv>_pv_current` | sensor | Per-inverter PV current (A) |
| `sensor.<inv>_grid_voltage` | sensor | Per-inverter grid voltage (V) |
| `sensor.<inv>_grid_frequency` | sensor | Per-inverter grid frequency (Hz) |
| `sensor.<inv>_temperature` | sensor | Inverter case temperature (°C, signed) |
| `sensor.<inv>_today_production` | sensor | Inverter today (Wh) |
| `sensor.<inv>_total_production` | sensor | Inverter lifetime (Wh, `total_increasing`) |
| `sensor.<inv>_alarm_code` | sensor | Current alarm code (0 = no alarm) |
| `sensor.<inv>_alarm_count` | sensor | Cumulative alarm counter |
| `binary_sensor.<inv>_link` | binary_sensor | RF link to inverter healthy |

Entity IDs follow Home Assistant's `translation_key` slugification — see the
language files in `custom_components/hoymiles_dtupro/translations/` for the
display name in your locale.

---

## Lovelace examples

A minimal, dependency-free dashboard example is provided in
[`lovelace_examples/photovoltaique_minimal.yaml`](lovelace_examples/photovoltaique_minimal.yaml).
It uses only Home Assistant's built-in cards.

Richer examples (Mushroom, ApexCharts, animated SVG) will be added in upcoming
releases. Watch the repository or the [CHANGELOG](CHANGELOG.md).

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│  Home Assistant integration  (custom_components/hoymiles_dtupro/)   │
│  config flow, coordinators, entities, diagnostics, services, i18n   │
└──────────────────────┬──────────────────────────────────────────────┘
                       │ from .api import ...
┌──────────────────────▼──────────────────────────────────────────────┐
│  Pure async api  (custom_components/hoymiles_dtupro/api/)           │
│  HoymilesAsyncClient → pymodbus.AsyncModbusTcpClient                │
└──────────────────────┬──────────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────────────┐
│  Modbus TCP — DTU-Pro firmware                                      │
└─────────────────────────────────────────────────────────────────────┘
```

**Why a sub-package?** The `api/` sub-package has no Home Assistant dependency.
It can be tested with synthetic byte payloads, and would be straightforward to
extract to PyPI in a future release. The HA layer above it is a thin adapter —
it does config flow, entity wiring, and translation, but no protocol logic.

---

## Development

```bash
# Clone and set up
git clone https://github.com/netnic0/ha-hoymiles-dtupro.git
cd ha-hoymiles-dtupro
python -m venv .venv && source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -e ".[dev]"
pre-commit install

# Lint, type check, test
ruff check .
ruff format --check .
mypy custom_components/hoymiles_dtupro/api
pytest --cov=custom_components.hoymiles_dtupro.api
```

CI runs the same checks against Python 3.12 and 3.13 on every PR. See
[`CONTRIBUTING.md`](CONTRIBUTING.md) for the full contributor guide.

---

## Roadmap

- **v0.1.0-alpha.1** *(this release)* — Pure library + HA skeleton + i18n + CI.
- **v0.1.0** — Phase 1 hardware-validated, `apply_data_size_fix` wired into
  the async client, brand assets in `home-assistant/brands`.
- **v0.2.0** — `pytest-homeassistant-custom-component` test suite covering
  config flow, coordinators, entities. Lovelace Mushroom + ApexCharts examples.
- **v1.0.0** — Submission to the HACS *default* repository, broader hardware
  matrix, optional service for setting per-inverter limits.

See [`CHANGELOG.md`](CHANGELOG.md) for the actual release notes once releases
are cut.

---

## License

MIT — see [`LICENSE`](LICENSE) and
[`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md) for the upstream credits
that made this work possible.

[hacs-shield]: https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=flat
[hacs-url]: https://hacs.xyz
[release-shield]: https://img.shields.io/github/v/release/netnic0/ha-hoymiles-dtupro?include_prereleases&sort=semver&color=blue
[release-url]: https://github.com/netnic0/ha-hoymiles-dtupro/releases
[license-shield]: https://img.shields.io/badge/License-MIT-yellow.svg
[cc-shield]: https://img.shields.io/badge/Conventional_Commits-1.0.0-yellow.svg
[cc-url]: https://www.conventionalcommits.org/en/v1.0.0/
[issues-url]: https://github.com/netnic0/ha-hoymiles-dtupro/issues
[arek-url]: https://github.com/ArekKubacki/Hoymiles-Plant-DTU-Pro
[suav-url]: https://github.com/suaveolent/ha-hoymiles-wifi
