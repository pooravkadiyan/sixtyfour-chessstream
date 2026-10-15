# Hardware Design Documentation

## Overview

The ChessStream board uses a simple but effective sensing approach:
- **64 reed switches** arranged in an 8x8 grid (one per square)
- **4 multiplexers** (CD74HC4067) to read all switches with minimal GPIO
- **ESP32** microcontroller for WiFi connectivity and processing
- **Neodymium magnets** embedded in chess piece bases

## Schematic

### Block Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         CHESS BOARD                              │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    8x8 Reed Switch Matrix                │    │
│  │   a8  b8  c8  d8  e8  f8  g8  h8                        │    │
│  │   ○   ○   ○   ○   ○   ○   ○   ○   ← Row 8              │    │
│  │   a7  b7  c7  d7  e7  f7  g7  h7                        │    │
│  │   ○   ○   ○   ○   ○   ○   ○   ○   ← Row 7              │    │
│  │   ...                                                    │    │
│  │   a1  b1  c1  d1  e1  f1  g1  h1                        │    │
│  │   ○   ○   ○   ○   ○   ○   ○   ○   ← Row 1              │    │
│  └─────────────────────────────────────────────────────────┘    │
│                              │                                   │
│                              ▼                                   │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐               │
│  │  MUX 1  │ │  MUX 2  │ │  MUX 3  │ │  MUX 4  │               │
│  │ (a1-h2) │ │ (a3-h4) │ │ (a5-h6) │ │ (a7-h8) │               │
│  │CD74HC   │ │CD74HC   │ │CD74HC   │ │CD74HC   │               │
│  │  4067   │ │  4067   │ │  4067   │ │  4067   │               │
│  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘               │
│       │           │           │           │                     │
│       └───────────┴─────┬─────┴───────────┘                     │
│                         │                                        │
│                         ▼                                        │
│              ┌─────────────────────┐                            │
│              │       ESP32         │                            │
│              │   ┌─────────────┐   │                            │
│              │   │   WiFi      │   │◄──── 2.4GHz Antenna        │
│              │   └─────────────┘   │                            │
│              │   GPIO 32-35 (MUX)  │                            │
│              │   GPIO 25-28 (SEL)  │                            │
│              └──────────┬──────────┘                            │
│                         │                                        │
│                    USB-C (5V)                                    │
└─────────────────────────────────────────────────────────────────┘
```

### Pin Mapping

#### ESP32 GPIO Assignments

| GPIO | Function | Description |
|------|----------|-------------|
| 32 | MUX1_SIG | Multiplexer 1 signal output |
| 33 | MUX2_SIG | Multiplexer 2 signal output |
| 34 | MUX3_SIG | Multiplexer 3 signal output |
| 35 | MUX4_SIG | Multiplexer 4 signal output |
| 25 | SEL_A | Multiplexer select bit 0 |
| 26 | SEL_B | Multiplexer select bit 1 |
| 27 | SEL_C | Multiplexer select bit 2 |
| 14 | SEL_D | Multiplexer select bit 3 |
| 2 | LED | Status LED |

#### Multiplexer Channel Mapping

Each CD74HC4067 has 16 channels (0-15). We map them to squares:

**MUX 1 (Rows 1-2):**
| Channel | Square | Channel | Square |
|---------|--------|---------|--------|
| 0 | a1 | 8 | a2 |
| 1 | b1 | 9 | b2 |
| 2 | c1 | 10 | c2 |
| 3 | d1 | 11 | d2 |
| 4 | e1 | 12 | e2 |
| 5 | f1 | 13 | f2 |
| 6 | g1 | 14 | g2 |
| 7 | h1 | 15 | h2 |

**MUX 2 (Rows 3-4):** Same pattern for a3-h4  
**MUX 3 (Rows 5-6):** Same pattern for a5-h6  
**MUX 4 (Rows 7-8):** Same pattern for a7-h8

### Reed Switch Circuit

Each reed switch is connected with a pull-up resistor:

```
    VCC (3.3V)
        │
        ├──[10kΩ]──┬──► To MUX Channel
        │          │
        │       [Reed]
        │          │
        └──────────┴──► GND (when magnet present)
```

- **No magnet**: Reed switch OPEN → GPIO reads HIGH (1)
- **Magnet present**: Reed switch CLOSED → GPIO reads LOW (0)

### Power Supply

```
USB-C (5V) ──► AMS1117-3.3 ──► 3.3V Rail
                    │
                    ├──► ESP32 (3.3V)
                    ├──► Multiplexers (3.3V)
                    └──► Pull-up resistors
