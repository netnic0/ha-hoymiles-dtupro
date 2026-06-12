# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
Releases are automated by [release-please](https://github.com/googleapis/release-please)
from [Conventional Commits](https://www.conventionalcommits.org/).

## [1.5.0](https://github.com/netnic0/ha-hoymiles-dtupro/compare/v1.4.0...v1.5.0) (2026-06-12)


### Features

* **api:** add bounded retry with exponential backoff to Modbus client ([21dc9cd](https://github.com/netnic0/ha-hoymiles-dtupro/commit/21dc9cdb93415a5b8185d5dffd0b3d7473857064))
* **api:** add bounded retry with exponential backoff to Modbus client ([cb31935](https://github.com/netnic0/ha-hoymiles-dtupro/commit/cb31935971e42e5c7a51813e2fb645da3dea81c7))
* **diagnostics,repairs:** enrich diagnostics and add Repair Issues ([b22ba0b](https://github.com/netnic0/ha-hoymiles-dtupro/commit/b22ba0b4ead19db470dbbec72f4829d5ed3a53ab))

## [Unreleased]

### Added

- **OptionsFlow** — eight user-tunable knobs are now reachable from the
  integration's *Configure* button in the HA UI, without requiring a removal
  and re-add of the integration:
  - **Polling**: `scan_interval_real_data` (10–600 s) and
    `scan_interval_metadata` (60–3600 s).
  - **Modbus client**: `timeout_s` (2–30 s), `retry_attempts` (1–10),
    `backoff_initial_s` (0–5 s), `backoff_max_s` (0.5–30 s) — these wire into
    the bounded retry / exponential backoff machinery introduced in v1.5.0.
  - **Repair Issue thresholds**: `dtu_unreachable_threshold_min` (1–60 min)
    and `inverter_offline_threshold_h` (1–168 h) — replaces the previously
    hardcoded `ISSUE_DTU_UNREACHABLE_THRESHOLD` and
    `ISSUE_INVERTER_OFFLINE_THRESHOLD`.
- Cross-field validation: `backoff_initial_s` cannot exceed `backoff_max_s`
  (form error `backoff_initial_above_max`).
- Update listener wired via `entry.add_update_listener` — the integration
  reloads automatically when options change so new values take effect
  immediately.
- New `tests/test_options_flow.py` (7 cases): migration v1.1→v1.2,
  options-form rendering, valid-submission persistence, parametrised
  out-of-range rejection, and inverted-backoff cross-field error.
- Extra coordinator tests asserting custom thresholds are honoured by both
  coordinators (real-data and metadata).
- PR #3 follow-ups (from senior code review): `_open()` failure path now
  exercised in `tests/test_client.py`, exception `__cause__` chain
  preservation asserted, and the `# type: ignore[misc]` rationale comment
  expanded to explain why mypy cannot prove the loop invariant.

### Changed

- **Schema migration**: `MINOR_VERSION` bumped from 1 to 2. Existing entries
  carrying `scan_interval_real_data` in `entry.data` are migrated on first
  load — the value moves to `entry.options`. Net effect for existing users:
  the previously collected scan interval (which was silently ignored — see
  Fixed) is now actually honoured by the coordinator.
- `HoymilesRealDataCoordinator` and `HoymilesMetadataCoordinator` constructors
  accept new `dtu_unreachable_threshold` / `inverter_offline_threshold`
  kwargs. Defaults preserve previous behaviour (5 min / 6 h).
- `async_setup_entry` reads all 8 options via `entry.options.get(KEY,
  DEFAULT)` and passes them to the client and coordinators.
- Translations updated for EN, FR, DE, ES — new `options.step.init` block
  with title, description, eight `data` labels, and eight `data_description`
  hints (including the post-reload threshold-reset behaviour).
- CHANGELOG `[Unreleased]` housekeeping: removed a duplicate `[Unreleased]`
  block whose content shipped in v1.4.0 (PR #3 review follow-up).

### Fixed

- **`scan_interval_real_data` was collected by the user step but never read
  by `async_setup_entry`**, so coordinators always polled at the hardcoded
  60 s default. The migration above wires the value end-to-end.

### Not Changed (intentional)

- The reconfigure-step probe still uses the hardcoded `DEFAULT_TIMEOUT_S`
  (5 s) for the connectivity check. Captured as deferred technical debt for
  PR #5.
- HA's `last_update_success_time` is `None` immediately after a reload, so
  lowering `dtu_unreachable_threshold_min` does not retroactively fire the
  issue — the threshold counter restarts from the next successful poll.
  Documented in the relevant `data_description` translation strings.

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
