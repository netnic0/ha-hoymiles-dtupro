# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
Releases are automated by [release-please](https://github.com/googleapis/release-please)
from [Conventional Commits](https://www.conventionalcommits.org/).

## [Unreleased]

### Added

- **Modbus client resilience** — bounded retry with exponential backoff for
  transient TCP failures. Connection drops and timeouts now trigger up to 3
  attempts (default) within a single `async_get_plant_data` /
  `async_get_inverters` / `async_get_dtu_serial` fetch, with 0.5 → 1 → 2 s
  backoff capped at 4 s. Worst-case wall-clock ~16.5 s, well below the 60 s
  polling interval and the 5-min `dtu_unreachable` Repair Issue threshold.
  Each attempt opens a fresh TCP socket (transactional retry at the public-API
  boundary).
- New `HoymilesAsyncClient` constructor kwargs `retry_attempts`,
  `backoff_initial_s`, `backoff_max_s` (defaults in `api/const.py`). PR #4 will
  expose these via the OptionsFlow.
- Three `tests/test_client.py` cases covering retry-on-connection-error,
  retry-on-timeout, no-retry-on-protocol-error, and an additional
  exhaustion-with-fresh-socket-contract assertion (`connect.await_count == 3`).

### Changed

- Public methods `async_get_dtu_serial`, `async_get_inverters`, and
  `async_get_plant_data` now delegate to internal `_fetch_*_once` helpers
  through a single `_fetch_with_retry` orchestrator. **No change to the
  external API contract.**
- `HoymilesProtocolError` is **not** retried — these errors are deterministic
  (malformed frame at a specific slot) and retrying wastes wall-clock time.
- `api/const.py`: dead constant `DEFAULT_RETRIES` renamed to
  `DEFAULT_RETRY_ATTEMPTS` and is now actually wired into the client. Two new
  constants `DEFAULT_BACKOFF_INITIAL_S` and `DEFAULT_BACKOFF_MAX_S` were added.

### Added

- **Repair Issues** powered by `homeassistant.helpers.issue_registry`:
  - `dtu_unreachable_<entry_id>` — fires (severity ERROR) when the DTU has not
    answered for more than **5 minutes**, and is automatically cleared on the
    next successful poll.
  - `inverter_offline_<serial>_<entry_id>` — fires (severity WARNING) per
    inverter once `link_status=False` has held continuously for more than
    **6 hours**. **Guard:** an inverter that has *never* been observed online
    since this integration load will not raise the issue — this prevents
    false positives on freshly added hardware.
- **Diagnostics enriched** with a new `coordinator_state` section exposing,
  for each coordinator, the runtime values of `last_update_success`,
  `last_update_success_time`, `update_interval_seconds`, `online_inverter_count`,
  and `inverter_count`.
- New translation keys (`issues.dtu_unreachable`, `issues.inverter_offline_long`)
  in `strings.json` and all four bundled languages (EN/FR/DE/ES).
- Extensive `tests/test_repairs.py` covering: below-threshold no-op, above-threshold
  fire, recovery clears, never-seen-online guard.

### Changed

- **Coordinators migrated** from `DataUpdateCoordinator` to
  `TimestampDataUpdateCoordinator`. This is the HA-blessed base class that
  exposes `last_update_success_time` natively — required to compute the
  unreachable threshold without reinventing state tracking.
- Coordinator constructors now require `entry_id` (and `host` for the real-data
  coordinator). This change is internal: external callers must pass these
  values when instantiating coordinators directly. The integration's
  `async_setup_entry` is updated accordingly.
- `async_unload_entry` now calls `async_delete_issue` for every Repair Issue
  the integration could have raised, preventing stale issue cards after an
  integration reload.

### Not Changed (intentional)

- Thresholds (5 min / 6 h) are hardcoded in `const.py`. PR #4 (OptionsFlow)
  will make them user-configurable.
- Diagnostics deliberately omit raw Modbus frames and per-inverter
  `_last_seen_online` timestamps to avoid leaking installation-specific data
  in public bug reports.

## [1.4.0](https://github.com/netnic0/ha-hoymiles-dtupro/compare/v1.3.0...v1.4.0) (2026-06-11)


### Features

* **sensor:** suggest kWh display unit and mark alarms diagnostic ([656c661](https://github.com/netnic0/ha-hoymiles-dtupro/commit/656c6615fd0fb63105ef48a3e45cfc4ee05fb65a))
* **sensor:** suggest kWh display unit and mark alarms diagnostic ([a704738](https://github.com/netnic0/ha-hoymiles-dtupro/commit/a704738ce1421d12db208ef7b1b83fcc75cf5569))

## [1.3.0](https://github.com/netnic0/ha-hoymiles-dtupro/compare/v1.2.0...v1.3.0) (2026-06-05)


### Features

* add brand icons directly in integration (HA 2026.3+) ([ddc1c98](https://github.com/netnic0/ha-hoymiles-dtupro/commit/ddc1c98079374f9983a16dd4ce3ef831716b8cda))

## [1.2.0](https://github.com/netnic0/ha-hoymiles-dtupro/compare/v1.1.1...v1.2.0) (2026-06-05)


### Features

* **api:** add async Modbus client and pure decoders ([5644200](https://github.com/netnic0/ha-hoymiles-dtupro/commit/56442007d9a564dd22bc0f20d7e3d334abe69882))
* **ci:** add test-ha job running pytest-homeassistant-custom-component ([9d5bef0](https://github.com/netnic0/ha-hoymiles-dtupro/commit/9d5bef086b004f1d0afa4d3c23a3b76285c96130))
* **integration:** add Home Assistant integration skeleton ([3662a73](https://github.com/netnic0/ha-hoymiles-dtupro/commit/3662a73b61dcd394114f32dd8c604e706df91993))
* **integration:** move api package under custom_components for HACS compatibility ([853cb69](https://github.com/netnic0/ha-hoymiles-dtupro/commit/853cb69522f5a0980d350bf08c1b2dfaadaf428b))
* **lovelace:** add mushroom and full dashboard examples ([fce5bb9](https://github.com/netnic0/ha-hoymiles-dtupro/commit/fce5bb9295f91e306dc7e83bea46743f5f66224f))
* **sensor:** M2 full sensor wiring — port-level entities for HMS-1000-2T ([32e78ac](https://github.com/netnic0/ha-hoymiles-dtupro/commit/32e78ac0f10e8b29e5292e54ceee2fd1778cc5ca))


### Bug Fixes

* **api,manifest:** pymodbus 3.7+ device_id and hassfest manifest order ([7b7438f](https://github.com/netnic0/ha-hoymiles-dtupro/commit/7b7438fc9b21172447247f46930585759ebc712a))
* **ci:** satisfy ruff lint and format on first CI run ([e9ef5f6](https://github.com/netnic0/ha-hoymiles-dtupro/commit/e9ef5f634dc79121b9b28f60309f3ffbb650d2fa))
* **client:** wire apply_data_size_fix before inverter payload decoding ([2cc50dd](https://github.com/netnic0/ha-hoymiles-dtupro/commit/2cc50dd85f42155dfcc9689c19c58cb13d2a56d1))
* **coordinator:** raise default scan interval to 60 s ([42e2ec9](https://github.com/netnic0/ha-hoymiles-dtupro/commit/42e2ec97283b43a7b39cca3b363ed8ef4e505313))
* **diagnostics:** suppress DTU serial leak via config entry title ([428891d](https://github.com/netnic0/ha-hoymiles-dtupro/commit/428891dfded3d397172d7031fe4c52ae542b79bb))
* **sensor:** use TOTAL state_class for total_production ([13b3a13](https://github.com/netnic0/ha-hoymiles-dtupro/commit/13b3a13ba168d3ab3f140412835f75884ede54b7))
* **test:** adjust HA-native tests for HA 2026.x and avoid editable-install hook ([4e4a387](https://github.com/netnic0/ha-hoymiles-dtupro/commit/4e4a38744280aef5bbc2e7820cf2687d0b45c4dd))


### Documentation

* add README, CONTRIBUTING, CHANGELOG, and minimal Lovelace example ([4b8cda6](https://github.com/netnic0/ha-hoymiles-dtupro/commit/4b8cda6d59b487943ae3e7abc74ed3b7a8df130a))
* **readme:** update status to Stable v1.0.0 ([1149819](https://github.com/netnic0/ha-hoymiles-dtupro/commit/11498198164f34328ae9727ec59edab8892ee121))
* **readme:** use English entity key names in entity table ([2fc1d55](https://github.com/netnic0/ha-hoymiles-dtupro/commit/2fc1d55d89fde85b1d2baf69e8f6fc724f6a56f9))
* update README to reflect v0.3.1-alpha.1 hardware-validated state ([fce5bb9](https://github.com/netnic0/ha-hoymiles-dtupro/commit/fce5bb9295f91e306dc7e83bea46743f5f66224f))

## [1.1.1](https://github.com/netnic0/ha-hoymiles-dtupro/compare/v1.1.0...v1.1.1) (2026-06-05)


### Documentation

* **readme:** update status to Stable v1.0.0 ([1149819](https://github.com/netnic0/ha-hoymiles-dtupro/commit/11498198164f34328ae9727ec59edab8892ee121))

## [1.1.0](https://github.com/netnic0/ha-hoymiles-dtupro/compare/v1.0.0...v1.1.0) (2026-06-05)


### Features

* **api:** add async Modbus client and pure decoders ([5644200](https://github.com/netnic0/ha-hoymiles-dtupro/commit/56442007d9a564dd22bc0f20d7e3d334abe69882))
* **ci:** add test-ha job running pytest-homeassistant-custom-component ([9d5bef0](https://github.com/netnic0/ha-hoymiles-dtupro/commit/9d5bef086b004f1d0afa4d3c23a3b76285c96130))
* **integration:** add Home Assistant integration skeleton ([3662a73](https://github.com/netnic0/ha-hoymiles-dtupro/commit/3662a73b61dcd394114f32dd8c604e706df91993))
* **integration:** move api package under custom_components for HACS compatibility ([853cb69](https://github.com/netnic0/ha-hoymiles-dtupro/commit/853cb69522f5a0980d350bf08c1b2dfaadaf428b))
* **lovelace:** add mushroom and full dashboard examples ([fce5bb9](https://github.com/netnic0/ha-hoymiles-dtupro/commit/fce5bb9295f91e306dc7e83bea46743f5f66224f))
* **sensor:** M2 full sensor wiring — port-level entities for HMS-1000-2T ([32e78ac](https://github.com/netnic0/ha-hoymiles-dtupro/commit/32e78ac0f10e8b29e5292e54ceee2fd1778cc5ca))


### Bug Fixes

* **api,manifest:** pymodbus 3.7+ device_id and hassfest manifest order ([7b7438f](https://github.com/netnic0/ha-hoymiles-dtupro/commit/7b7438fc9b21172447247f46930585759ebc712a))
* **ci:** satisfy ruff lint and format on first CI run ([e9ef5f6](https://github.com/netnic0/ha-hoymiles-dtupro/commit/e9ef5f634dc79121b9b28f60309f3ffbb650d2fa))
* **client:** wire apply_data_size_fix before inverter payload decoding ([2cc50dd](https://github.com/netnic0/ha-hoymiles-dtupro/commit/2cc50dd85f42155dfcc9689c19c58cb13d2a56d1))
* **diagnostics:** suppress DTU serial leak via config entry title ([428891d](https://github.com/netnic0/ha-hoymiles-dtupro/commit/428891dfded3d397172d7031fe4c52ae542b79bb))
* **sensor:** use TOTAL state_class for total_production ([13b3a13](https://github.com/netnic0/ha-hoymiles-dtupro/commit/13b3a13ba168d3ab3f140412835f75884ede54b7))
* **test:** adjust HA-native tests for HA 2026.x and avoid editable-install hook ([4e4a387](https://github.com/netnic0/ha-hoymiles-dtupro/commit/4e4a38744280aef5bbc2e7820cf2687d0b45c4dd))


### Documentation

* add README, CONTRIBUTING, CHANGELOG, and minimal Lovelace example ([4b8cda6](https://github.com/netnic0/ha-hoymiles-dtupro/commit/4b8cda6d59b487943ae3e7abc74ed3b7a8df130a))
* **readme:** use English entity key names in entity table ([2fc1d55](https://github.com/netnic0/ha-hoymiles-dtupro/commit/2fc1d55d89fde85b1d2baf69e8f6fc724f6a56f9))
* update README to reflect v0.3.1-alpha.1 hardware-validated state ([fce5bb9](https://github.com/netnic0/ha-hoymiles-dtupro/commit/fce5bb9295f91e306dc7e83bea46743f5f66224f))

## [0.4.0-alpha.1](https://github.com/netnic0/ha-hoymiles-dtupro/compare/v0.3.1-alpha.1...v0.4.0-alpha.1) (2026-06-05)


### Features

* **lovelace:** add mushroom and full dashboard examples ([fce5bb9](https://github.com/netnic0/ha-hoymiles-dtupro/commit/fce5bb9295f91e306dc7e83bea46743f5f66224f))


### Documentation

* update README to reflect v0.3.1-alpha.1 hardware-validated state ([fce5bb9](https://github.com/netnic0/ha-hoymiles-dtupro/commit/fce5bb9295f91e306dc7e83bea46743f5f66224f))

## [0.3.1-alpha.1](https://github.com/netnic0/ha-hoymiles-dtupro/compare/v0.3.0-alpha.1...v0.3.1-alpha.1) (2026-06-05)


### Bug Fixes

* **client:** wire apply_data_size_fix before inverter payload decoding ([2cc50dd](https://github.com/netnic0/ha-hoymiles-dtupro/commit/2cc50dd85f42155dfcc9689c19c58cb13d2a56d1))

## [0.3.0-alpha.1](https://github.com/netnic0/ha-hoymiles-dtupro/compare/v0.2.1-alpha.1...v0.3.0-alpha.1) (2026-06-05)


### Features

* **sensor:** M2 full sensor wiring — port-level entities for HMS-1000-2T ([32e78ac](https://github.com/netnic0/ha-hoymiles-dtupro/commit/32e78ac0f10e8b29e5292e54ceee2fd1778cc5ca))

## [0.2.1-alpha.1](https://github.com/netnic0/ha-hoymiles-dtupro/compare/v0.2.0-alpha.1...v0.2.1-alpha.1) (2026-06-05)


### Bug Fixes

* **diagnostics:** suppress DTU serial leak via config entry title ([428891d](https://github.com/netnic0/ha-hoymiles-dtupro/commit/428891dfded3d397172d7031fe4c52ae542b79bb))
* **sensor:** use TOTAL state_class for total_production ([13b3a13](https://github.com/netnic0/ha-hoymiles-dtupro/commit/13b3a13ba168d3ab3f140412835f75884ede54b7))

## [0.2.0-alpha.1](https://github.com/netnic0/ha-hoymiles-dtupro/compare/v0.1.1-alpha.1...v0.2.0-alpha.1) (2026-06-04)


### Features

* **ci:** add test-ha job running pytest-homeassistant-custom-component ([9d5bef0](https://github.com/netnic0/ha-hoymiles-dtupro/commit/9d5bef086b004f1d0afa4d3c23a3b76285c96130))
* **integration:** move api package under custom_components for HACS compatibility ([853cb69](https://github.com/netnic0/ha-hoymiles-dtupro/commit/853cb69522f5a0980d350bf08c1b2dfaadaf428b))


### Bug Fixes

* **test:** adjust HA-native tests for HA 2026.x and avoid editable-install hook ([4e4a387](https://github.com/netnic0/ha-hoymiles-dtupro/commit/4e4a38744280aef5bbc2e7820cf2687d0b45c4dd))

## [0.1.1-alpha.1](https://github.com/netnic0/ha-hoymiles-dtupro/compare/v0.1.0-alpha.1...v0.1.1-alpha.1) (2026-06-04)


### Bug Fixes

* **api,manifest:** pymodbus 3.7+ device_id and hassfest manifest order ([7b7438f](https://github.com/netnic0/ha-hoymiles-dtupro/commit/7b7438fc9b21172447247f46930585759ebc712a))
* **ci:** satisfy ruff lint and format on first CI run ([e9ef5f6](https://github.com/netnic0/ha-hoymiles-dtupro/commit/e9ef5f634dc79121b9b28f60309f3ffbb650d2fa))

## [Unreleased]

### Changed

- **UX**: Energy sensors (`today_production`, `total_production`) now suggest
  **kWh** as their display unit via `suggested_unit_of_measurement`. Storage
  remains in Wh — historical data is unaffected, HA only adapts the displayed
  unit so values like `9 935 738 Wh` show up as `9 935.7 kWh`.
- **UX**: Diagnostic entities (`alarm_code`, `alarm_count`) are now categorised as
  `EntityCategory.DIAGNOSTIC`. They appear under the device's *Diagnostics*
  section instead of the main entity list. Existing automations that reference
  these entities continue to work unchanged.
- **i18n**: Sensor labels clarified for better semantic alignment with the
  underlying physical quantity. The `key` of every entity is unchanged, so
  **existing entity IDs are preserved** — only the *friendly name* shown in
  the UI is updated:

  | key                | EN              | FR                        | DE              | ES             |
  |--------------------|-----------------|---------------------------|-----------------|----------------|
  | `pv_power`         | Power           | Puissance instantanée     | Leistung        | Potencia       |
  | `today_production` | Energy today    | Énergie du jour           | Energie heute   | Energía hoy    |
  | `total_production` | Lifetime energy | Énergie totale (cumul)    | Gesamtenergie   | Energía total  |

  **Note for new installs in French locale**: the new labels generate different
  entity slugs (e.g. `sensor.<dtu>_energie_du_jour` instead of
  `sensor.<dtu>_production_du_jour`). The bundled
  `lovelace_examples/full.yaml` and `lovelace_examples/mushroom.yaml` have been
  updated accordingly.

### Added

- Descriptor-level tests in `tests/test_sensor.py` lock down `state_class`,
  `suggested_unit_of_measurement`, and `entity_category` for every sensor —
  preventing accidental regressions on Energy-Dashboard semantics.

### Not Changed (intentional)

- `state_class` of `total_production` remains `TOTAL` (not `TOTAL_INCREASING`).
  Reason: the Hoymiles DTU resets the per-port lifetime counter at midnight
  (see commit `13b3a13`). `TOTAL_INCREASING` would trigger HA recorder warnings
  on each reset; `TOTAL` handles this correctly while still feeding long-term
  statistics.

## [0.1.0-alpha.1] — 2026-06-04

### Added

- Initial alpha release of the modern Hoymiles DTU-Pro integration.
- Four-layer architecture: pure async Modbus library `ha_hoymiles_dtupro/` +
  HA integration `custom_components/hoymiles_dtupro/`.
- 51 unit tests against mocked pymodbus, 96 % coverage on the pure library.
- Internationalisation: English, French, Spanish, German.
- Diagnostics platform skeleton.
- Lovelace minimal example dashboard (built-in cards only).

### Known limitations

- **Not yet validated against real hardware** — pending Phase 1 LAN test on a
  DTU-Pro running firmware V00.07.04. See `README.md` "Experimental status".
- HA-native integration tests (with `pytest-homeassistant-custom-component`)
  are deferred to milestone M2; only the pure library is currently covered.
- `apply_data_size_fix` is implemented as a pure function but not yet wired
  into the async pymodbus client — to be done once we observe the firmware
  bug behaviour in async mode.
- Brand assets (`icon.png`, `logo.png`) not yet submitted to
  [`home-assistant/brands`](https://github.com/home-assistant/brands).

[Unreleased]: https://github.com/netnic0/ha-hoymiles-dtupro/compare/v0.1.0-alpha.1...HEAD
[0.1.0-alpha.1]: https://github.com/netnic0/ha-hoymiles-dtupro/releases/tag/v0.1.0-alpha.1
