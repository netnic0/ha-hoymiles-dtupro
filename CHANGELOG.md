# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
Releases are automated by [release-please](https://github.com/googleapis/release-please)
from [Conventional Commits](https://www.conventionalcommits.org/).

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
