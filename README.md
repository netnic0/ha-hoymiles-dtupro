# Hoymiles DTU-Pro — Home Assistant integration

[![HACS Custom Repository][hacs-shield]][hacs-url]
[![GitHub Release][release-shield]][release-url]
[![License: MIT][license-shield]](LICENSE)
[![Conventional Commits][cc-shield]][cc-url]

> Modern Home Assistant custom integration for the **Hoymiles DTU-Pro** monitoring
> gateway. Speaks Modbus TCP. Built with `asyncio`, typed dataclasses, multi-language
> UI (EN / FR / ES / DE), Silver-tier quality (>=80% api / >=95% HA-layer test coverage).

---

## Hardware validated ✅

Tested end-to-end against a real **DTU-Pro** with 7 **HMS-1000-2T** micro-inverters
(14 panels — 6 Est, 8 Ouest) running firmware **V00.07.04**.

Results: **8 devices · 120 entities** (1 plant device + 7 inverter sub-devices,
each with 16 entities covering per-MPPT-port PV power, energy, voltage, current,
temperature, grid data, alarm, RF link status, plus 4 plant-level environmental
impact sensors — CO2 savings and equivalent young trees planted, both today and
lifetime variants).

---

## Compatible devices

### Officially supported (tested)

| Device | Firmware | Status |
|---|---|---|
| **Hoymiles DTU-Pro** | V00.07.04 | ✅ Fully tested (HMS-1000-2T, 7 inverters / 14 panels) |

### Likely compatible (not yet tested — reports welcome)

These devices are reported by the broader Hoymiles community to expose the same
Modbus TCP register map. The integration **should** work out of the box; please
[open an issue][issues-url] with your model + firmware version + a diagnostics
export so we can confirm and add it to the tested list.

| Device | Notes |
|---|---|
| **DTU-Pro-S** | Newer hardware revision of DTU-Pro, same Modbus TCP server. Confirmed working in upstream community projects. |
| **DTU-W100 / DTU-W100G2** | May expose Modbus TCP depending on firmware revision. |
| **DTU-G100** | Same family; register map likely compatible — to verify. |
| **DTU-Pro v2** | If commercialised — same protocol expected. |

### Not compatible

| Device | Why | Alternative |
|---|---|---|
| **HMS-WiFi inverters** *(no DTU)* | Speak Hoymiles Protobuf TCP, not Modbus TCP | [`suaveolent/ha-hoymiles-wifi`][suav-url] |
| **DTU-Lite** | Older hardware; may lack a Modbus TCP server | — |

> **Adapting to a different DTU**: the protocol code lives in the pure-async
> [`api/`](custom_components/hoymiles_dtupro/api/) sub-package. Most variations
> would amount to register-address overrides in
> [`api/const.py`](custom_components/hoymiles_dtupro/api/const.py) — pull
> requests welcome.

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
- Polling cadence is configurable; default is 60 s for live data.
- Built-in firmware data-size workaround (`apply_data_size_fix`) for known
  Hoymiles DTU firmware quirks.

### Compared to the existing ecosystem

| Project | Transport | Async | Status |
|---|---|---|---|
| **`netnic0/ha-hoymiles-dtupro`** *(this repo)* | Modbus TCP (DTU-Pro wired gateway) | Yes — `pymodbus.AsyncModbusTcpClient` | **Stable v1.9.4 — Silver tier 🥈** — hardware validated |
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

