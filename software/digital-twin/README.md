# ChessStream digital twin

Browser view of the mechanical model plus the firmware protocol.

```bash
python -m http.server 8765
```

Open http://127.0.0.1:8765

- Drag pieces. Illegal moves snap back. Castling, en passant, and queen promotion follow chess rules.
- The reed grid is the occupancy bitmap the ESP32 scans.
- **Connect** to `ws://<board>:81` (firmware, listen only) or `ws://127.0.0.1:8080/ws` (the Python relay). Local moves are published to the relay and ignored while a live socket is open.
- STL files in `models/` are copied from `hardware/enclosure/export/`.

Regenerate the meshes with `python hardware/tools/generate_design.py` from the repo root.
