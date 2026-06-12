# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
Releases are automated by [release-please](https://github.com/googleapis/release-please)
from [Conventional Commits](https://www.conventionalcommits.org/).

## [1.8.0](https://github.com/netnic0/ha-hoymiles-dtupro/compare/v1.7.0...v1.8.0) (2026-06-12)


### Features

* **quality:** bump quality_scale to silver + add quality_scale.yaml ([35ab547](https://github.com/netnic0/ha-hoymiles-dtupro/commit/35ab547ced67757149b9ad91d27fc9a0ee60a8f5))


### Bug Fixes

* **ci:** scope HA-native coverage to the HA layer only ([bfb1bf2](https://github.com/netnic0/ha-hoymiles-dtupro/commit/bfb1bf2a2976203c06762ac7737c8955a5cc1247))


### Documentation

* **changelog:** refresh [Unreleased] block for PR [#5](https://github.com/netnic0/ha-hoymiles-dtupro/issues/5)c ([34dc03c](https://github.com/netnic0/ha-hoymiles-dtupro/commit/34dc03ce28d792b2b7b9823d8d2078659e46d5c2))

## [1.7.0](https://github.com/netnic0/ha-hoymiles-dtupro/compare/v1.6.1...v1.7.0) (2026-06-12)


### Features

* **i18n:** add data_description to the reconfigure step ([46654cc](https://github.com/netnic0/ha-hoymiles-dtupro/commit/46654cc79a52bfbd441eb1cd8f7eb335f18a84de))


### Bug Fixes

* address senior code review of PR [#5](https://github.com/netnic0/ha-hoymiles-dtupro/issues/5)b ([cf9fd6f](https://github.com/netnic0/ha-hoymiles-dtupro/commit/cf9fd6f19168ae32171aa4e211a48222254d10bd))
* **types:** align HA layer with real HA stubs (CI-revealed bugs) ([fb24563](https://github.com/netnic0/ha-hoymiles-dtupro/commit/fb24563c815dcb05f73abb4b9cec4caaa5d17f5b))


### Documentation

* **changelog:** refresh [Unreleased] block for PR [#5](https://github.com/netnic0/ha-hoymiles-dtupro/issues/5)b ([f002ef4](https://github.com/netnic0/ha-hoymiles-dtupro/commit/f002ef4de2294dac29d4c531695b309ff5e472a3))
* **readme:** add 'Compatible devices' section + utility_meter pointer ([03f9c5a](https://github.com/netnic0/ha-hoymiles-dtupro/commit/03f9c5ad7a72772d55d660224d4c7bca1537e122))
* **utility_meter:** add daily/monthly/yearly energy reporting guide ([2932c8f](https://github.com/netnic0/ha-hoymiles-dtupro/commit/2932c8faf130f2645bc6c39d9d16d233d1ae63b4))

## [1.6.1](https://github.com/netnic0/ha-hoymiles-dtupro/compare/v1.6.0...v1.6.1) (2026-06-12)


### Bug Fixes

* **ci:** include test_options_flow and test_repairs in test-ha job ([7bad8f4](https://github.com/netnic0/ha-hoymiles-dtupro/commit/7bad8f4a6a6923181e300a584d0f0e0b93aecf22))
* **config_flow:** honour options timeout_s in _probe_dtu during reconfigure ([d8eb248](https://github.com/netnic0/ha-hoymiles-dtupro/commit/d8eb248d15a6f871db13c699880bdb4d679129c1))
* **tests:** autouse enable_custom_integrations for HA-native tests ([78a4327](https://github.com/netnic0/ha-hoymiles-dtupro/commit/78a4327e7d765475c10c6432447d1963780b6c55))

## [1.6.0](https://github.com/netnic0/ha-hoymiles-dtupro/compare/v1.5.0...v1.6.0) (2026-06-12)


### Features

* **integration:** add OptionsFlow exposing 8 user-tunable knobs ([9fd179a](https://github.com/netnic0/ha-hoymiles-dtupro/commit/9fd179a30c49a3d16f268d872b81a4b2f506be03))
* **integration:** add OptionsFlow exposing 8 user-tunable knobs ([234c081](https://github.com/netnic0/ha-hoymiles-dtupro/commit/234c081411a12fa45af7c6ee6c9be2c70f9a4a5b))


### Bug Fixes

* **tests:** drop scan_interval_real_data from config_flow user_input ([0dc0a25](https://github.com/netnic0/ha-hoymiles-dtupro/commit/0dc0a25f5710a3deb653df1584e60361ff35c659))

## [1.5.0](https://github.com/netnic0/ha-hoymiles-dtupro/compare/v1.4.0...v1.5.0) (2026-06-12)


### Features

* **api:** add bounded retry with exponential backoff to Modbus client ([21dc9cd](https://github.com/netnic0/ha-hoymiles-dtupro/commit/21dc9cdb93415a5b8185d5dffd0b3d7473857064))
* **api:** add bounded retry with exponential backoff to Modbus client ([cb31935](https://github.com/netnic0/ha-hoymiles-dtupro/commit/cb31935971e42e5c7a51813e2fb645da3dea81c7))
* **diagnostics,repairs:** enrich diagnostics and add Repair Issues ([b22ba0b](https://github.com/netnic0/ha-hoymiles-dtupro/commit/b22ba0b4ead19db470dbbec72f4829d5ed3a53ab))

## [Unreleased]

### Added

- **Silver quality_scale tier 🥈** — `manifest.json` now declares
  `"quality_scale": "silver"`, backed by the new
  `custom_components/hoymiles_dtupro/quality_scale.yaml` checklist
  documenting the status of all 28 Bronze + Silver rules (26 `done`,
  2 `exempt` with justification: `action-exceptions` for the placeholder
  service and `reauthentication-flow` for this no-auth Modbus integration).
- **HA-native test coverage ≥ 95 %** on the integration's HA layer
  (`__init__`, `binary_sensor`, `config_flow`, `coordinator`,
  `diagnostics`, `entity`, `sensor`, `const`). Seven new tests across
  two new files:
  - `tests/test_init_coverage.py` — options-update listener triggers
    reload, `async_unload_entry` handles a missing bundle gracefully,
    `async_unload_entry` deletes per-inverter Repair Issues for every
    serial known to the metadata coordinator.
  - `tests/test_config_flow_coverage.py` — `HoymilesMetadataCoordinator`
    wraps `HoymilesError` into `UpdateFailed` with proper `__cause__`
    chain (HA depends on this for retry/backoff scheduling); the
    reconfigure step surfaces `cannot_connect` on `HoymilesError`,
    `unknown` on arbitrary exceptions, and updates `entry.data` with
    `reconfigure_successful` on the happy path.

### Changed

- **CI HA-native coverage scope tightened**. The `test-ha` job's
  `--cov` arg is now an explicit list of HA-layer modules
  (`__init__`, `binary_sensor`, `config_flow`, `const`, `coordinator`,
  `diagnostics`, `entity`, `sensor`), not the whole package. The
  api/ sub-package is mocked in HA-native tests and would otherwise
  drag the score down (mocked-out modules read as low coverage). It
  is already covered by the separate `test` job with its own
  `--cov-fail-under=80`. Coverage floor for `test-ha` raised from
  `60 %` to `95 %` to enforce the Silver gate.

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