For other Hoymiles DTU models, see [Compatible devices](#compatible-devices) above.

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
| Live data scan interval | `60 s` | Minimum 10 s to avoid stressing the DTU |

Reconfiguring (host changed, scan interval tuning) is done via the
*"Configure"* button on the integration card — entities are preserved.

> 📘 **Energy dashboard setup**: use `sensor.<dtu>_today_production` (state_class
> `total_increasing`) as the **Solar production** source in the HA Energy
> dashboard. See [Energy dashboard — which entity to use](#energy-dashboard--which-entity-to-use)
> below for the full explanation, and [`docs/utility_meter.md`](docs/utility_meter.md)
> for daily / monthly / yearly utility meter recipes.

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
| `sensor.<dtu>_co2_savings_today` | sensor | CO2 emissions avoided today (kg, `state_class: total_increasing`). Default factor matches the Hoymiles app; configurable via OptionsFlow. |
| `sensor.<dtu>_equivalent_trees_planted_today` | sensor | Equivalent young trees planted today (fractional count, `state_class: total_increasing`). |
| `sensor.<dtu>_co2_savings_lifetime` | sensor | CO2 emissions avoided since installation (kg, `state_class: total`). Derived from the plant lifetime energy; same configurable factor as today. |
| `sensor.<dtu>_equivalent_trees_planted_lifetime` | sensor | Lifetime equivalent young trees planted (fractional count, `state_class: total`). |
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

## Energy dashboard — which entity to use

The plant device exposes **two** energy-class sensors that look interchangeable
but serve different purposes. Pick the right one or the HA Energy dashboard
will display misleading totals.

| Use case | Entity | `state_class` | Notes |
|---|---|---|---|
| **HA Energy dashboard → Solar production** | `sensor.<dtu>_today_production` | `total_increasing` | ✅ Designed for this. Resets at midnight via HA's standard meter-cycle logic. |
| Lovelace cards showing lifetime production | `sensor.<dtu>_total_production` | `total` | ⚠️ The DTU resets this register at midnight too (firmware quirk), so HA stores it with `state_class: total` to keep recorder warnings away. **Do not** add it to the Energy dashboard. |

### Why not `total_production` in the Energy dashboard?

The Energy dashboard *does* accept `state_class: total` sources, so HA will
let you pick `total_production` — but the DTU's midnight reset will be
interpreted as a "meter replacement" by HA's long-term statistics engine, and
the delta of the last few minutes before midnight is lost from the daily sum.
Over months this drifts.

`today_production` was added precisely to feed the Energy dashboard with a
clean `total_increasing` series. Use it.

> Since **v1.9.4** the plant `today_production` is also protected against
> single-poll RF-flap drops by an in-memory monotone clamp in the coordinator
> (see [CHANGELOG](CHANGELOG.md)). If you upgraded from an earlier version and
> had installed a Riemann-sum + utility_meter workaround, you can remove it.

### Do not force `state_class: total_increasing` on `total_production`

A common workaround on community forums is to override `total_production`'s
state class via `customize.yaml`:

```yaml
# DON'T DO THIS
sensor.<dtu>_total_production:
  state_class: total_increasing
```

This re-introduces the very HA recorder warnings the integration's
`state_class: total` choice was meant to silence (see commit
[`13b3a13`](https://github.com/netnic0/ha-hoymiles-dtupro/commit/13b3a13)),
and corrupts long-term statistics every night.

### For utility meters

If you want extra `utility_meter` sensors on top of the Energy dashboard,
use `today_production` (or a Riemann sum of `pv_power`) as the source — not
`total_production`. Full recipes in [`docs/utility_meter.md`](docs/utility_meter.md).

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

Released:
- **v1.0.0** — Initial public release (config flow, sensor wiring, hardware validated, brand assets, Lovelace examples).
- **v1.4.0** — Diagnostics platform + Repair Issues (DTU unreachable / inverter offline thresholds).
- **v1.5.0** — Modbus retry + exponential backoff (resilience).
- **v1.6.0** — OptionsFlow with 8 user-tunable knobs (scan intervals, retries, backoff, alert thresholds).
- **v1.7.0** — mypy strict expanded to the full HA layer; Silver prerequisites (PARALLEL_UPDATES, reconfigure i18n, utility_meter doc).
- **v1.8.0** — **Silver tier 🥈** reached (>=95% HA-layer coverage, 28 quality_scale rules).
- **v1.9.0** — CO2 savings + equivalent young trees planted sensors with user-configurable factors.
- **v1.9.1** — Bug A fix: plant-level `total_production` deduplication by `serial_number` (was ×4–5 overcounting from MPPT-port replication of `total_wh`).
- **v1.9.2 / v1.9.3** — README docs refresh: clarify which entity to use in the HA Energy dashboard; roadmap status pass.
- **v1.9.4** — Bug B fix: `today_production` RF-flap clamp. The plant `today_production` (and the derived CO2/trees-today sensors) no longer drop when an inverter's RF link briefly flaps, which had been inflating HA Energy dashboard totals by 10–20×. New in-memory `TodayCache` in the coordinator clamps the value monotonically within the local day. **This is the recommended baseline for the HA Energy dashboard.**

Forward-looking:
- **Lifetime environmental sensors** *(this PR)* — `co2_savings_lifetime` and `equivalent_trees_planted_lifetime`, symmetric to the today variants but derived from `total_production` (dedup'd by serial since v1.9.1) with `state_class: total`. Ship in the next release.
- **Per-port `today_production` resilience (Wave 2)** — when an inverter's RF link flaps, its two per-port `today_production` entities currently return their last raw value; planned to return `None` instead so HA marks them unavailable cleanly. Plant-level is already fixed via v1.9.4's `TodayCache`.
- **Per-inverter power limit service** — implement the `set_inverter_limit` service handler (currently a skeleton — see `services.yaml`).
- **Gold-tier candidate** — strict-typing of test code, full action-exception handling, accessibility audit.

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
