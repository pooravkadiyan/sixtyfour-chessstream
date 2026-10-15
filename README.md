# ChessStream India 🇮🇳♟️

**Low-cost electronic chess boards for tournament streaming in India**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Overview

ChessStream India is an open-source project to manufacture affordable electronic chess boards (<₹2,000) for live tournament streaming. We aim to democratize chess broadcasting in India by providing tournament organizers with a cost-effective alternative to expensive DGT boards (₹36,000+).

## Why This Project?

- **570+ FIDE-rated tournaments** happen in India every year
- **DGT boards cost ₹36,000+** — prohibitive for most organizers
- **DGT's core patent (US6168158B1) expired in 2013** — no legal barriers
- **Open-source designs exist** (ChessTrace, LiBoard) — we can build on them

## Target Specifications

| Spec | Target |
|------|--------|
| BOM Cost | <₹2,000 |
| Connectivity | WiFi (ESP32) |
| Sensing | Reed switches + magnets |
| Power | USB-C (5V) |
| Streaming | LiveChess-compatible / Lichess Board API |
| Piece Detection | Occupancy only (software infers moves) |

## Project Structure

```
├── hardware/           # PCB designs, schematics, enclosure CAD
│   ├── pcb/           # KiCad project files
│   ├── enclosure/     # 3D printable / laser-cut designs
│   └── bom/           # Bill of Materials
├── firmware/          # ESP32 firmware (Arduino/PlatformIO)
│   ├── src/           # Main source code
│   └── lib/           # Libraries
├── software/          # Desktop/web streaming software
│   ├── server/        # Local relay server
│   └── web/           # Web dashboard
├── docs/              # Documentation
│   ├── assembly/      # Assembly instructions
│   ├── api/           # API documentation
│   └── guides/        # User guides
└── RESEARCH_REPORT.md # Market research
```

## Hardware Design

### Sensing Technology: Reed Switches

We use **reed switches** (simplest, cheapest method):
- 64 reed switches (one per square)
- 32 neodymium magnets (one per piece)
- Binary detection: occupied/empty
- Software infers piece type from game state

### Core Components

| Component | Qty | Est. Cost |
|-----------|-----|-----------|
| ESP32-WROOM-32E | 1 | ₹125 |
| Reed switches (glass) | 64 | ₹270 |
| Neodymium magnets (10mm) | 32 | ₹135 |
| CD74HC4067 multiplexer | 4 | ₹100 |
| Custom PCB | 1 | ₹170 |
| MDF/Acrylic enclosure | 1 | ₹170 |
| Chess pieces (plastic) | 32 | ₹250 |
| USB-C connector | 1 | ₹30 |
| Passive components | lot | ₹50 |
| **Total** | | **~₹1,300** |

### Schematic Overview

```
                    ┌─────────────────┐
                    │     ESP32       │
                    │   (WiFi MCU)    │
                    └────────┬────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
    ┌────┴────┐        ┌────┴────┐        ┌────┴────┐
    │  MUX 1  │        │  MUX 2  │   ...  │  MUX 4  │
    │(16 ch)  │        │(16 ch)  │        │(16 ch)  │
    └────┬────┘        └────┬────┘        └────┬────┘
         │                   │                   │
    ┌────┴────┐        ┌────┴────┐        ┌────┴────┐
    │ Reed    │        │ Reed    │        │ Reed    │
    │Switches │        │Switches │        │Switches │
    │ (a1-h2) │        │ (a3-h4) │        │ (a7-h8) │
    └─────────┘        └─────────┘        └─────────┘
```

## Firmware

The ESP32 firmware:
1. Scans all 64 reed switches via multiplexers
2. Detects piece movements (lift/place events)
3. Maintains board state
4. Broadcasts moves via WebSocket/MQTT
5. Supports LiveChess protocol for compatibility

