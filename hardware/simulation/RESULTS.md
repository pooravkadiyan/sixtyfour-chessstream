# ChessStream circuit simulation results

Numerical integration of the same circuits as `reed_switch.cir`, `mux_timing.cir`, and `power_supply.cir`. Open those files, or the `.asc` schematics, in LTspice XVII if you want the waveform viewer. LTspice is not installed in this workspace, so the numbers below come from the matching Python integration in `run_sim.py`.

## Reed switch and debounce

| Result | Value |
| --- | --- |
| Contact-bounce window | 1.10 ms |
| Time to fall below 0.4 V after the last close | 0.00 us |
| Highest sense voltage while the reed is held | 0.000 V |
| Firmware debounce | 50 ms |
| Debounce margin over the bounce window | 45x |

The 10 kΩ pull-up and 20 pF of stray capacitance settle in well under a microsecond. Reed contact bounce lasts about a millisecond. The firmware in `firmware/src/main.cpp` waits 50 ms before it trusts a square, so a bouncing reed cannot invent a move. A human lift-and-place is much slower than 50 ms, so legal moves are not dropped.

## Multiplexer timing

| Result | Value |
| --- | --- |
| Ron · C time constant | 2.1 ns |
| Analog settle (4 tau) | 8 ns |
| Logic delay used in the model | 30 ns |
| Firmware dwell after each select | 10 us |
| Margin | 260x |

`delayMicroseconds(10)` in the scanner is the right order of magnitude. Four multiplexers are read in parallel, so a full 64-square scan is 16 dwells, about 160 us, against a 10 ms scan period.

## 5 V to 3.3 V under a Wi-Fi burst

Load is 150 mA at idle and 300 mA from 1 ms to 3 ms, standing in for an ESP32 transmit burst. Cout is 10 uF behind 0.2 ohm of regulator impedance.

| Result | Value |
| --- | --- |
| Idle rail | 3.270 V |
| Lowest rail during the burst | 3.240 V |
| Droop | 30.0 mV |
| Rail at 6 ms | 3.270 V |

Droop stays inside the ESP32 3.0–3.6 V operating window. The 10 uF input and output capacitors in the controller schematic are sufficient for this burst. A second 10 uF close to the module is already on the controller (`C3` is 100 nF for the fast edge; `C2` is the bulk 10 uF).

## What to open in LTspice

1. `reed_switch.asc` or `reed_switch.cir` — plot `V(sense)`.
2. `power_supply.cir` — plot `V(vout)` across the 2 ms burst.
3. `mux_timing.cir` — plot `V(com)` after the select edge.
4. `full_scan.cir` — one 10 us select dwell.
