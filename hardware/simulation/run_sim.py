"""Numerical twin of the LTspice decks in this folder.

LTspice is not required. The same circuits are integrated here and the
results are written to RESULTS.md next to the .asc/.cir files.

    python hardware/simulation/run_sim.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

OUT = Path(__file__).resolve().parent / "RESULTS.md"


def reed_waveform(t: np.ndarray) -> np.ndarray:
    """Closed (1) after 1ms, with four bounces, then held."""
    closed = np.zeros_like(t)
    edges = [
        (1.00e-3, 1.25e-3),
        (1.40e-3, 1.55e-3),
        (1.75e-3, 1.90e-3),
        (2.10e-3, 1.0),
    ]
    for a, b in edges:
        closed[(t >= a) & (t < b)] = 1.0
    return closed


def simulate_reed() -> dict:
    dt = 0.2e-6
    t = np.arange(0, 12e-3, dt)
    closed = reed_waveform(t)
    r = 10e3
    c = 20e-12
    v = np.empty_like(t)
    v[0] = 3.3
    # dv/dt = (3.3 - v)/(R C) when open, and a fast pull to 0 when closed (Ron=0.8)
    ron = 0.8
    for i in range(1, len(t)):
        if closed[i]:
            tau = ron * c
            target = 0.0
        else:
            tau = r * c
            target = 3.3
        v[i] = target + (v[i - 1] - target) * np.exp(-dt / tau)
    # last rising bounce ends at 2.10ms; signal must stay < 0.4V after that
    settle_idx = np.where((t >= 2.10e-3) & (v < 0.4))[0][0]
    bounce_end = 2.10e-3
    return {
        "bounce_window_ms": (bounce_end - 1.00e-3) * 1e3,
        "settle_us_after_last_close": (t[settle_idx] - bounce_end) * 1e6,
        "vmin_during_hold": float(v[t > 2.2e-3].max()),
        "firmware_debounce_ms": 50.0,
        "margin": 50.0 / ((bounce_end - 1e-3) * 1e3),
    }


def simulate_power() -> dict:
    dt = 1e-6
    t = np.arange(0, 6e-3, dt)
    iload = np.full_like(t, 0.15)
    iload[(t >= 1e-3) & (t < 3e-3)] = 0.30
    c = 10e-6
    rout = 0.2
    v = np.empty_like(t)
    v[0] = 3.3 - 0.15 * rout
    for i in range(1, len(t)):
        # regulator wants 3.3, series 0.2 ohm into 10uF, load current
        # dV/dt = ((3.3 - V)/Rout - Iload) / C
        dv = (((3.3 - v[i - 1]) / rout) - iload[i]) / c
        v[i] = v[i - 1] + dv * dt
    burst = (t >= 1e-3) & (t < 3.2e-3)
    return {
        "v_idle": float(v[t < 0.5e-3].mean()),
        "v_min_burst": float(v[burst].min()),
        "droop_mv": float((v[t < 0.5e-3].mean() - v[burst].min()) * 1e3),
        "v_recovered": float(v[-1]),
    }


def simulate_mux() -> dict:
    ron = 70.0
    c = 30e-12
    tau = ron * c
    # 4 tau to 1.8% 
    settle = 4 * tau
    logic = 30e-9
    firmware_wait = 10e-6
    return {
        "tau_ns": tau * 1e9,
        "analog_settle_ns": settle * 1e9,
        "logic_delay_ns": logic * 1e9,
        "firmware_wait_us": firmware_wait * 1e6,
        "margin": firmware_wait / (settle + logic),
    }


def main() -> None:
    reed = simulate_reed()
    power = simulate_power()
    mux = simulate_mux()
    text = f"""# ChessStream circuit simulation results

Numerical integration of the same circuits as `reed_switch.cir`, `mux_timing.cir`, and `power_supply.cir`. Open those files, or the `.asc` schematics, in LTspice XVII if you want the waveform viewer. LTspice is not installed in this workspace, so the numbers below come from the matching Python integration in `run_sim.py`.

## Reed switch and debounce

| Result | Value |
| --- | --- |
| Contact-bounce window | {reed['bounce_window_ms']:.2f} ms |
| Time to fall below 0.4 V after the last close | {reed['settle_us_after_last_close']:.2f} us |
| Highest sense voltage while the reed is held | {reed['vmin_during_hold']:.3f} V |
| Firmware debounce | {reed['firmware_debounce_ms']:.0f} ms |
| Debounce margin over the bounce window | {reed['margin']:.0f}x |

The 10 kΩ pull-up and 20 pF of stray capacitance settle in well under a microsecond. Reed contact bounce lasts about a millisecond. The firmware in `firmware/src/main.cpp` waits 50 ms before it trusts a square, so a bouncing reed cannot invent a move. A human lift-and-place is much slower than 50 ms, so legal moves are not dropped.

## Multiplexer timing

| Result | Value |
| --- | --- |
| Ron · C time constant | {mux['tau_ns']:.1f} ns |
| Analog settle (4 tau) | {mux['analog_settle_ns']:.0f} ns |
| Logic delay used in the model | {mux['logic_delay_ns']:.0f} ns |
| Firmware dwell after each select | {mux['firmware_wait_us']:.0f} us |
| Margin | {mux['margin']:.0f}x |

`delayMicroseconds(10)` in the scanner is the right order of magnitude. Four multiplexers are read in parallel, so a full 64-square scan is 16 dwells, about 160 us, against a 10 ms scan period.

## 5 V to 3.3 V under a Wi-Fi burst

Load is 150 mA at idle and 300 mA from 1 ms to 3 ms, standing in for an ESP32 transmit burst. Cout is 10 uF behind 0.2 ohm of regulator impedance.

| Result | Value |
| --- | --- |
| Idle rail | {power['v_idle']:.3f} V |
| Lowest rail during the burst | {power['v_min_burst']:.3f} V |
| Droop | {power['droop_mv']:.1f} mV |
| Rail at 6 ms | {power['v_recovered']:.3f} V |

Droop stays inside the ESP32 3.0–3.6 V operating window. The 10 uF input and output capacitors in the controller schematic are sufficient for this burst. A second 10 uF close to the module is already on the controller (`C3` is 100 nF for the fast edge; `C2` is the bulk 10 uF).

## What to open in LTspice

1. `reed_switch.asc` or `reed_switch.cir` — plot `V(sense)`.
2. `power_supply.cir` — plot `V(vout)` across the 2 ms burst.
3. `mux_timing.cir` — plot `V(com)` after the select edge.
4. `full_scan.cir` — one 10 us select dwell.
"""
    OUT.write_text(text, encoding="utf-8")
    print(OUT)


if __name__ == "__main__":
    main()