### Key Features
- **Debouncing**: Handles noisy reed switch signals
- **Move validation**: Basic chess rule validation
- **Offline buffer**: Stores moves if WiFi drops
- **OTA updates**: Over-the-air firmware updates

## Software

### Streaming Server
- Local relay server (Python/Node.js)
- Connects to multiple boards
- Broadcasts to Chess.com/Lichess/custom platforms
- PGN export and game archival

### Web Dashboard
- Real-time board visualization
- Tournament management
- Multi-board monitoring
- Player/game metadata entry

## Digital twin

The browser twin loads the enclosure and piece STL files and speaks the same WebSocket events as the ESP32 firmware (`lift`, `place`, `move` with UCI).

```bash
cd software/digital-twin
python -m http.server 8765
```

Open http://127.0.0.1:8765 and drag a piece. The 8×8 grid is the reed-matrix view (occupied or empty). Connect `ws://<board-ip>:81` to follow a real board, or `ws://127.0.0.1:8080/ws` to follow the Python relay.

KiCad, FreeCAD, Gerber, and LTspice sources are under `hardware/`. See `hardware/README.md`.

## Digital Twin

The browser twin loads the enclosure and piece STL files and speaks the same WebSocket events as the ESP32 firmware (`lift`, `place`, `move` with UCI).

```bash
cd software/digital-twin
python -m http.server 8765
```

Open http://127.0.0.1:8765 and drag a piece. The 8×8 grid is the reed-matrix view (occupied or empty). Connect `ws://<board-ip>:81` to follow a real board, or `ws://127.0.0.1:8080/ws` to follow the Python relay.

KiCad, FreeCAD, Gerber, and LTspice sources are under `hardware/`. See `hardware/README.md`.

## Getting Started

### Prerequisites
- ESP32 development board (for prototyping)
- Arduino IDE or PlatformIO
- Basic soldering equipment
- 3D printer or laser cutter (for enclosure)

### Quick Start

```bash
# Clone the repo
git clone https://github.com/monara-ventures/chessstream-india.git
cd chessstream-india

# Install PlatformIO (if not installed)
pip install platformio

# Build and upload firmware
cd firmware
pio run -t upload

# Start the streaming server
cd ../software/server
pip install -r requirements.txt
python server.py
```

## Roadmap

### Phase 1: Prototype (Current)
- [ ] Finalize PCB schematic
- [ ] Order prototype PCBs from JLCPCB
- [ ] Design 3D-printable enclosure
- [ ] Basic ESP32 firmware
- [ ] Simple WebSocket streaming

### Phase 2: Software
- [ ] LiveChess protocol implementation
- [ ] Lichess Board API integration
- [ ] Web dashboard MVP
- [ ] Multi-board support

### Phase 3: Production
- [ ] Optimize BOM for cost
- [ ] Design injection-molded enclosure
- [ ] Reliability testing
- [ ] Documentation

### Phase 4: Pilot
- [ ] Partner with TNSCA/MCA for pilot tournament
- [ ] Gather feedback
- [ ] Iterate on design

## Contributing

We welcome contributions! See [CONTRIBUTING.md](docs/CONTRIBUTING.md) for guidelines.

### Areas We Need Help
- **Hardware**: PCB design, enclosure design
- **Firmware**: ESP32 programming, protocol implementation
- **Software**: Web development, streaming integrations
- **Testing**: Tournament organizers willing to pilot

## References

- [ChessTrace](https://github.com/anujjainbatu/chess-trace) - Open-source ESP32 chess board
- [LiBoard](https://github.com/nicvagn/LiBoard) - Lichess-compatible board
- [DGT Patent (Expired)](https://patents.google.com/patent/US6168158B1/en)
- [Lichess Board API](https://lichess.org/api#tag/Board)

## License

This project is licensed under the MIT License - see [LICENSE](LICENSE) for details.

## Contact

**Monara Ventures**  
Poorav Kadiyan  
Email: poorav.pepi@gmail.com

---

*Made with ♟️ in India*
