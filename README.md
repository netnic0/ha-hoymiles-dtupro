# Hoymiles DTU-Pro — Home Assistant integration

[![HACS Custom Repository][hacs-shield]][hacs-url]
[![GitHub Release][release-shield]][release-url]
[![License: MIT][license-shield]](LICENSE)
[![Conventional Commits][cc-shield]][cc-url]

> Modern Home Assistant custom integration for the **Hoymiles DTU-Pro** monitoring
> gateway. Speaks Modbus TCP. Built with `asyncio`, typed dataclasses, multi-language
> UI (EN / FR / ES / DE), and 96 % library test coverage.

---

## Hardware validated ✅

Tested end-to-end against a real **DTU-Pro** with 7 **HMS-1000-2T** micro-inverters
(14 panels — 6 Est, 8 Ouest) running firmware **V00.07.04**.

Results: **8 devices · 116 entities** (1 plant device + 7 inverter sub-devices,
each with 16 entities covering per-MPPT-port PV power, energy, voltage, current,
temperature, grid data, alarm, and RF link status).

---

## What this integration does

- Polls a Hoymiles **DTU-Pro** gateway over **Modbus TCP** (port 502 by default).
- Exposes one **plant device** for the DTU and one **sub-device per inverter**
  (linked via `via_device` so the HA UI shows a clean tree).
- HMS-1000-2T dual-MPPT support: each inverter exposes **two independent PV port
  entities** so you can monitor individual panels.
- Per inverter port: PV power, voltage, current, today / total production.
- Per inverter: grid voltage, grid frequency, temperature, alarm code, alarm count,
  RF link status.
- Diagnostics platform included (download a redacted JSON report from the
  device page for bug reports).
- Polling cadence is configurable; default is 30 s for live data.
- Built-in firmware data-size workaround (`apply_data_size_fix`) for known
  Hoymiles DTU firmware quirks.

### Compared to the existing ecosystem

| Project | Transport | Async | Status |
|---|---|---|---|
| **`netnic0/ha-hoymiles-dtupro`** *(this repo)* | Modbus TCP (DTU-Pro wired gateway) | Yes — `pymodbus.AsyncModbusTcpClient` | **Stable v1.0.0** — hardware validated |
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

### Via HACS (custom repository)

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

Entity IDs are generated from the `translation_key` slugified in your HA locale.
The table below uses the **English** translation key names (locale `en`).

### Plant device (1 per DTU)

| Entity | Domain | Description |
|---|---|---|
| `sensor.<dtu>_pv_power` | sensor | Plant total live power (W) |
| `sensor.<dtu>_today_production` | sensor | Plant total today (Wh, displayed as kWh, `state_class: total_increasing`) |
| `sensor.<dtu>_total_production` | sensor | Plant lifetime (Wh, displayed as kWh, `state_class: total`) |
| `binary_sensor.<dtu>_alarm` | binary_sensor | Aggregated alarm flag |

### Per-inverter device (×N, one per detected inverter)

| Entity | Domain | Description |
|---|---|---|
| `sensor.<inv>_pv_power_1` | sensor | Port 1 PV power (W) |
| `sensor.<inv>_pv_power_2` | sensor | Port 2 PV power (W) — HMS-1000-2T dual MPPT |
| `sensor.<inv>_pv_voltage_1` / `_2` | sensor | Port PV voltage (V) |
| `sensor.<inv>_pv_current_1` / `_2` | sensor | Port PV current (A) |
| `sensor.<inv>_today_production_1` / `_2` | sensor | Port today production (Wh) |
| `sensor.<inv>_total_production_1` / `_2` | sensor | Port lifetime production (Wh) |
| `sensor.<inv>_temperature` | sensor | Inverter case temperature (°C, signed) |
| `sensor.<inv>_grid_voltage` | sensor | Grid voltage (V) |
| `sensor.<inv>_grid_frequency` | sensor | Grid frequency (Hz) |
| `sensor.<inv>_alarm_code` | sensor | Current alarm code (0 = no alarm) |
| `sensor.<inv>_alarm_count` | sensor | Cumulative alarm counter |
| `binary_sensor.<inv>_link` | binary_sensor | RF link to inverter healthy |

> **Note:** If your HA is configured in French, the entity slugs will use the
> French translation keys (e.g. `puissance_instantanee`, `energie_du_jour`, `liaison`).
> The translation key names are defined in `translations/en.json`.

---

## Lovelace examples

Ready-to-use dashboard examples are provided in [`lovelace_examples/`](lovelace_examples/):

| File | Dependencies | Description |
|---|---|---|
| [`mushroom.yaml`](lovelace_examples/mushroom.yaml) | mushroom, apexcharts-card | Compact card — chips, KPIs, 24h chart, inverter status |
| [`full.yaml`](lovelace_examples/full.yaml) | mushroom, apexcharts-card, button-card, card-mod, vertical-stack-in-card | Full dashboard view — animated power circle, per-panel power display, energy balance, autoconsommation gauge |

Copy the YAML into the HA Lovelace raw editor and replace the `PLACEHOLDER_{1..7}`
serial tokens with your actual inverter serial numbers (found in
*Settings → Devices & Services → Hoymiles DTU-Pro*).

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

CI runs the same checks against Python 3.13 on every PR. See
[`CONTRIBUTING.md`](CONTRIBUTING.md) for the full contributor guide.

---

## Roadmap

- **v0.3.1-alpha.1** *(current)* — Full sensor wiring (116 entities), hardware
  validated, `apply_data_size_fix` wired, brand assets, Lovelace examples.
- **v1.0.0** — Stable release, broader hardware matrix, optional service for
  setting per-inverter power limits.

See [`CHANGELOG.md`](CHANGELOG.md) for the actual release notes.

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