```

- Input: 5V via USB-C
- Regulated: 3.3V via AMS1117-3.3
- Current draw: ~150mA typical, ~300mA peak (WiFi TX)

## PCB Design

### Layer Stack-up

2-layer PCB:
- **Top**: Components, signal traces
- **Bottom**: Ground plane, power traces

### Design Rules

| Parameter | Value |
|-----------|-------|
| Trace width (signal) | 0.25mm |
| Trace width (power) | 0.5mm |
| Clearance | 0.2mm |
| Via size | 0.8mm/0.4mm |
| Board thickness | 1.6mm |

### PCB Dimensions

- **Main board**: 450mm x 450mm (standard tournament size)
- **Controller board**: 80mm x 50mm (separate, connects via ribbon cable)

## Bill of Materials (BOM)

### Electronics

| Ref | Component | Qty | Unit Cost | Total | Supplier |
|-----|-----------|-----|-----------|-------|----------|
| U1 | ESP32-WROOM-32E | 1 | ₹125 | ₹125 | AliExpress |
| U2-U5 | CD74HC4067 | 4 | ₹25 | ₹100 | AliExpress |
| U6 | AMS1117-3.3 | 1 | ₹5 | ₹5 | AliExpress |
| SW1-SW64 | Reed switch (glass) | 64 | ₹4 | ₹256 | AliExpress |
| R1-R64 | 10kΩ 0805 | 64 | ₹0.50 | ₹32 | AliExpress |
| C1-C6 | 100nF 0805 | 6 | ₹1 | ₹6 | AliExpress |
| C7-C8 | 10µF 0805 | 2 | ₹2 | ₹4 | AliExpress |
| J1 | USB-C connector | 1 | ₹15 | ₹15 | AliExpress |
| LED1 | LED 0805 (blue) | 1 | ₹1 | ₹1 | AliExpress |
| R65 | 330Ω 0805 | 1 | ₹0.50 | ₹0.50 | AliExpress |
| | **Electronics Total** | | | **₹544.50** | |

### Mechanical

| Item | Qty | Unit Cost | Total | Supplier |
|------|-----|-----------|-------|----------|
| PCB (450x450mm, 2-layer) | 1 | ₹300 | ₹300 | JLCPCB |
| Controller PCB (80x50mm) | 1 | ₹50 | ₹50 | JLCPCB |
| MDF board (500x500x6mm) | 1 | ₹100 | ₹100 | Local |
| Acrylic sheet (500x500x3mm) | 1 | ₹150 | ₹150 | Local |
| Vinyl squares (printed) | 1 | ₹50 | ₹50 | Local |
| Rubber feet | 4 | ₹5 | ₹20 | Local |
| Screws, standoffs | lot | ₹30 | ₹30 | Local |
| | **Mechanical Total** | | | **₹700** | |

### Chess Pieces

| Item | Qty | Unit Cost | Total | Supplier |
|------|-----|-----------|-------|----------|
| Plastic chess pieces (tournament) | 1 set | ₹150 | ₹150 | Local |
| Neodymium magnets (10x3mm) | 32 | ₹4 | ₹128 | AliExpress |
| | **Pieces Total** | | | **₹278** | |

### Total BOM

| Category | Cost |
|----------|------|
| Electronics | ₹544.50 |
| Mechanical | ₹700 |
| Chess Pieces | ₹278 |
| **Grand Total** | **₹1,522.50** |

*Note: Prices at 100+ unit volume. Prototype costs will be higher.*

## Assembly Instructions

See [docs/assembly/ASSEMBLY.md](../assembly/ASSEMBLY.md) for step-by-step instructions.

## Design Files

- `pcb/chessstream.kicad_pro` - KiCad project
- `pcb/chessstream.kicad_sch` - Schematic
- `pcb/chessstream.kicad_pcb` - PCB layout
- `enclosure/enclosure.step` - 3D CAD model
- `enclosure/laser_cut.dxf` - Laser cutting files

## References

- [ESP32 Datasheet](https://www.espressif.com/sites/default/files/documentation/esp32-wroom-32e_esp32-wroom-32ue_datasheet_en.pdf)
- [CD74HC4067 Datasheet](https://www.ti.com/lit/ds/symlink/cd74hc4067.pdf)
- [ChessTrace Hardware](https://github.com/anujjainbatu/chess-trace/tree/main/hardware)
