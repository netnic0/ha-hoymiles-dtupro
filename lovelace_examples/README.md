# Lovelace examples for `hoymiles_dtupro`

> Ready-to-paste Lovelace YAML snippets exposing the entities created by the
> Hoymiles DTU-Pro Home Assistant integration.

## Available examples

| File | Required HACS frontend cards | Looks like |
|---|---|---|
| `photovoltaique_minimal.yaml` | **None** (built-in cards only) | Tile, gauge, history-graph, statistics-graph. Clean, minimal. |
| `photovoltaique_mushroom.yaml` | `mushroom`, `apexcharts-card` | Compact mobile-friendly view. KPI tiles with computed icon colors, area/heatmap charts, mushroom-chips for inverter health. **Lixee optional via `type: conditional`.** |
| `photovoltaique_full.yaml` | `mushroom`, `apexcharts-card`, `button-card`, `card-mod`, `vertical-stack-in-card`, `power-flow-card-plus` | Reproduces the user's existing dashboard style: animated SVG circle, 14 PV panels grid with photo background and gradient overlay, power-flow card. **Lixee optional via `type: conditional`.** Requires `/local/images/energie/pv/pv_petit.png`. |

## How to use

1. Open your Home Assistant dashboard YAML (Settings → Dashboards → ⋮ → Edit dashboard → Raw configuration editor).
2. Pick the example that matches the HACS frontend cards you have installed.
3. Copy the `views:` section from the example file.
4. Replace the placeholders:
   - `<DTU_SN>` → your DTU's 12-character serial (e.g. `AABBCCDDEEFF`).
   - `<INV_1>` … `<INV_N>` → each inverter's serial (lowercase, e.g. `1144000000a1`).
5. Reload Lovelace.

## Entity naming convention

The `hoymiles_dtupro` integration registers entities using `translation_key`,
so HA generates entity IDs that follow this pattern:

| Domain entity | Pattern |
|---|---|
| Plant total power | `sensor.hoymiles_pv_pv_power` |
| Plant today energy | `sensor.hoymiles_pv_today_production` |
| Plant lifetime energy | `sensor.hoymiles_pv_total_production` |
| Plant alarm flag | `binary_sensor.hoymiles_pv_alarm` |
| Inverter live power | `sensor.hoymiles_pv_<inv_sn_lower>_pv_power` |
| Inverter temperature | `sensor.hoymiles_pv_<inv_sn_lower>_temperature` |
| Inverter RF link | `binary_sensor.hoymiles_pv_<inv_sn_lower>_link` |

> ⚠️ The `hoymiles_pv_` prefix is the integration's domain slug as exposed by
> HA. If a different prefix appears in your install (e.g. you renamed the
> entry), substitute accordingly via Find & Replace.

## Roadmap (per integration version)

| Integration version | Lovelace assets |
|---|---|
| **v0.1** | none — backend only |
| **v0.5** | this folder (3 YAML examples) |
| **v1.0** | this folder + opt-in `create_dashboard` service that auto-installs the chosen example as a dedicated dashboard |
| **v2.0** _(if community demand)_ | dedicated HACS Plugin repo with a custom Web Component card |
