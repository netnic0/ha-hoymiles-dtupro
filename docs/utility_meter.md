# Daily / monthly / yearly energy reporting

The Hoymiles DTU-Pro integration ships **lifetime energy** sensors with
`state_class: total` on the `total_production` entities (the DTU resets its
lifetime counter at midnight, see [`CHANGELOG.md`](../CHANGELOG.md), commit
`13b3a13`). The `today_production` entities use `state_class: total_increasing`
(they monotonically grow within a day).

To get readable **per-day / per-month / per-year** totals, pair these sensors
with Home Assistant's built-in [`utility_meter`][hac-utility-meter]
integration. `utility_meter` works with both `state_class` values.

This guide is verified against Home Assistant **2026.x** YAML schema (see
the official [utility_meter docs][hac-utility-meter] for the full reference).

---

## What you'll get

| Sensor created by `utility_meter` | Source | Cycle |
|---|---|---|
| `sensor.<name>_daily` | one of our `today_production` / `total_production` sensors | `daily` |
| `sensor.<name>_monthly` | same | `monthly` |
| `sensor.<name>_yearly` | same | `yearly` |

These appear in the **Energy dashboard** automatically once you assign them
under *Settings → Dashboards → Energy → Solar production*.

---

## Example 1 — Per-MPPT-port utility_meter

For an HMS-1000-2T inverter with two MPPT ports, you may want to track each
panel separately. Replace `<sn>` with the inverter's 12-character serial.

```yaml
# configuration.yaml
utility_meter:
  panel_east_daily:
    source: sensor.<sn>_lifetime_energy_1
    name: Panel East — daily
    cycle: daily
  panel_east_monthly:
    source: sensor.<sn>_lifetime_energy_1
    name: Panel East — monthly
    cycle: monthly
  panel_east_yearly:
    source: sensor.<sn>_lifetime_energy_1
    name: Panel East — yearly
    cycle: yearly

  panel_west_daily:
    source: sensor.<sn>_lifetime_energy_2
    name: Panel West — daily
    cycle: daily
  panel_west_monthly:
    source: sensor.<sn>_lifetime_energy_2
    name: Panel West — monthly
    cycle: monthly
  panel_west_yearly:
    source: sensor.<sn>_lifetime_energy_2
    name: Panel West — yearly
    cycle: yearly
```

> **Entity ID format**: HA derives the slug from the `translation_key` in your
> locale. In English: `sensor.<sn>_lifetime_energy_<port>`. In French:
> `sensor.<sn>_energie_totale_cumul_<port>`. Adjust `source:` accordingly.

---

## Example 2 — Per-inverter sum (template + utility_meter)

If you want one row per inverter (sum of both MPPT ports), first build a
template sensor that sums port 1 and port 2, **then** feed the
`utility_meter` from that template.

```yaml
# configuration.yaml
template:
  - sensor:
      - name: "Inverter <sn> total energy"
        unique_id: hoymiles_inv_<sn>_total
        device_class: energy
        state_class: total
        unit_of_measurement: Wh
        state: >
          {{ (states('sensor.<sn>_lifetime_energy_1') | float(0)
              + states('sensor.<sn>_lifetime_energy_2') | float(0))
              | round(0) }}
        availability: >
          {{ has_value('sensor.<sn>_lifetime_energy_1')
             and has_value('sensor.<sn>_lifetime_energy_2') }}

utility_meter:
  inverter_<sn>_daily:
    source: sensor.inverter_<sn>_total_energy
    cycle: daily
  inverter_<sn>_monthly:
    source: sensor.inverter_<sn>_total_energy
    cycle: monthly
  inverter_<sn>_yearly:
    source: sensor.inverter_<sn>_total_energy
    cycle: yearly
```

---

## Example 3 — Whole-plant utility_meter

For most users, the simplest setup uses the plant-level
`sensor.<dtu>_lifetime_energy` directly:

```yaml
# configuration.yaml
utility_meter:
  plant_daily:
    source: sensor.<dtu>_lifetime_energy
    cycle: daily
  plant_monthly:
    source: sensor.<dtu>_lifetime_energy
    cycle: monthly
  plant_yearly:
    source: sensor.<dtu>_lifetime_energy
    cycle: yearly
```

Then in *Settings → Dashboards → Energy → Solar production*, point at
`sensor.plant_yearly` (or any of the cycles).

---

## Important caveats

### `state_class: total` and the DTU midnight reset

Our integration declares `state_class: total` (not `total_increasing`) on
all `total_production` (lifetime) sensors. Reason: the DTU-Pro firmware
resets the lifetime counter at midnight, which would trigger
*"Spike removed"* warnings under `total_increasing` and confuse the HA
recorder's long-term statistics. The `today_production` sensors, in
contrast, use `state_class: total_increasing` — they monotonically grow
between midnight and the next midnight, then reset cleanly with the day.

`utility_meter` works correctly with both classes. With `total` (our
`total_production` case) you do **not** need to set the optional
`delta_values: false` (it is the default) — `utility_meter` interprets
each new value as a cumulative reading, exactly what we publish.

### `periodically_resetting` (default `true`)

The default `periodically_resetting: true` is correct here: the DTU's
midnight reset is treated as expected, not as data loss. If you ever see
strange jumps, set `periodically_resetting: false` and reload the YAML.

### Cycle precision

The cycle uses calendar boundaries (midnight, the 1st of the month, the
1st of January). HA's built-in `utility_meter` runs internal scheduled
resets — no need for additional automation.

### Migration from previous versions

If you had `utility_meter` set up against the older `today_production`
sensor (`state_class: total_increasing` before v1.0.0), you do **not**
need to change anything: the source is still valid. Only the underlying
state class on lifetime sensors changed.

---

## Reference

- [Home Assistant — utility_meter integration][hac-utility-meter]
- [`CHANGELOG.md`](../CHANGELOG.md) — see the v1.0.0 entry on the DTU
  midnight reset and `state_class: total` decision.

[hac-utility-meter]: https://www.home-assistant.io/integrations/utility_meter/
