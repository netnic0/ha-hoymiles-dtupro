# Third-party credits

This integration would not exist without the prior reverse-engineering and
design work of the following open-source projects, both released under the
MIT License (compatible with this project's own MIT license).

---

## ArekKubacki / Hoymiles-Plant-DTU-Pro

> Source: <https://github.com/ArekKubacki/Hoymiles-Plant-DTU-Pro>
> License: MIT

The byte-precise layout of the DTU-Pro Modbus payload (40 bytes per inverter
record, register `0x1000 + i*40`, big-endian struct format with mixed
`uint16/uint32/int16` fields, `_data_size_fixer` workaround for the firmware's
packet size byte) was learned by reading this project's `hoymiles/datatypes.py`
and `hoymiles/client.py`.

The pure decoder in `ha_hoymiles_dtupro/decoder.py` and the constant
`INVERTER_FMT` in `ha_hoymiles_dtupro/const.py` are independent re-implementations
of that knowledge using only the Python standard library (`struct`), without
copying source code.

```text
MIT License

Copyright (c) 2023 Arek Kubacki

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## suaveolent / ha-hoymiles-wifi

> Source: <https://github.com/suaveolent/ha-hoymiles-wifi>
> License: MIT

While this project does **not** share any code or transport layer with
`ha-hoymiles-wifi` (that integration speaks Protobuf over TCP port 10081 to
inverters with WiFi modules; this one speaks Modbus TCP to the wired DTU-Pro),
its modern architecture inspired several decisions in this repository:

- The four-layer split (HA integration → Coordinators → pure async client → models).
- The use of frozen `@dataclass` models instead of `plum-py` `Structure`s.
- The discipline of `raise UpdateFailed(...) from err` for backoff-friendly errors.
- The pattern of `via_device` linking inverter sub-devices to a parent DTU device.

```text
MIT License

Copyright (c) 2024 suaveolent

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## Hoymiles-Modbus protocol specification

The Modbus register map of the DTU-Pro is **not** publicly documented by
Hoymiles. The understanding embodied in `MODBUS_PROTOCOL_DTUPRO.md` (in the
companion `photovoltaique-ve` notes) is the result of community-driven reverse
engineering, primarily through `ArekKubacki/Hoymiles-Plant-DTU-Pro`.
