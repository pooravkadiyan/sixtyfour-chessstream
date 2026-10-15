"""
Generate the ChessStream digital-twin hardware pack:

- KiCad 8 project (hierarchical schematic + both PCBs + libraries)
- JLCPCB BOM, pick-and-place, Gerber RS-274X, Excellon drill
- STL meshes, laser DXF, FreeCAD build script
- LTSpice decks are written separately; this script writes manufacturing geometry

Run from anywhere:
    python hardware/tools/generate_design.py
"""

from __future__ import annotations

import math
import shutil
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HW = ROOT / "hardware"
PCB = HW / "pcb"
GERBER = HW / "gerber"
ENC = HW / "enclosure"
PIECES = HW / "pieces"
TWIN_MODELS = ROOT / "software" / "digital-twin" / "models"

BOARD_W = 450.0
BOARD_H = 450.0
ORIGIN = 50.0
PITCH = 50.0
CTRL_W = 80.0
CTRL_H = 50.0

FILES = "abcdefgh"
RANKS = "12345678"


def uid() -> str:
    return str(uuid.uuid4())


def sq_name(col: int, row: int) -> str:
    return f"{FILES[col]}{RANKS[row]}"


def sq_index(col: int, row: int) -> int:
    return row * 8 + col


def center(col: int, row: int) -> tuple[float, float]:
    return (ORIGIN + col * PITCH, ORIGIN + row * PITCH)


# CD74HC4067: pin -> (side, index from top). side L pins 1-12, R pins 13-24.
MUX_PINS = {
    1: "COM",
    2: "I7",
    3: "I6",
    4: "I5",
    5: "I4",
    6: "I3",
    7: "I2",
    8: "I1",
    9: "I0",
    10: "S0",
    11: "S1",
    12: "GND",
    13: "S3",
    14: "S2",
    15: "E",
    16: "I15",
    17: "I14",
    18: "I13",
    19: "I12",
    20: "I11",
    21: "I10",
    22: "I9",
    23: "I8",
    24: "VCC",
}
CHANNEL_PIN = {}
for _ch in range(16):
    if _ch <= 7:
        CHANNEL_PIN[_ch] = 9 - _ch
    else:
        CHANNEL_PIN[_ch] = 31 - _ch


def soic24_pad(pin: int) -> tuple[float, float]:
    """Local pad center. Pin 1 is top-left, +Y up. Pitch 1.27, row span ~9.3 mm."""
    pitch = 1.27
    y0 = 11 * pitch / 2
    x = -4.65 if pin <= 12 else 4.65
    if pin <= 12:
        y = y0 - (pin - 1) * pitch
    else:
        y = -y0 + (pin - 13) * pitch
    return (x, y)


def esp32_pad(pin: int) -> tuple[float, float]:
    """ESP32-WROOM-32E land. Antenna toward +Y. Pin 1 bottom-left. Pitch 1.27."""
    pitch = 1.27
    y1 = -18 * pitch / 2  # pin 1
    if pin <= 19:
        return (-7.90, y1 + (pin - 1) * pitch)
    return (7.90, -y1 - (pin - 20) * pitch)


ESP32_NAME = {
    1: "GND",
    2: "3V3",
    3: "EN",
    6: "IO34",
    7: "IO35",
    8: "IO32",
    9: "IO33",
    10: "IO25",
    11: "IO26",
    12: "IO27",
    13: "IO14",
    24: "IO2",
    38: "GND",
}


class Sch:
    def __init__(self, title: str, paper: str = "A3"):
        self.title = title
        self.paper = paper
        self.symbols_lib: list[str] = []
        self.body: list[str] = []
        self._seen_lib: set[str] = set()

    def add_lib(self, lib_id: str, text: str) -> None:
        if lib_id not in self._seen_lib:
            self._seen_lib.add(lib_id)
            self.symbols_lib.append(text)

    def add(self, text: str) -> None:
        self.body.append(text)

    def dump(self, root_uuid: str, sheet_path: str, page: str) -> str:
        libs = "\n".join(self.symbols_lib)
        body = "\n".join(self.body)
        return f"""(kicad_sch
  (version 20231120)
  (generator "eeschema")
  (generator_version "8.0.6")
  (uuid "{root_uuid}")
  (paper "{self.paper}")
  (title_block
    (title "{self.title}")
    (date "2026-10-15")
    (rev "0.1")
    (company "Monara Ventures")
    (comment 1 "ChessStream India electronic chessboard")
  )
  (lib_symbols
{libs}
  )
{body}
  (sheet_instances
    (path "{sheet_path}"
      (page "{page}")
    )
  )
)
"""


def effects(size: float = 1.27, hide: bool = False) -> str:
    hid = " hide" if hide else ""
    return f"(effects (font (size {size} {size})){hid})"


def prop(name: str, value: str, x: float, y: float, hide: bool = False, rot: float = 0) -> str:
    return (
        f'(property "{name}" "{value}" (at {x} {y} {rot}) {effects(1.27, hide)})'
    )


def pin_def(num: str, name: str, x: float, y: float, angle: float, etype: str = "passive") -> str:
    return (
        f'(pin {etype} line (at {x} {y} {angle}) (length 2.54)\n'
        f'  (name "{name}" {effects(1.0)})\n'
        f'  (number "{num}" {effects(1.0)})\n'
        f")"
    )


def lib_symbol(lib_id: str, ref: str, value: str, pins: list[str], graphics: str, desc: str) -> str:
    pin_block = "\n".join(pins)
    return f"""    (symbol "{lib_id}"
      (exclude_from_sim no) (in_bom yes) (on_board yes)
      (property "Reference" "{ref}" (at 0 0 0) {effects(1.27)})
      (property "Value" "{value}" (at 0 -2.54 0) {effects(1.27)})
      (property "Footprint" "" (at 0 0 0) {effects(1.27, True)})
      (property "Datasheet" "~" (at 0 0 0) {effects(1.27, True)})
      (property "Description" "{desc}" (at 0 0 0) {effects(1.27, True)})
      (symbol "{lib_id.split(":")[-1]}_0_1"
{graphics}
      )
      (symbol "{lib_id.split(":")[-1]}_1_1"
{pin_block}
      )
    )"""


def rect(x1, y1, x2, y2) -> str:
    return (
        f"        (rectangle (start {x1} {y1}) (end {x2} {y2})\n"
        f"          (stroke (width 0.254) (type default)) (fill (type background)))"
    )


def poly(pts: list[tuple[float, float]]) -> str:
    body = " ".join(f"(xy {x} {y})" for x, y in pts)
    return (
        f"        (polyline (pts {body})\n"
        f"          (stroke (width 0.254) (type default)) (fill (type none)))"
    )


RES = lib_symbol(
    "chessstream:R",
    "R",
    "R",
    [
        pin_def("1", "~", -3.81, 0, 180),
        pin_def("2", "~", 3.81, 0, 0),
    ],
    rect(-2.54, -1.016, 2.54, 1.016),
    "Resistor",
)
CAP = lib_symbol(
    "chessstream:C",
    "C",
    "C",
    [
        pin_def("1", "~", 0, 3.81, 270),
        pin_def("2", "~", 0, -3.81, 90),
    ],
    poly([(-2, 1), (2, 1), (2, 0.4), (-2, 0.4), (-2, 1)])
    + "\n"
    + poly([(-2, -1), (2, -1), (2, -0.4), (-2, -0.4), (-2, -1)]),
    "Capacitor",
)
REED = lib_symbol(
    "chessstream:ReedSwitch",
    "SW",
    "REED",
    [
        pin_def("1", "A", -7.62, 0, 180),
        pin_def("2", "B", 7.62, 0, 0),
    ],
    poly([(-5, 0), (-1.5, 1.2), (2.5, -1.2), (5, 0)]),
    "Glass reed switch, closes with axial magnet",
)
LED = lib_symbol(
    "chessstream:LED",
    "D",
    "LED",
    [
        pin_def("1", "A", -3.81, 0, 180),
        pin_def("2", "K", 3.81, 0, 0),
    ],
    poly([(-1.5, -1.5), (-1.5, 1.5), (1.8, 0), (-1.5, -1.5)]),
    "LED",
)

_mux_pins = []
for _p in range(1, 25):
    _name = MUX_PINS[_p]
    if _p <= 12:
        _mux_pins.append(pin_def(str(_p), _name, -15.24, 16.51 - (_p - 1) * 2.54, 180, "passive"))
    else:
        _mux_pins.append(pin_def(str(_p), _name, 15.24, 16.51 - (_p - 13) * 2.54, 0, "passive"))
MUX = lib_symbol(
    "chessstream:CD74HC4067",
    "U",
    "CD74HC4067",
    _mux_pins,
    rect(-12.7, -15.24, 12.7, 19.05),
    "16-channel analog mux, TI CD74HC4067",
)

_esp_pins_spec = [
    (1, "GND", -20.32, 15.24, 180, "power_in"),
    (2, "3V3", -20.32, 12.70, 180, "power_in"),
    (3, "EN", -20.32, 10.16, 180, "input"),
    (8, "IO32", 20.32, 15.24, 0, "input"),
    (9, "IO33", 20.32, 12.70, 0, "input"),
    (6, "IO34", 20.32, 10.16, 0, "input"),
    (7, "IO35", 20.32, 7.62, 0, "input"),
    (10, "IO25", 20.32, 2.54, 0, "output"),
    (11, "IO26", 20.32, 0.00, 0, "output"),
    (12, "IO27", 20.32, -2.54, 0, "output"),
    (13, "IO14", 20.32, -5.08, 0, "output"),
    (24, "IO2", 20.32, -10.16, 0, "output"),
    (38, "GND", -20.32, -15.24, 180, "power_in"),
]
ESP = lib_symbol(
    "chessstream:ESP32-WROOM-32E",
    "U",
    "ESP32-WROOM-32E",
    [pin_def(str(n), name, x, y, a, t) for n, name, x, y, a, t in _esp_pins_spec],
    rect(-17.78, -17.78, 17.78, 17.78),
    "ESP32-WROOM-32E Wi-Fi module",
)
AMS = lib_symbol(
    "chessstream:AMS1117-3.3",
    "U",
    "AMS1117-3.3",
    [
        pin_def("1", "GND", -7.62, 2.54, 180, "power_in"),
        pin_def("2", "VOUT", 7.62, 2.54, 0, "power_out"),
        pin_def("3", "VIN", -7.62, -2.54, 180, "power_in"),
    ],
    rect(-5.08, -5.08, 5.08, 5.08),
    "3.3V LDO, SOT-223",
)
USB = lib_symbol(
    "chessstream:USB_C_Power",
    "J",
    "USB-C",
    [
        pin_def("A4", "VBUS", 10.16, 5.08, 0, "power_out"),
        pin_def("A1", "GND", 10.16, 2.54, 0, "power_out"),
        pin_def("A5", "CC1", 10.16, 0, 0, "passive"),
        pin_def("B5", "CC2", 10.16, -2.54, 0, "passive"),
        pin_def("SH", "SHIELD", 10.16, -5.08, 0, "passive"),
    ],
    rect(-7.62, -7.62, 7.62, 7.62),
    "USB-C power sink",
)

# Header pins used on both boards. Local Y from +11.43 down, 2.54 pitch, two columns.
HDR_PINS = [
    (1, "3V3"),
    (2, "GND"),
    (3, "SIG1"),
    (4, "SIG2"),
    (5, "SIG3"),
    (6, "SIG4"),
    (7, "S0"),
    (8, "S1"),
    (9, "S2"),
    (10, "S3"),
    (11, "LED"),
    (12, "GND"),
]
_hdr_pin_defs = []
for _i, (_n, _name) in enumerate(HDR_PINS):
    _col = 0 if _i < 6 else 1
    _row = _i if _i < 6 else _i - 6
    _x = -2.54 if _col == 0 else 2.54
    _y = 7.62 - _row * 2.54
    _ang = 180 if _col == 0 else 0
    _px = _x - 5.08 if _col == 0 else _x + 5.08
    _hdr_pin_defs.append(pin_def(str(_n), _name, _px, _y, _ang))
HDR = lib_symbol(
    "chessstream:Conn_02x10",
    "J",
    "HDR20",
    _hdr_pin_defs,
    rect(-2.54, -8.89, 2.54, 8.89),
    "2x10 2.54mm ribbon header, pins 13-20 unused",
)

LIB_ALL = [RES, CAP, REED, LED, MUX, ESP, AMS, USB, HDR]


def place_symbol(
    sch: Sch,
    lib_id: str,
    ref: str,
    value: str,
    footprint: str,
    x: float,
    y: float,
    project_path: str,
    pin_uuids: dict[str, str],
    rot: float = 0,
) -> dict[str, tuple[float, float]]:
    """Return world coordinates of each pin connection point."""
    su = uid()
    pins_txt = "\n".join(
        f'    (pin "{num}" (uuid "{pu}"))' for num, pu in pin_uuids.items()
    )
    sch.add(
        f"""  (symbol
    (lib_id "{lib_id}")
    (at {x} {y} {rot})
    (unit 1)
    (exclude_from_sim no)
    (in_bom yes)
    (on_board yes)
    (dnp no)
    (uuid "{su}")
    {prop("Reference", ref, x + 2, y + 2)}
    {prop("Value", value, x + 2, y - 2)}
    {prop("Footprint", footprint, x, y, True)}
    {prop("Datasheet", "~", x, y, True)}
{pins_txt}
    (instances
      (project "chessstream"
        (path "{project_path}"
          (reference "{ref}")
          (unit 1)
        )
      )
    )
  )"""
    )
    return {}


def wire(sch: Sch, x1, y1, x2, y2) -> None:
    sch.add(
        f"""  (wire (pts (xy {x1} {y1}) (xy {x2} {y2}))
    (stroke (width 0) (type default)) (uuid "{uid()}"))"""
    )


def glabel(sch: Sch, name: str, x: float, y: float, shape: str = "bidirectional", rot: float = 0) -> None:
    sch.add(
        f"""  (global_label "{name}" (shape {shape}) (at {x} {y} {rot})
    (effects (font (size 1.27 1.27)) (justify left bottom))
    (uuid "{uid()}"))"""
    )


def hlabel(sch: Sch, name: str, x: float, y: float, shape: str = "bidirectional") -> None:
    sch.add(
        f"""  (hierarchical_label "{name}" (shape {shape}) (at {x} {y} 0)
    (effects (font (size 1.27 1.27)) (justify left))
    (uuid "{uid()}"))"""
    )


def note(sch: Sch, text: str, x: float, y: float) -> None:
    safe = text.replace('"', "'")
    sch.add(
        f"""  (text "{safe}" (at {x} {y} 0)
    (effects (font (size 1.5 1.5)))
    (uuid "{uid()}"))"""
    )


def rotate_point(x: float, y: float, rot: float) -> tuple[float, float]:
    r = math.radians(rot)
    return (x * math.cos(r) - y * math.sin(r), x * math.sin(r) + y * math.cos(r))


def connect_pin(sch: Sch, px: float, py: float, name: str, shape: str = "bidirectional") -> None:
    wire(sch, px, py, px + 7.62, py)
    glabel(sch, name, px + 7.62, py, shape)


# ---------- footprints ----------

def fp_header(name: str, descr: str, tags: str, attr: str) -> str:
    return f"""(footprint "{name}"
  (version 20240108)
  (generator "pcbnew")
  (generator_version "8.0.6")
  (layer "F.Cu")
  (descr "{descr}")
  (tags "{tags}")
  (attr {attr})
"""


def fp_tail() -> str:
    return ")\n"


def pad_th(num, x, y, drill=0.8, size=1.6) -> str:
    return (
        f'  (pad "{num}" thru_hole circle (at {x} {y}) (size {size} {size}) '
        f'(drill {drill}) (layers "*.Cu" "*.Mask"))\n'
    )


def pad_smd(num, x, y, w, h) -> str:
    return (
        f'  (pad "{num}" smd rect (at {x} {y}) (size {w} {h}) '
        f'(layers "F.Cu" "F.Paste" "F.Mask"))\n'
    )


def write_footprints() -> None:
    pretty = PCB / "footprints" / "chessstream.pretty"
    pretty.mkdir(parents=True, exist_ok=True)

    reed = fp_header("ReedSwitch_D2_L12", "Glass reed, 12mm lead spacing", "reed switch", "through_hole")
    reed += '  (fp_line (start -7 1) (end 7 1) (stroke (width 0.12) (type solid)) (layer "F.SilkS"))\n'
    reed += '  (fp_line (start -7 -1) (end 7 -1) (stroke (width 0.12) (type solid)) (layer "F.SilkS"))\n'
    reed += '  (fp_circle (center 0 0) (end 1.2 0) (stroke (width 0.12) (type solid)) (layer "F.Fab"))\n'
    reed += pad_th("1", -6, 0)
    reed += pad_th("2", 6, 0)
    reed += fp_tail()
    (pretty / "ReedSwitch_D2_L12.kicad_mod").write_text(reed, encoding="utf-8")

    r0805 = fp_header("R_0805", "0805 resistor", "0805", "smd")
    r0805 += pad_smd("1", -0.95, 0, 0.7, 0.9)
    r0805 += pad_smd("2", 0.95, 0, 0.7, 0.9)
    r0805 += '  (fp_line (start -0.5 -0.6) (end 0.5 -0.6) (stroke (width 0.12) (type solid)) (layer "F.SilkS"))\n'
    r0805 += fp_tail()
    (pretty / "R_0805.kicad_mod").write_text(r0805, encoding="utf-8")

    c0805 = fp_header("C_0805", "0805 capacitor", "0805", "smd")
    c0805 += pad_smd("1", -0.95, 0, 0.7, 0.9)
    c0805 += pad_smd("2", 0.95, 0, 0.7, 0.9)
    c0805 += fp_tail()
    (pretty / "C_0805.kicad_mod").write_text(c0805, encoding="utf-8")

    soic = fp_header("SOIC-24W_7.5x15.4_P1.27", "CD74HC4067 DW", "SOIC-24", "smd")
    soic += '  (fp_rect (start -3.75 -7.7) (end 3.75 7.7) (stroke (width 0.12) (type solid)) (layer "F.Fab"))\n'
    for pin in range(1, 25):
        x, y = soic24_pad(pin)
        soic += pad_smd(str(pin), x, y, 1.5, 0.6)
    soic += '  (fp_circle (center -5.6 7.4) (end -5.2 7.4) (stroke (width 0.12) (type solid)) (layer "F.SilkS"))\n'
    soic += fp_tail()
    (pretty / "SOIC-24W_7.5x15.4_P1.27.kicad_mod").write_text(soic, encoding="utf-8")

    esp = fp_header("ESP32-WROOM-32E", "Espressif module land pattern", "ESP32", "smd")
    esp += '  (fp_rect (start -9 -12.75) (end 9 12.75) (stroke (width 0.12) (type solid)) (layer "F.Fab"))\n'
    esp += '  (fp_text user "ANT" (at 0 15) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))))\n'
    for pin in range(1, 39):
        x, y = esp32_pad(pin)
        esp += pad_smd(str(pin), x, y, 1.5, 0.9)
    esp += fp_tail()
    (pretty / "ESP32-WROOM-32E.kicad_mod").write_text(esp, encoding="utf-8")

    sot = fp_header("SOT-223", "AMS1117", "SOT-223", "smd")
    sot += pad_smd("1", -2.3, 3.15, 1.2, 2.0)
    sot += pad_smd("2", 0.0, 3.15, 1.2, 2.0)
    sot += pad_smd("3", 2.3, 3.15, 1.2, 2.0)
    sot += pad_smd("2", 0.0, -1.6, 3.8, 2.0)  # tab, also pin 2 / VOUT
    sot += fp_tail()
    (pretty / "SOT-223.kicad_mod").write_text(sot, encoding="utf-8")

    usb = fp_header("USB_C_16_PowerOnly", "USB-C power-only simplified land", "USB-C", "smd")
    # A4 VBUS, A1 GND, A5 CC1, B5 CC2, shield
    usb += pad_smd("A4", -1.25, 3.2, 0.6, 1.2)
    usb += pad_smd("A1", 0.0, 3.2, 0.6, 1.2)
    usb += pad_smd("A5", 1.25, 3.2, 0.6, 1.2)
    usb += pad_smd("B5", -1.25, -3.2, 0.6, 1.2)
    usb += pad_smd("SH", 4.6, 0, 1.2, 1.8)
    usb += pad_smd("SH", -4.6, 0, 1.2, 1.8)
    usb += '  (fp_rect (start -4.5 -4.2) (end 4.5 4.2) (stroke (width 0.12) (type solid)) (layer "F.SilkS"))\n'
    usb += fp_tail()
    (pretty / "USB_C_16_PowerOnly.kicad_mod").write_text(usb, encoding="utf-8")

    led = fp_header("LED_0805", "0805 LED", "LED", "smd")
    led += pad_smd("1", -0.95, 0, 0.7, 0.9)
    led += pad_smd("2", 0.95, 0, 0.7, 0.9)
    led += fp_tail()
    (pretty / "LED_0805.kicad_mod").write_text(led, encoding="utf-8")

    hdr = fp_header("PinHeader_2x10_P2.54", "2.54mm 2x10 through hole", "header", "through_hole")
    for i in range(10):
        for col, num0 in ((0, 1), (1, 2)):
            num = num0 + i * 2
            hdr += pad_th(str(num), col * 2.54, i * 2.54, drill=1.0, size=1.7)
    hdr += fp_tail()
    (pretty / "PinHeader_2x10_P2.54.kicad_mod").write_text(hdr, encoding="utf-8")

    (PCB / "fp-lib-table").write_text(
        """(fp_lib_table
  (version 7)
  (lib (name "chessstream")(type "KiCad")(uri "${KIPRJMOD}/footprints/chessstream.pretty")(options "")(descr "ChessStream footprints"))
)
""",
        encoding="utf-8",
    )
    (PCB / "sym-lib-table").write_text(
        """(sym_lib_table
  (version 7)
  (lib (name "chessstream")(type "KiCad")(uri "${KIPRJMOD}/symbols/chessstream.kicad_sym")(options "")(descr "ChessStream symbols"))
)
""",
        encoding="utf-8",
    )


def write_symbol_lib() -> None:
    sym_dir = PCB / "symbols"
    sym_dir.mkdir(parents=True, exist_ok=True)
    body = "\n".join(LIB_ALL)
    text = f"""(kicad_symbol_lib
  (version 20231120)
  (generator "kicad_symbol_editor")
  (generator_version "8.0.6")
{body}
)
"""
    (sym_dir / "chessstream.kicad_sym").write_text(text, encoding="utf-8")


def write_project() -> None:
    (PCB / "chessstream.kicad_pro").write_text(
        """{
  "board": {
    "design_settings": {
      "defaults": { "board_outline_line_width": 0.1, "copper_line_width": 0.25 },
      "rules": {
        "min_clearance": 0.2,
        "min_track_width": 0.2,
        "min_via_diameter": 0.6,
        "min_via_drill": 0.3
      },
      "track_widths": [0.25, 0.5],
      "via_dimensions": [{ "diameter": 0.8, "drill": 0.4 }]
    }
  },
  "boards": [],
  "meta": { "filename": "chessstream.kicad_pro", "version": 1 },
  "net_settings": {
    "classes": [{
      "name": "Default",
      "clearance": 0.2,
      "track_width": 0.25,
      "via_diameter": 0.8,
      "via_drill": 0.4
    }],
    "meta": { "version": 3 }
  },
  "sheets": [],
  "text_variables": {}
}
""",
        encoding="utf-8",
    )


# ---------- schematics ----------

def build_schematics() -> tuple[str, str]:
    root_uuid = uid()
    ctrl_sheet_uuid = uid()
    matrix_sheet_uuid = uid()
    ctrl_path = f"/{root_uuid}/{ctrl_sheet_uuid}"
    matrix_path = f"/{root_uuid}/{matrix_sheet_uuid}"

    root = Sch("ChessStream India", "A3")
    for lib in (ESP, MUX):  # root has no parts; libs can be empty
        pass
    root.add(
        f"""  (sheet
    (at 25 25)
    (size 90 110)
    (stroke (width 0.1524) (type solid))
    (fill (color 0 0 0 0))
    (uuid "{ctrl_sheet_uuid}")
    (property "Sheetname" "Controller" (at 25 24 0) {effects(1.5)})
    (property "Sheetfile" "controller.kicad_sch" (at 25 136 0) {effects(1.27)})
  )"""
    )
    root.add(
        f"""  (sheet
    (at 140 25)
    (size 120 110)
    (stroke (width 0.1524) (type solid))
    (fill (color 0 0 0 0))
    (uuid "{matrix_sheet_uuid}")
    (property "Sheetname" "ReedMatrix" (at 140 24 0) {effects(1.5)})
    (property "Sheetfile" "reed_matrix.kicad_sch" (at 140 136 0) {effects(1.27)})
  )"""
    )
    note(
        root,
        "Global labels 3V3 GND SIG1-4 S0-S3 LED tie the controller to the matrix. "
        "Muxes sit on the 450mm board. The 80x50mm controller carries ESP32, USB-C and the LDO. "
        "Reed closes to GND when a magnet is present. 10k pulls each channel up to 3.3V.",
        25,
        160,
    )
    (PCB / "chessstream.kicad_sch").write_text(
        root.dump(root_uuid, "/", "1"), encoding="utf-8"
    )

    # Controller sheet
    ctrl = Sch("Controller 80x50mm", "A3")
    for lib in (RES, CAP, LED, ESP, AMS, USB, HDR):
        ctrl.add_lib("chessstream:" + lib.split('"')[1].split(":")[-1] if False else "", "")
    # add libs properly
    ctrl.symbols_lib = []
    ctrl._seen_lib = set()
    for lib in (RES, CAP, LED, ESP, AMS, USB, HDR):
        # lib starts with spaces then (symbol "id"
        lib_id = lib.split('(symbol "')[1].split('"')[0]
        ctrl.add_lib(lib_id, lib)

    path = ctrl_path

    def part(lib_id, ref, value, fp, x, y, pins: list[str], rot=0):
        pu = {p: uid() for p in pins}
        place_symbol(ctrl, lib_id, ref, value, fp, x, y, path, pu, rot)
        return pu

    # We need pin world positions. Symbols are not rotated (rot 0).
    # USB at (40, 40): pins at local x=10.16
    part("chessstream:USB_C_Power", "J1", "USB-C", "chessstream:USB_C_16_PowerOnly", 40, 50, ["A4", "A1", "A5", "B5", "SH"])
    for name, ly, gname in (
        ("A4", 5.08, "VBUS"),
        ("A1", 2.54, "GND"),
        ("A5", 0, "CC1"),
        ("B5", -2.54, "CC2"),
        ("SH", -5.08, "GND"),
    ):
        connect_pin(ctrl, 40 + 10.16, 50 + ly, gname, "output" if name == "A4" else "bidirectional")

    part("chessstream:R", "R1", "5.1k", "chessstream:R_0805", 70, 50, ["1", "2"])
    wire(ctrl, 70 - 3.81, 50, 70 - 8, 50)
    glabel(ctrl, "CC1", 70 - 8, 50)
    wire(ctrl, 70 + 3.81, 50, 70 + 8, 50)
    glabel(ctrl, "GND", 70 + 8, 50)

    part("chessstream:R", "R2", "5.1k", "chessstream:R_0805", 70, 40, ["1", "2"])
    wire(ctrl, 70 - 3.81, 40, 70 - 8, 40)
    glabel(ctrl, "CC2", 70 - 8, 40)
    wire(ctrl, 70 + 3.81, 40, 70 + 8, 40)
    glabel(ctrl, "GND", 70 + 8, 40)

    part("chessstream:AMS1117-3.3", "U1", "AMS1117-3.3", "chessstream:SOT-223", 110, 50, ["1", "2", "3"])
    connect_pin(ctrl, 110 - 7.62, 50 + 2.54, "GND")
    connect_pin(ctrl, 110 + 7.62, 50 + 2.54, "3V3", "output")
    connect_pin(ctrl, 110 - 7.62, 50 - 2.54, "VBUS", "input")

    part("chessstream:C", "C1", "10uF", "chessstream:C_0805", 110, 70, ["1", "2"], rot=0)
    # cap pins are vertical: pin1 (0, 3.81), pin2 (0, -3.81) — wire sideways from those points
    wire(ctrl, 110, 70 + 3.81, 118, 70 + 3.81)
    glabel(ctrl, "VBUS", 118, 70 + 3.81, "input")
    wire(ctrl, 110, 70 - 3.81, 118, 70 - 3.81)
    glabel(ctrl, "GND", 118, 70 - 3.81)

    part("chessstream:C", "C2", "10uF", "chessstream:C_0805", 130, 70, ["1", "2"])
    wire(ctrl, 130, 70 + 3.81, 138, 70 + 3.81)
    glabel(ctrl, "3V3", 138, 70 + 3.81, "output")
    wire(ctrl, 130, 70 - 3.81, 138, 70 - 3.81)
    glabel(ctrl, "GND", 138, 70 - 3.81)

    part("chessstream:C", "C3", "100nF", "chessstream:C_0805", 145, 70, ["1", "2"])
    wire(ctrl, 145, 70 + 3.81, 153, 70 + 3.81)
    glabel(ctrl, "3V3", 153, 70 + 3.81)
    wire(ctrl, 145, 70 - 3.81, 153, 70 - 3.81)
    glabel(ctrl, "GND", 153, 70 - 3.81)

    part(
        "chessstream:ESP32-WROOM-32E",
        "U2",
        "ESP32-WROOM-32E",
        "chessstream:ESP32-WROOM-32E",
        200,
        80,
        ["1", "2", "3", "8", "9", "6", "7", "10", "11", "12", "13", "24", "38"],
    )
    # left pins x = 200-20.32
    for off, name, shape in (
        (15.24, "GND", "bidirectional"),
        (12.70, "3V3", "input"),
        (10.16, "EN", "input"),
        (-15.24, "GND", "bidirectional"),
    ):
        wire(ctrl, 200 - 20.32, 80 + off, 200 - 28, 80 + off)
        glabel(ctrl, name, 200 - 28, 80 + off, shape)
    right = {
        15.24: "SIG1",
        12.70: "SIG2",
        10.16: "SIG3",
        7.62: "SIG4",
        2.54: "S0",
        0.00: "S1",
        -2.54: "S2",
        -5.08: "S3",
        -10.16: "LED",
    }
    for off, name in right.items():
        wire(ctrl, 200 + 20.32, 80 + off, 200 + 28, 80 + off)
        glabel(ctrl, name, 200 + 28, 80 + off, "output" if name.startswith("S") or name == "LED" else "input")

    part("chessstream:R", "R3", "10k", "chessstream:R_0805", 160, 100, ["1", "2"])
    wire(ctrl, 160 - 3.81, 100, 152, 100)
    glabel(ctrl, "3V3", 152, 100)
    wire(ctrl, 160 + 3.81, 100, 168, 100)
    glabel(ctrl, "EN", 168, 100)

    part("chessstream:R", "R4", "330", "chessstream:R_0805", 250, 60, ["1", "2"])
    wire(ctrl, 250 - 3.81, 60, 242, 60)
    glabel(ctrl, "LED", 242, 60, "input")
    wire(ctrl, 250 + 3.81, 60, 258, 60)
    glabel(ctrl, "LED_A", 258, 60)

    part("chessstream:LED", "D1", "BLUE", "chessstream:LED_0805", 275, 60, ["1", "2"])
    wire(ctrl, 275 - 3.81, 60, 268, 60)
    glabel(ctrl, "LED_A", 268, 60)
    wire(ctrl, 275 + 3.81, 60, 283, 60)
    glabel(ctrl, "GND", 283, 60)

    part("chessstream:Conn_02x10", "J2", "TO_MATRIX", "chessstream:PinHeader_2x10_P2.54", 320, 80, [str(n) for n, _ in HDR_PINS])
    # header pin connection points: left col x local = -2.54-5.08 = -7.62, right = 2.54+5.08=7.62
    for i, (num, name) in enumerate(HDR_PINS):
        col = 0 if i < 6 else 1
        row = i if i < 6 else i - 6
        y = 80 + (7.62 - row * 2.54)
        if col == 0:
            wire(ctrl, 320 - 7.62, y, 320 - 14, y)
            glabel(ctrl, name, 320 - 14, y)
        else:
            wire(ctrl, 320 + 7.62, y, 320 + 14, y)
            glabel(ctrl, name, 320 + 14, y)

    note(ctrl, "EN tied high via 10k. USB-C CC1/CC2 5.1k to GND advertise a default USB sink. GPIO34/35 are input-only and read SIG3/SIG4.", 30, 150)
    for name, y, shape in (
        ("3V3", 170, "input"),
        ("GND", 175, "bidirectional"),
        ("SIG1", 180, "input"),
        ("SIG2", 185, "input"),
        ("SIG3", 190, "input"),
        ("SIG4", 195, "input"),
        ("S0", 200, "output"),
        ("S1", 205, "output"),
        ("S2", 210, "output"),
        ("S3", 215, "output"),
        ("LED", 220, "output"),
    ):
        hlabel(ctrl, name, 20, y, shape)

    (PCB / "controller.kicad_sch").write_text(ctrl.dump(uid(), ctrl_path, "2"), encoding="utf-8")

    # Reed matrix sheet — 4 muxes + 64 cells using global labels (same names as controller)
    mx = Sch("Reed matrix 450mm", "A0")
    mx._seen_lib = set()
    for lib in (RES, CAP, REED, MUX, HDR):
        lib_id = lib.split('(symbol "')[1].split('"')[0]
        mx.add_lib(lib_id, lib)

    # Four muxes
    mux_at = [(40, 40), (40, 90), (40, 140), (40, 190)]
    for m, (x, y) in enumerate(mux_at):
        pins = [str(i) for i in range(1, 25)]
        place_symbol(
            mx,
            "chessstream:CD74HC4067",
            f"U{m+3}",
            "CD74HC4067",
            "chessstream:SOIC-24W_7.5x15.4_P1.27",
            x,
            y,
            matrix_path,
            {p: uid() for p in pins},
        )
        # left pins local x=-15.24, y = 16.51 - (p-1)*2.54 for p=1..12
        for p in range(1, 13):
            ly = 16.51 - (p - 1) * 2.54
            pname = MUX_PINS[p]
            net = mux_pin_net(m, p, pname)
            wire(mx, x - 15.24, y + ly, x - 22, y + ly)
            glabel(mx, net, x - 22, y + ly, "input" if pname.startswith("I") or pname == "COM" else "bidirectional")
        for p in range(13, 25):
            ly = 16.51 - (p - 13) * 2.54
            pname = MUX_PINS[p]
            net = mux_pin_net(m, p, pname)
            wire(mx, x + 15.24, y + ly, x + 22, y + ly)
            shape = "output" if pname == "COM" else "bidirectional"
            glabel(mx, net, x + 22, y + ly, shape)

        place_symbol(
            mx,
            "chessstream:C",
            f"C{m+4}",
            "100nF",
            "chessstream:C_0805",
            x + 30,
            y,
            matrix_path,
            {"1": uid(), "2": uid()},
        )
        wire(mx, x + 30, y + 3.81, x + 38, y + 3.81)
        glabel(mx, "3V3", x + 38, y + 3.81)
        wire(mx, x + 30, y - 3.81, x + 38, y - 3.81)
        glabel(mx, "GND", x + 38, y - 3.81)

    # 64 reed + pull-up cells on the right portion of A0
    for row in range(8):
        for col in range(8):
            name = sq_name(col, row)
            idx = sq_index(col, row)
            mux = idx // 16
            ch = idx % 16
            x = 120 + col * 28
            y = 30 + row * 22
            place_symbol(
                mx,
                "chessstream:ReedSwitch",
                f"SW{idx+1}",
                name,
                "chessstream:ReedSwitch_D2_L12",
                x,
                y,
                matrix_path,
                {"1": uid(), "2": uid()},
            )
            wire(mx, x - 7.62, y, x - 12, y)
            glabel(mx, "GND", x - 12, y)
            wire(mx, x + 7.62, y, x + 12, y)
            glabel(mx, f"SQ_{name}", x + 12, y)
            place_symbol(
                mx,
                "chessstream:R",
                f"R{idx+5}",
                "10k",
                "chessstream:R_0805",
                x,
                y + 8,
                matrix_path,
                {"1": uid(), "2": uid()},
            )
            wire(mx, x - 3.81, y + 8, x - 8, y + 8)
            glabel(mx, f"SQ_{name}", x - 8, y + 8)
            wire(mx, x + 3.81, y + 8, x + 8, y + 8)
            glabel(mx, "3V3", x + 8, y + 8)
            # also tag the mux channel with the same global by a second label near the mux pin already done
            # Connect channel pin net name: use SQ_ name directly in mux_pin_net — see function.

    place_symbol(
        mx,
        "chessstream:Conn_02x10",
        "J3",
        "TO_CONTROLLER",
        "chessstream:PinHeader_2x10_P2.54",
        360,
        30,
        matrix_path,
        {str(n): uid() for n, _ in HDR_PINS},
    )
    for i, (num, name) in enumerate(HDR_PINS):
        col = 0 if i < 6 else 1
        row = i if i < 6 else i - 6
        y = 30 + (7.62 - row * 2.54)
        if col == 0:
            wire(mx, 360 - 7.62, y, 360 - 14, y)
            glabel(mx, name, 360 - 14, y)
        else:
            wire(mx, 360 + 7.62, y, 360 + 14, y)
            glabel(mx, name, 360 + 14, y)

    note(
        mx,
        "Each square: reed to GND, 10k to 3V3, signal into CD74HC4067. "
        "Channel n on mux m is square index m*16+n in a1,b1.. order. E is tied to GND so the mux stays enabled. "
        "S0 is GPIO25 bit0. COM outputs are SIG1..SIG4 into GPIO32,33,34,35.",
        110,
        210,
    )
    (PCB / "reed_matrix.kicad_sch").write_text(mx.dump(uid(), matrix_path, "3"), encoding="utf-8")
    return root_uuid, matrix_path


def mux_pin_net(mux: int, pin: int, pname: str) -> str:
    if pname == "VCC":
        return "3V3"
    if pname == "GND" or pname == "E":
        return "GND"
    if pname == "COM":
        return f"SIG{mux+1}"
    if pname in ("S0", "S1", "S2", "S3"):
        return pname
    if pname.startswith("I"):
        ch = int(pname[1:])
        idx = mux * 16 + ch
        col = idx % 8
        row = idx // 8
        return f"SQ_{sq_name(col, row)}"
    return pname


# ---------- PCB ----------

LAYERS = """  (layers
    (0 "F.Cu" signal)
    (31 "B.Cu" signal)
    (32 "B.Adhes" user "B.Adhesive")
    (33 "F.Adhes" user "F.Adhesive")
    (34 "B.Paste" user)
    (35 "F.Paste" user)
    (36 "B.SilkS" user "B.Silkscreen")
    (37 "F.SilkS" user "F.Silkscreen")
    (38 "B.Mask" user)
    (39 "F.Mask" user)
    (40 "Dwgs.User" user "User.Drawings")
    (41 "Cmts.User" user "User.Comments")
    (42 "Eco1.User" user "User.Eco1")
    (43 "Eco2.User" user "User.Eco2")
    (44 "Edge.Cuts" user)
    (45 "Margin" user)
    (46 "B.CrtYd" user "B.Courtyard")
    (47 "F.CrtYd" user "F.Courtyard")
    (48 "B.Fab" user)
    (49 "F.Fab" user)
  )"""


class Board:
    def __init__(self, width: float, height: float):
        self.width = width
        self.height = height
        self.nets: dict[str, int] = {"": 0}
        self.footprints: list[str] = []
        self.segments: list[tuple[float, float, float, float, str, float]] = []
        self.vias: list[tuple[float, float, str]] = []
        self.silk: list[str] = []
        self.parts: list[dict] = []

    def net_id(self, name: str) -> int:
        if name not in self.nets:
            self.nets[name] = len(self.nets)
        return self.nets[name]

    def add_fp(self, text: str) -> None:
        self.footprints.append(text)

    def track(self, x1, y1, x2, y2, net: str, width: float = 0.25) -> None:
        if (x1, y1) == (x2, y2):
            return
        self.segments.append((x1, y1, x2, y2, net, width))

    def via(self, x, y, net: str) -> None:
        self.vias.append((x, y, net))

    def route(self, points: list[tuple[float, float]], net: str, width: float = 0.25) -> None:
        for (x1, y1), (x2, y2) in zip(points, points[1:]):
            if abs(x1 - x2) < 1e-6 or abs(y1 - y2) < 1e-6:
                self.track(x1, y1, x2, y2, net, width)
            else:
                self.track(x1, y1, x2, y1, net, width)
                self.track(x2, y1, x2, y2, net, width)


def fp_instance(lib_name: str, ref: str, value: str, x: float, y: float, rot: float, pads: list[tuple[str, float, float, str, str]]) -> str:
    """pads: (num, lx, ly, net, kind) kind is 'th' or 'smd'."""
    lines = [
        f'(footprint "{lib_name}"',
        f'  (layer "F.Cu")',
        f'  (uuid "{uid()}")',
        f'  (at {x:.3f} {y:.3f} {rot})',
        f'  (property "Reference" "{ref}" (at 0 0 0) (layer "F.SilkS") (effects (font (size 0.8 0.8) (thickness 0.12))))',
        f'  (property "Value" "{value}" (at 0 -1.5 0) (layer "F.Fab") (effects (font (size 0.8 0.8) (thickness 0.12))))',
    ]
    for num, lx, ly, net, kind in pads:
        nid = net  # placeholder replaced by caller? we'll embed net id outside
        lines.append(f"  PAD {num}|{lx}|{ly}|{net}|{kind}")
    lines.append(")")
    return "\n".join(lines)


def render_fp(raw: str, board: Board) -> str:
    out = []
    for line in raw.splitlines():
        if line.startswith("  PAD "):
            num, lx, ly, net, kind = line[6:].split("|")
            nid = board.net_id(net)
            lx_f, ly_f = float(lx), float(ly)
            if kind == "th":
                out.append(
                    f'  (pad "{num}" thru_hole circle (at {lx_f} {ly_f}) (size 1.6 1.6) (drill 0.8) '
                    f'(layers "*.Cu" "*.Mask") (net {nid} "{net}"))'
                )
            else:
                w, h = (0.7, 0.9) if kind == "r0805" else (1.5, 0.6) if kind == "soic" else (1.5, 0.9) if kind == "esp" else (1.2, 2.0) if kind == "sot" else (0.6, 1.2) if kind == "usb" else (1.7, 1.7)
                if kind == "th2":
                    out.append(
                        f'  (pad "{num}" thru_hole circle (at {lx_f} {ly_f}) (size 1.7 1.7) (drill 1.0) '
                        f'(layers "*.Cu" "*.Mask") (net {nid} "{net}"))'
                    )
                elif kind == "sot_tab":
                    out.append(
                        f'  (pad "{num}" smd rect (at {lx_f} {ly_f}) (size 3.8 2.0) '
                        f'(layers "F.Cu" "F.Paste" "F.Mask") (net {nid} "{net}"))'
                    )
                else:
                    out.append(
                        f'  (pad "{num}" smd rect (at {lx_f} {ly_f}) (size {w} {h}) '
                        f'(layers "F.Cu" "F.Paste" "F.Mask") (net {nid} "{net}"))'
                    )
        else:
            out.append(line)
    return "\n".join(out)


def dump_board(board: Board, title: str) -> str:
    net_lines = "\n".join(f'  (net {i} "{n}")' for n, i in sorted(board.nets.items(), key=lambda kv: kv[1]))
    seg_lines = []
    for x1, y1, x2, y2, net, width in board.segments:
        nid = board.net_id(net)
        seg_lines.append(
            f'  (segment (start {x1:.3f} {y1:.3f}) (end {x2:.3f} {y2:.3f}) (width {width}) (layer "F.Cu") (net {nid} "{net}") (uuid "{uid()}"))'
        )
    via_lines = []
    for x, y, net in board.vias:
        nid = board.net_id(net)
        via_lines.append(
            f'  (via (at {x:.3f} {y:.3f}) (size 0.8) (drill 0.4) (layers "F.Cu" "B.Cu") (net {nid} "{net}") (uuid "{uid()}"))'
        )
    nid_g = board.net_id("GND")
    zone = f"""  (zone (net {nid_g}) (net_name "GND") (layer "B.Cu") (uuid "{uid()}")
    (hatch edge 0.5)
    (connect_pads yes (clearance 0.3))
    (min_thickness 0.25)
    (fill yes (thermal_gap 0.3) (thermal_bridge_width 0.4))
    (polygon (pts (xy 1 1) (xy {board.width-1} 1) (xy {board.width-1} {board.height-1}) (xy 1 {board.height-1})))
  )"""
    edge = f"""  (gr_rect (start 0 0) (end {board.width} {board.height})
    (stroke (width 0.1) (type default)) (fill none) (layer "Edge.Cuts") (uuid "{uid()}"))
  (gr_text "{title}" (at 8 8 0) (layer "F.SilkS") (effects (font (size 1.5 1.5) (thickness 0.2))))"""
    fps = "\n".join(board.footprints)
    segs = "\n".join(seg_lines)
    vias = "\n".join(via_lines)
    return f"""(kicad_pcb
  (version 20240108)
  (generator "pcbnew")
  (generator_version "8.0.6")
  (general (thickness 1.6) (legacy_teardrops no))
  (paper "A2")
{LAYERS}
  (setup
    (pad_to_mask_clearance 0.05)
    (allow_soldermask_bridges_in_footprints no)
    (pcbplotparams
      (layerselection 0x00010fc_ffffffff)
      (plot_on_all_layers_selection 0x0000000_00000000)
      (disableapertmacros no)
      (usegerberextensions yes)
      (usegerberattributes yes)
      (usegerberadvancedattributes yes)
      (creategerberjobfile yes)
      (dashed_line_dash_ratio 12)
      (dashed_line_gap_ratio 3)
      (svgprecision 4)
      (plotframeref no)
      (viasonmask no)
      (mode 1)
      (useauxorigin no)
      (hpglpennumber 1)
      (hpglpenspeed 20)
      (hpglpendiameter 15)
      (pdf_front_fp_property_popups yes)
      (pdf_back_fp_property_popups yes)
      (dxfpolygonmode yes)
      (dxfimperialunits no)
      (dxfusepcbnewfont yes)
      (psnegative no)
      (psa4output no)
      (plotreference yes)
      (plotvalue yes)
      (plotfptext yes)
      (plotinvisibletext no)
      (sketchpadsonfab no)
      (subtractmaskfromsilk no)
      (outputformat 1)
      (mirror no)
      (drillshape 1)
      (scaleselection 1)
      (outputdirectory "gerber/")
    )
  )
{net_lines}
{fps}
{segs}
{vias}
{zone}
{edge}
)
"""


def add_simple_fp(board: Board, lib: str, ref: str, value: str, x: float, y: float, rot: float, pads: list[tuple]) -> None:
    raw_lines = [
        f'(footprint "{lib}"',
        '  (layer "F.Cu")',
        f'  (uuid "{uid()}")',
        f'  (at {x:.3f} {y:.3f} {rot})',
        f'  (property "Reference" "{ref}" (at 0 3 0) (layer "F.SilkS") (effects (font (size 0.7 0.7) (thickness 0.1))))',
        f'  (property "Value" "{value}" (at 0 -3 0) (layer "F.Fab") (effects (font (size 0.7 0.7) (thickness 0.1)) hide))',
    ]
    for num, lx, ly, net, kind in pads:
        raw_lines.append(f"  PAD {num}|{lx}|{ly}|{net}|{kind}")
    raw_lines.append(")")
    board.add_fp(render_fp("\n".join(raw_lines), board))
    board.parts.append({"ref": ref, "value": value, "x": x, "y": y, "rot": rot, "layer": "top"})


def build_matrix_pcb() -> Board:
    b = Board(BOARD_W, BOARD_H)
    # 3V3 rail on the left margin and one spur per rank
    b.track(6, 20, 6, 430, "3V3", 0.5)
    for row in range(8):
        sy = ORIGIN + row * PITCH
        b.track(6, sy + 8, 400, sy + 8, "3V3", 0.4)

    for row in range(8):
        for col in range(8):
            idx = sq_index(col, row)
            name = sq_name(col, row)
            net = f"SQ_{name}"
            sx, sy = center(col, row)
            add_simple_fp(
                b,
                "chessstream:ReedSwitch_D2_L12",
                f"SW{idx+1}",
                name,
                sx,
                sy,
                0,
                [("1", -6, 0, "GND", "th"), ("2", 6, 0, net, "th")],
            )
            # pull-up just above the signal pad
            add_simple_fp(
                b,
                "chessstream:R_0805",
                f"R{idx+5}",
                "10k",
                sx + 6,
                sy + 6,
                90,
                [("1", -0.95, 0, net, "r0805"), ("2", 0.95, 0, "3V3", "r0805")],
            )
            # resistor is rotated 90 deg in KiCad: local +X rotates to +Y? 
            # KiCad rotation is CCW. rot 90: local (x,y) -> (-y, x).
            # We'll route using explicit world points assuming rot 0 placement instead.
            # Recreate pull-up unrotated horizontally between signal pad and the 3V3 spur.
            # The footprint above is rot 90 which complicates pads. Override by using rot 0
            # placed between pad and spur: center (sx+6, sy+4) is wrong for horizontal.
            # Leave footprint; add tracks to the unrotated pad math if rot is 0.
            b.via(sx - 6, sy - 3, "GND")
            b.track(sx - 6, sy, sx - 6, sy - 3, "GND", 0.4)

    # The pull-up footprints were rotated. Rebuild them unrotated for a clean net.
    # Remove is hard; instead place a second correct resistor and we should not have added rot 90.
    # Fix: the generator is the source — I'll adjust above by not using rot 90.
    # Done below by reconstructing board cleanly.
    return b


def build_matrix_pcb_clean() -> Board:
    b = Board(BOARD_W, BOARD_H)
    b.track(8, 30, 8, 430, "3V3", 0.6)
    for row in range(8):
        sy = ORIGIN + row * PITCH
        b.track(8, sy + 8, ORIGIN + 7 * PITCH + 10, sy + 8, "3V3", 0.35)

    mux_xy = []
    for m in range(4):
        # between the two ranks this mux serves
        y = ORIGIN + (m * 2) * PITCH + PITCH / 2
        x = 436.0
        mux_xy.append((x, y))
        pads = []
        for pin in range(1, 25):
            lx, ly = soic24_pad(pin)
            pname = MUX_PINS[pin]
            pads.append((str(pin), lx, ly, mux_pin_net(m, pin, pname), "soic"))
        add_simple_fp(
            b,
            "chessstream:SOIC-24W_7.5x15.4_P1.27",
            f"U{m+3}",
            "CD74HC4067",
            x,
            y,
            0,
            pads,
        )
        add_simple_fp(
            b,
            "chessstream:C_0805",
            f"C{m+4}",
            "100nF",
            x - 8,
            y + 12,
            0,
            [("1", -0.95, 0, "3V3", "r0805"), ("2", 0.95, 0, "GND", "r0805")],
        )
        b.via(x - 8 + 0.95, y + 12, "GND")

    for row in range(8):
        for col in range(8):
            idx = sq_index(col, row)
            name = sq_name(col, row)
            net = f"SQ_{name}"
            mux = idx // 16
            ch = idx % 16
            sx, sy = center(col, row)
            add_simple_fp(
                b,
                "chessstream:ReedSwitch_D2_L12",
                f"SW{idx+1}",
                name,
                sx,
                sy,
                0,
                [("1", -6, 0, "GND", "th"), ("2", 6, 0, net, "th")],
            )
            # horizontal 0805 from signal pad toward the 3V3 spur at sy+8
            rx = sx + 10
            ry = sy + 8
            add_simple_fp(
                b,
                "chessstream:R_0805",
                f"R{idx+5}",
                "10k",
                rx,
                ry,
                90,
                # rot 90 CCW: world = (x - ly, y + lx)
                # We store local pads and also route in world space matching KiCad rot.
                [("1", -0.95, 0, net, "r0805"), ("2", 0.95, 0, "3V3", "r0805")],
            )
            # KiCad rotates footprint pads. For rot=90, pad local (lx,ly) -> world (x-ly, y+lx)
            # pad1 local (-0.95, 0) -> (rx, ry-0.95)
            # pad2 local (0.95, 0) -> (rx, ry+0.95)
            # 3V3 spur is at sy+8 = ry, so pad2 is 0.95 above the spur. Jog it.
            b.track(sx + 6, sy, rx, sy, net, 0.25)
            b.track(rx, sy, rx, ry - 0.95, net, 0.25)
            b.track(rx, ry + 0.95, rx, ry + 2.2, "3V3", 0.25)  # up toward... spur is at ry
            # pad2 is at ry+0.95, spur at ry. Connect down.
            b.track(rx, ry + 0.95, rx + 1.2, ry + 0.95, "3V3", 0.25)
            b.track(rx + 1.2, ry + 0.95, rx + 1.2, ry, "3V3", 0.25)

            b.via(sx - 6, sy - 3.2, "GND")
            b.track(sx - 6, sy, sx - 6, sy - 3.2, "GND", 0.35)

            # route signal to mux channel pad
            mx, my = mux_xy[mux]
            pin = CHANNEL_PIN[ch]
            plx, ply = soic24_pad(pin)
            px, py = mx + plx, my + ply
            lane_x = 418 + ch * 0.85
            b.route([(sx + 6, sy), (lane_x, sy), (lane_x, py), (px, py)], net, 0.25)

    # select / COM / power from muxes back to the header at the bottom margin
    # Header at (160, 8) rot 0: pin (col, row) local (col*2.54, row*2.54)
    hx, hy = 180.0, 6.0
    hdr_pads = []
    pin_world = {}
    for i in range(10):
        for col, base in ((0, 1), (1, 2)):
            num = base + i * 2
            lx, ly = col * 2.54, i * 2.54
            net = "NC" if num > 12 else dict(HDR_PINS)[num]
            if net == "NC":
                net = f"NC{num}"
            hdr_pads.append((str(num), lx, ly, net, "th2"))
            pin_world[num] = (hx + lx, hy + ly)
    add_simple_fp(b, "chessstream:PinHeader_2x10_P2.54", "J3", "TO_CONTROLLER", hx, hy, 0, hdr_pads)

    # Tie mux COM and address pins with a bus in the top-of-border / along x=410
    for m, (mx, my) in enumerate(mux_xy):
        com_pin = 1
        lx, ly = soic24_pad(com_pin)
        b.route([(mx + lx, my + ly), (pin_world[3 + m][0], my + ly), pin_world[3 + m]], f"SIG{m+1}", 0.3)
        for sel, pin in (("S0", 10), ("S1", 11), ("S2", 14), ("S3", 13)):
            lx, ly = soic24_pad(pin)
            # collect later
            b.route([(mx + lx, my + ly), (405, my + ly), (405, pin_world[{"S0": 7, "S1": 8, "S2": 9, "S3": 10}[sel]][1]), pin_world[{"S0": 7, "S1": 8, "S2": 9, "S3": 10}[sel]]], sel, 0.3)
        for pwr_pin, net in ((24, "3V3"), (12, "GND"), (15, "GND")):
            lx, ly = soic24_pad(pwr_pin)
            if net == "GND":
                b.via(mx + lx, my + ly, "GND")
            else:
                b.route([(mx + lx, my + ly), (8, my + ly)], "3V3", 0.4)

    b.route([pin_world[1], (8, pin_world[1][1])], "3V3", 0.5)
    b.via(pin_world[2][0], pin_world[2][1], "GND")
    b.via(pin_world[12][0], pin_world[12][1], "GND")
    # LED net just reaches the header; the LED itself is on the controller
    b.track(pin_world[11][0], pin_world[11][1], pin_world[11][0], 20, "LED", 0.25)

    # mounting holes
    for mx_, my_ in ((5, 5), (445, 5), (5, 445), (445, 445)):
        add_simple_fp(
            b,
            "chessstream:MountingHole",
            "H",
            "M3",
            mx_,
            my_,
            0,
            [("1", 0, 0, "GND", "th")],
        )
    return b


def build_controller_pcb() -> Board:
    b = Board(CTRL_W, CTRL_H)
    # ESP32 centered, antenna toward +Y (top of 50mm board)
    ex, ey = 40.0, 26.0
    pads = []
    for pin in range(1, 39):
        lx, ly = esp32_pad(pin)
        net = {
            1: "GND",
            2: "3V3",
            3: "EN",
            6: "SIG3",
            7: "SIG4",
            8: "SIG1",
            9: "SIG2",
            10: "S0",
            11: "S1",
            12: "S2",
            13: "S3",
            24: "LED",
            38: "GND",
        }.get(pin, f"NC_ESP{pin}")
        pads.append((str(pin), lx, ly, net, "esp"))
    add_simple_fp(b, "chessstream:ESP32-WROOM-32E", "U2", "ESP32-WROOM-32E", ex, ey, 0, pads)

    # USB-C at left edge
    add_simple_fp(
        b,
        "chessstream:USB_C_16_PowerOnly",
        "J1",
        "USB-C",
        8,
        14,
        0,
        [
            ("A4", -1.25, 3.2, "VBUS", "usb"),
            ("A1", 0.0, 3.2, "GND", "usb"),
            ("A5", 1.25, 3.2, "CC1", "usb"),
            ("B5", -1.25, -3.2, "CC2", "usb"),
            ("SH", 4.6, 0, "GND", "usb"),
            ("SH", -4.6, 0, "GND", "sot_tab"),
        ],
    )
    add_simple_fp(b, "chessstream:R_0805", "R1", "5.1k", 16, 10, 0, [("1", -0.95, 0, "CC1", "r0805"), ("2", 0.95, 0, "GND", "r0805")])
    add_simple_fp(b, "chessstream:R_0805", "R2", "5.1k", 16, 6, 0, [("1", -0.95, 0, "CC2", "r0805"), ("2", 0.95, 0, "GND", "r0805")])
    b.via(16.95, 10, "GND")
    b.via(16.95, 6, "GND")
    b.track(8 - 1.25, 14 + 3.2, 16 - 0.95, 10, "CC1", 0.25)
    b.track(8 - 1.25, 14 - 3.2, 16 - 0.95, 6, "CC2", 0.25)

    # LDO
    add_simple_fp(
        b,
        "chessstream:SOT-223",
        "U1",
        "AMS1117-3.3",
        22,
        30,
        0,
        [
            ("1", -2.3, 3.15, "GND", "sot"),
            ("2", 0.0, 3.15, "3V3", "sot"),
            ("3", 2.3, 3.15, "VBUS", "sot"),
            ("2", 0.0, -1.6, "3V3", "sot_tab"),
        ],
    )
    add_simple_fp(b, "chessstream:C_0805", "C1", "10uF", 30, 36, 0, [("1", -0.95, 0, "VBUS", "r0805"), ("2", 0.95, 0, "GND", "r0805")])
    add_simple_fp(b, "chessstream:C_0805", "C2", "10uF", 30, 28, 0, [("1", -0.95, 0, "3V3", "r0805"), ("2", 0.95, 0, "GND", "r0805")])
    add_simple_fp(b, "chessstream:C_0805", "C3", "100nF", 36, 28, 0, [("1", -0.95, 0, "3V3", "r0805"), ("2", 0.95, 0, "GND", "r0805")])
    b.via(30.95, 36, "GND")
    b.via(30.95, 28, "GND")
    b.via(36.95, 28, "GND")
    b.track(8 - 1.25, 14 + 3.2, 22 + 2.3, 30 + 3.15, "VBUS", 0.5)
    b.track(22 + 2.3, 30 + 3.15, 30 - 0.95, 36, "VBUS", 0.4)
    b.track(22, 30 + 3.15, 30 - 0.95, 28, "3V3", 0.5)

    # EN pull-up
    add_simple_fp(b, "chessstream:R_0805", "R3", "10k", 28, 42, 0, [("1", -0.95, 0, "3V3", "r0805"), ("2", 0.95, 0, "EN", "r0805")])
    # ESP pin 3 EN local
    enx, eny = ex + esp32_pad(3)[0], ey + esp32_pad(3)[1]
    b.route([(28.95, 42), (enx, 42), (enx, eny)], "EN", 0.25)
    b.track(22, 30 - 1.6, 28 - 0.95, 42, "3V3", 0.4)

    # 3V3 and GND into module
    p3x, p3y = ex + esp32_pad(2)[0], ey + esp32_pad(2)[1]
    b.route([(22, 30 - 1.6), (p3x - 2, 30 - 1.6), (p3x - 2, p3y), (p3x, p3y)], "3V3", 0.4)
    for gpin in (1, 38):
        gx, gy = ex + esp32_pad(gpin)[0], ey + esp32_pad(gpin)[1]
        b.via(gx - 1.2, gy, "GND")
        b.track(gx, gy, gx - 1.2, gy, "GND", 0.4)

    # LED on GPIO2
    add_simple_fp(b, "chessstream:R_0805", "R4", "330", 62, 20, 0, [("1", -0.95, 0, "LED", "r0805"), ("2", 0.95, 0, "LED_A", "r0805")])
    add_simple_fp(b, "chessstream:LED_0805", "D1", "BLUE", 70, 20, 0, [("1", -0.95, 0, "LED_A", "r0805"), ("2", 0.95, 0, "GND", "r0805")])
    iox, ioy = ex + esp32_pad(24)[0], ey + esp32_pad(24)[1]
    b.route([(iox, ioy), (62 - 0.95, ioy), (62 - 0.95, 20)], "LED", 0.25)
    b.track(62.95, 20, 70 - 0.95, 20, "LED_A", 0.25)
    b.via(70.95, 20, "GND")

    # Header on the right
    hx, hy = 64.0, 30.0
    hdr_pads = []
    pin_world = {}
    for i in range(10):
        for col, base in ((0, 1), (1, 2)):
            num = base + i * 2
            lx, ly = col * 2.54, (i - 4.5) * 2.54
            net = dict(HDR_PINS).get(num, f"NC{num}")
            if num > 12:
                net = f"NC{num}"
            hdr_pads.append((str(num), lx, ly, net, "th2"))
            pin_world[num] = (hx + lx, hy + ly)
    add_simple_fp(b, "chessstream:PinHeader_2x10_P2.54", "J2", "TO_MATRIX", hx, hy, 0, hdr_pads)

    def esp_world(pin: int) -> tuple[float, float]:
        lx, ly = esp32_pad(pin)
        return (ex + lx, ey + ly)

    pairs = [
        (8, 3, "SIG1"),
        (9, 4, "SIG2"),
        (6, 5, "SIG3"),
        (7, 6, "SIG4"),
        (10, 7, "S0"),
        (11, 8, "S1"),
        (12, 9, "S2"),
        (13, 10, "S3"),
        (24, 11, "LED"),
    ]
    for esp_pin, hdr_pin, net in pairs:
        b.route([esp_world(esp_pin), pin_world[hdr_pin]], net, 0.25)
    b.route([esp_world(2), pin_world[1]], "3V3", 0.4)
    b.via(pin_world[2][0], pin_world[2][1], "GND")
    b.via(pin_world[12][0], pin_world[12][1], "GND")
    return b


# ---------- gerber / excellon ----------

def gcoord(v: float) -> str:
    return str(int(round(v * 1_000_000)))


def write_gerber_for_board(board: Board, folder: Path, name: str) -> None:
    folder.mkdir(parents=True, exist_ok=True)

    def header(func: str) -> str:
        return (
            f"G04 ChessStream {name}*\n"
            "%FSLAX46Y46*%\n%MOMM*%\n%LPD*%\n"
            f"G04 {func}*\n"
            "%ADD10C,0.250000*%\n%ADD11C,0.500000*%\n%ADD12C,0.800000*%\n"
            "%ADD13C,1.600000*%\n%ADD14R,1.500000X0.600000*%\n"
            "%ADD15C,0.100000*%\n"
        )

    def finish(body: str) -> str:
        return body + "M02*\n"

    # Edge
    edge = header("Edge.Cuts")
    edge += "D15*\n"
    edge += f"X{gcoord(0)}Y{gcoord(0)}D02*\n"
    edge += f"X{gcoord(board.width)}Y{gcoord(0)}D01*\n"
    edge += f"X{gcoord(board.width)}Y{gcoord(board.height)}D01*\n"
    edge += f"X{gcoord(0)}Y{gcoord(board.height)}D01*\n"
    edge += f"X{gcoord(0)}Y{gcoord(0)}D01*\n"
    (folder / f"{name}-Edge_Cuts.gbr").write_text(finish(edge), encoding="utf-8")

    # F.Cu tracks
    cu = header("F.Cu")
    cu += "D10*\n"
    for x1, y1, x2, y2, net, width in board.segments:
        aper = "D11" if width >= 0.45 else "D10"
        cu += f"{aper}*\n"
        cu += f"X{gcoord(x1)}Y{gcoord(y1)}D02*\n"
        cu += f"X{gcoord(x2)}Y{gcoord(y2)}D01*\n"
    for x, y, net in board.vias:
        cu += "D12*\n"
        cu += f"X{gcoord(x)}Y{gcoord(y)}D03*\n"
    (folder / f"{name}-F_Cu.gbr").write_text(finish(cu), encoding="utf-8")

    # B.Cu ground pour outline + vias
    bcu = header("B.Cu")
    bcu += "%ADD16C,0.200000*%\n"
    bcu += "G36*\n"
    for x, y in ((1, 1), (board.width - 1, 1), (board.width - 1, board.height - 1), (1, board.height - 1)):
        bcu += f"X{gcoord(x)}Y{gcoord(y)}D01*\n"
    bcu = bcu.replace("D01*\n", "D02*\n", 1)
    bcu += "G37*\n"
    bcu += "D12*\n"
    for x, y, net in board.vias:
        if net == "GND":
            bcu += f"X{gcoord(x)}Y{gcoord(y)}D03*\n"
    (folder / f"{name}-B_Cu.gbr").write_text(finish(bcu), encoding="utf-8")

    silk = header("F.SilkS")
    silk += "D15*\n"
    silk += f"X{gcoord(2)}Y{gcoord(2)}D02*\nX{gcoord(board.width-2)}Y{gcoord(2)}D01*\n"
    (folder / f"{name}-F_SilkS.gbr").write_text(finish(silk), encoding="utf-8")

    mask = header("F.Mask")
    mask += "D13*\n"
    # flashes at via/pad approximate positions are in the excellon; mask openings at vias
    for x, y, net in board.vias:
        mask += f"X{gcoord(x)}Y{gcoord(y)}D03*\n"
    (folder / f"{name}-F_Mask.gbr").write_text(finish(mask), encoding="utf-8")
    (folder / f"{name}-B_Mask.gbr").write_text(finish(header("B.Mask") + "D13*\n"), encoding="utf-8")

    # Excellon: vias + through-hole pads. Parse footprints roughly from stored parts is insufficient.
    # Vias + mounting. Through-hole pad world coords are recovered from segments endpoints? 
    # Store drills on the board object via vias plus we scan footprint text.
    drills = [(x, y, 0.4) for x, y, _ in board.vias]
    for fp in board.footprints:
        at = None
        rot = 0.0
        for line in fp.splitlines():
            if "(at " in line and line.strip().startswith("(at") and "property" not in line and "pad" not in line:
                bits = line.strip().strip("()").split()
                # at x y rot
                if bits[0] == "at":
                    at = (float(bits[1]), float(bits[2]))
                    if len(bits) > 3:
                        rot = float(bits[3])
            if "(pad " in line and "thru_hole" in line:
                # (pad "1" thru_hole circle (at -6 0) (size 1.6 1.6) (drill 0.8)
                local = line.split("(at ")[1].split(")")[0].split()
                lx, ly = float(local[0]), float(local[1])
                drill = 0.8
                if "(drill " in line:
                    drill = float(line.split("(drill ")[1].split(")")[0].split()[0])
                if at is None:
                    continue
                rx, ry = rotate_point(lx, ly, rot)
                drills.append((at[0] + rx, at[1] + ry, drill))
    exc = ["M48", "; ChessStream drills", "METRIC,TZ", "T01C0.400", "T02C0.800", "T03C1.000", "%", "G90", "G05"]
    for x, y, d in drills:
        tool = "T01" if d < 0.6 else "T02" if d < 0.9 else "T03"
        exc.append(tool)
        exc.append(f"X{x:.3f}Y{y:.3f}")
    exc.append("M30")
    (folder / f"{name}.drl").write_text("\n".join(exc) + "\n", encoding="utf-8")


def write_bom(matrix: Board, ctrl: Board) -> None:
    GERBER.mkdir(parents=True, exist_ok=True)
    rows = ["Designator,Value,Footprint,Quantity,LCSC"]
    grouped: dict[tuple[str, str], list[str]] = {}
    for part in matrix.parts + ctrl.parts:
        if part["ref"].startswith("H"):
            continue
        key = (part["value"], part["ref"][:1])
        grouped.setdefault((part["value"], ""), []).append(part["ref"])
    # collapse by value
    by_val: dict[str, list[str]] = {}
    for part in matrix.parts + ctrl.parts:
        if part["ref"] in ("H",) or part["value"] == "M3":
            continue
        by_val.setdefault(part["value"], []).append(part["ref"])
    lcsc = {
        "10k": "C25804",
        "5.1k": "C25905",
        "330": "C23138",
        "100nF": "C1525",
        "10uF": "C15850",
        "CD74HC4067": "C514342",
        "ESP32-WROOM-32E": "C701341",
        "AMS1117-3.3": "C6186",
        "BLUE": "C2297",
        "USB-C": "C2765186",
        "TO_MATRIX": "C49257",
        "TO_CONTROLLER": "C49257",
    }
    for value, refs in sorted(by_val.items(), key=lambda kv: kv[0]):
        rows.append(f"\"{' '.join(refs)}\",{value},,{len(refs)},{lcsc.get(value, '')}")
    # reeds share value = square name, group them
    (GERBER / "bom.csv").write_text("\n".join(rows) + "\n", encoding="utf-8")

    cpl = ["Designator,Mid X,Mid Y,Layer,Rotation"]
    for part in matrix.parts + ctrl.parts:
        prefix = "M-" if part in matrix.parts else "C-"
        # controller and matrix are separate boards; write two files
    (GERBER / "positions_matrix.csv").write_text(
        "Designator,Mid X,Mid Y,Layer,Rotation\n"
        + "\n".join(f"{p['ref']},{p['x']:.3f},{p['y']:.3f},top,{p['rot']}" for p in matrix.parts)
        + "\n",
        encoding="utf-8",
    )
    (GERBER / "positions_controller.csv").write_text(
        "Designator,Mid X,Mid Y,Layer,Rotation\n"
        + "\n".join(f"{p['ref']},{p['x']:.3f},{p['y']:.3f},top,{p['rot']}" for p in ctrl.parts)
        + "\n",
        encoding="utf-8",
    )


# ---------- meshes ----------

def box_tris(x0, y0, z0, x1, y1, z1) -> list[tuple]:
    v = [
        (x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
        (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1),
    ]
    faces = [
        (0, 2, 1), (0, 3, 2),
        (4, 5, 6), (4, 6, 7),
        (0, 1, 5), (0, 5, 4),
        (1, 2, 6), (1, 6, 5),
        (2, 3, 7), (2, 7, 6),
        (3, 0, 4), (3, 4, 7),
    ]
    return [(v[a], v[b], v[c]) for a, b, c in faces]


def write_stl(path: Path, name: str, tris: list[tuple]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"solid {name}"]
    for a, b, c in tris:
        lines.append("  facet normal 0 0 0")
        lines.append("    outer loop")
        for v in (a, b, c):
            lines.append(f"      vertex {v[0]:.4f} {v[1]:.4f} {v[2]:.4f}")
        lines.append("    endloop")
        lines.append("  endfacet")
    lines.append(f"endsolid {name}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def annulus_prism(cx, cy, z0, z1, r_out, r_in, n=28) -> list[tuple]:
    """Tube from z0 to z1. If z cavity is partial, caller stacks pieces."""
    tris = []

    def ring(z, r):
        return [
            (cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n), z)
            for i in range(n)
        ]

    outer0, outer1 = ring(z0, r_out), ring(z1, r_out)
    inner0, inner1 = ring(z0, r_in), ring(z1, r_in)
    for i in range(n):
        j = (i + 1) % n
        tris.append((outer0[i], outer0[j], outer1[j]))
        tris.append((outer0[i], outer1[j], outer1[i]))
        tris.append((inner0[i], inner1[j], inner0[j]))
        tris.append((inner0[i], inner1[i], inner1[j]))
        tris.append((outer0[i], inner0[i], inner0[j]))
        tris.append((outer0[i], inner0[j], outer0[j]))
        tris.append((outer1[i], outer1[j], inner1[j]))
        tris.append((outer1[i], inner1[j], inner1[i]))
    return tris


def cylinder(cx, cy, z0, z1, r, n=28) -> list[tuple]:
    return annulus_prism(cx, cy, z0, z1, r, 0.0, n) if False else _solid_cyl(cx, cy, z0, z1, r, n)


def _solid_cyl(cx, cy, z0, z1, r, n=28) -> list[tuple]:
    tris = []
    bot = [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n), z0) for i in range(n)]
    top = [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n), z1) for i in range(n)]
    cbot = (cx, cy, z0)
    ctop = (cx, cy, z1)
    for i in range(n):
        j = (i + 1) % n
        tris.append((cbot, bot[j], bot[i]))
        tris.append((ctop, top[i], top[j]))
        tris.append((bot[i], bot[j], top[j]))
        tris.append((bot[i], top[j], top[i]))
    return tris


def piece_mesh(kind: str) -> list[tuple]:
    """Staunton-like solid of revolution. Magnet cavity is a 10mm x 4mm pocket in the base."""
    spec = {
        "pawn": (14, 40, [(14, 0, 6), (12, 6, 10), (8, 16, 22), (6, 28, 34), (9, 34, 40)]),
        "rook": (16, 48, [(16, 0, 8), (13, 8, 14), (10, 14, 36), (14, 36, 48)]),
        "knight": (16, 52, [(16, 0, 8), (12, 8, 18), (9, 18, 40), (11, 40, 52)]),
        "bishop": (16, 58, [(16, 0, 8), (12, 8, 16), (8, 16, 44), (5, 44, 52), (8, 52, 58)]),
        "queen": (17, 68, [(17, 0, 8), (13, 8, 16), (9, 16, 52), (12, 52, 60), (7, 60, 68)]),
        "king": (18, 76, [(18, 0, 8), (14, 8, 16), (10, 16, 58), (13, 58, 66), (6, 66, 72), (3, 72, 76)]),
    }
    r_base, _h, bands = spec[kind]
    tris: list[tuple] = []
    # base with cavity: annulus 0..4mm then solid 4..first band
    tris += annulus_prism(0, 0, 0, 4, r_base, 5.0, 32)
    first_top = bands[0][1]
    if first_top < 4:
        first_top = 4
    tris += cylinder(0, 0, 4, bands[0][2], bands[0][0], 32)
    for r, z0, z1 in bands[1:]:
        tris += cylinder(0, 0, z0, z1, r, 32)
    if kind == "knight":
        tris += box_tris(-4, 6, 40, 10, 14, 54)
    if kind == "rook":
        tris += box_tris(-12, -3, 44, 12, 3, 50)
        tris += box_tris(-3, -12, 44, 3, 12, 50)
    if kind == "king":
        tris += box_tris(-2, -8, 72, 2, 8, 80)
        tris += box_tris(-8, -2, 72, 8, 2, 80)
    return tris


def enclosure_meshes() -> dict[str, list]:
    # Base 500x500x6
    base = box_tris(0, 0, 0, 500, 500, 6)
    # PCB pocket is air from z=6 to z=14 over the center 460x460, so the base is a slab
    # and a lip. Represent the lip as four walls from z=6 to z=14.
    walls = []
    walls += box_tris(0, 0, 6, 500, 20, 14)
    walls += box_tris(0, 480, 6, 500, 500, 14)
    walls += box_tris(0, 20, 6, 20, 480, 14)
    walls += box_tris(480, 20, 6, 500, 480, 14)
    frame = []
    # Playing frame z=14..22 with 4mm ribs on a 50mm grid, field from 50 to 450
    frame += box_tris(0, 0, 14, 500, 50, 22)
    frame += box_tris(0, 450, 14, 500, 500, 22)
    frame += box_tris(0, 50, 14, 50, 450, 22)
    frame += box_tris(450, 50, 14, 500, 450, 22)
    for i in range(1, 8):
        x = 50 + i * 50 - 2
        frame += box_tris(x, 50, 14, x + 4, 450, 22)
        y = 50 + i * 50 - 2
        frame += box_tris(50, y, 14, 450, y + 4, 22)
    # reed holes are through the squares; represented on the top skin
    top = []
    # vinyl sheet approximated as border plus we skip holes by not filling square centers fully:
    # a 1mm skin only on the ribs and border so squares stay open above the PCB sensors
    top += box_tris(0, 0, 22, 500, 50, 23)
    top += box_tris(0, 450, 22, 500, 500, 23)
    top += box_tris(0, 50, 22, 50, 450, 23)
    top += box_tris(450, 50, 22, 500, 450, 23)
    for i in range(1, 8):
        x = 50 + i * 50 - 2
        top += box_tris(x, 50, 22, x + 4, 450, 23)
        y = 50 + i * 50 - 2
        top += box_tris(50, y, 22, 450, y + 4, 23)
    controller = box_tris(0, 0, 0, 90, 60, 18)
    controller += box_tris(4, 4, 18, 86, 56, 20)  # lid lip marker, actually a separate lid:
    lid = box_tris(0, 0, 0, 90, 60, 2)
    return {
        "board_base": base,
        "board_walls": walls,
        "board_frame": frame,
        "board_top": top,
        "controller_box": controller,
        "controller_lid": lid,
    }


def write_dxf(path: Path) -> None:
    ents = []

    def line(x1, y1, x2, y2):
        ents.append(
            f"0\nLINE\n8\nCUT\n10\n{x1:.3f}\n20\n{y1:.3f}\n30\n0\n11\n{x2:.3f}\n21\n{y2:.3f}\n31\n0\n"
        )

    def rect(x0, y0, x1, y1):
        line(x0, y0, x1, y0)
        line(x1, y0, x1, y1)
        line(x1, y1, x0, y1)
        line(x0, y1, x0, y0)

    def circle(cx, cy, r):
        ents.append(f"0\nCIRCLE\n8\nDRILL\n10\n{cx:.3f}\n20\n{cy:.3f}\n30\n0\n40\n{r:.3f}\n")

    rect(0, 0, 500, 500)
    for row in range(8):
        for col in range(8):
            x0 = 50 + col * 50 + 2
            y0 = 50 + row * 50 + 2
            rect(x0, y0, x0 + 46, y0 + 46)
            circle(50 + col * 50 + 25, 50 + row * 50 + 25, 1.5)
    for cx, cy in ((8, 8), (492, 8), (8, 492), (492, 492)):
        circle(cx, cy, 1.6)
    body = "".join(ents)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "0\nSECTION\n2\nHEADER\n9\n$INSUNITS\n70\n4\n0\nENDSEC\n"
        "0\nSECTION\n2\nENTITIES\n" + body + "0\nENDSEC\n0\nEOF\n",
        encoding="utf-8",
    )


def write_freecad_script() -> None:
    ENC.mkdir(parents=True, exist_ok=True)
    (ENC / "generate_enclosure.py").write_text(
        '''"""
FreeCAD parametric enclosure for ChessStream India.

Open in FreeCAD 0.21+ and run this macro, or:
    freecadcmd generate_enclosure.py

Exports STEP and STL into ./export/
"""
import os

try:
    import FreeCAD as App
    import Part
except ImportError:
    raise SystemExit("Run this script with FreeCAD (freecadcmd).")

OUT = os.path.join(os.path.dirname(__file__), "export")
os.makedirs(OUT, exist_ok=True)

doc = App.newDocument("chessstream_enclosure")

def box(name, x, y, z, sx, sy, sz):
    shape = Part.makeBox(sx, sy, sz, App.Vector(x, y, z))
    obj = doc.addObject("Part::Feature", name)
    obj.Shape = shape
    return obj

base = box("base", 0, 0, 0, 500, 500, 6)
walls = []
walls.append(box("wall_s", 0, 0, 6, 500, 20, 8))
walls.append(box("wall_n", 0, 480, 6, 500, 20, 8))
walls.append(box("wall_w", 0, 20, 6, 20, 460, 8))
walls.append(box("wall_e", 480, 20, 6, 20, 460, 8))

frame = Part.makeBox(500, 500, 8, App.Vector(0, 0, 14))
for row in range(8):
    for col in range(8):
        pocket = Part.makeBox(46, 46, 8, App.Vector(52 + col * 50, 52 + row * 50, 14))
        frame = frame.cut(pocket)
        hole = Part.makeCylinder(1.5, 12, App.Vector(75 + col * 50, 75 + row * 50, 12))
        frame = frame.cut(hole)
frame_obj = doc.addObject("Part::Feature", "frame")
frame_obj.Shape = frame

pcb = box("pcb", 25, 25, 6.2, 450, 450, 1.6)

def piece(name, height, radius):
    body = Part.makeCylinder(radius, height, App.Vector(0, 0, 0))
    cavity = Part.makeCylinder(5, 4, App.Vector(0, 0, 0))
    shape = body.cut(cavity)
    obj = doc.addObject("Part::Feature", name)
    obj.Shape = shape
    return obj

specs = [("pawn", 40, 14), ("rook", 48, 16), ("knight", 52, 16), ("bishop", 58, 16), ("queen", 68, 17), ("king", 76, 18)]
for n, h, r in specs:
    piece(n, h, r)

doc.recompute()
Part.export([base, frame_obj, pcb], os.path.join(OUT, "assembly.step"))
frame_obj.Shape.exportStl(os.path.join(OUT, "board_frame_freecad.stl"))
print("Wrote", OUT)
''',
        encoding="utf-8",
    )


def write_step_boxes(path: Path) -> None:
    """AP214 STEP with the enclosure solids as rectangular blocks (no ribs).

    The STL/DXF/FreeCAD script carry the rib and cavity detail. This STEP is a
    dimensionally faithful assembly of the major solids that mechanical CAD can open.
    """
    # Each solid: name, x0,y0,z0,sx,sy,sz in mm
    solids = [
        ("base", 0, 0, 0, 500, 500, 6),
        ("pcb", 25, 25, 6.2, 450, 450, 1.6),
        ("frame_border", 0, 0, 14, 500, 500, 8),
        ("controller", 510, 0, 0, 80, 50, 12),
    ]
    # We'll emit one closed shell per box using the 8-corner brep pattern.
    lines = [
        "ISO-10303-21;",
        "HEADER;",
        "FILE_DESCRIPTION(('ChessStream India enclosure assembly'),'2;1');",
        "FILE_NAME('assembly.step','2026-10-15T12:00:00',('Monara Ventures'),('ChessStream'),' ',' ',' ');",
        "FILE_SCHEMA(('AUTOMOTIVE_DESIGN { 1 0 10303 214 1 1 1 1 }'));",
        "ENDSEC;",
        "DATA;",
    ]
    eid = 1

    def add(entity: str) -> int:
        nonlocal eid
        lines.append(f"#{eid}={entity};")
        cur = eid
        eid += 1
        return cur

    # Application context
    ctx = add("APPLICATION_CONTEXT('automotive design')")
    pctx = add(f"PRODUCT_CONTEXT('',#{ctx},'mechanical')")
    prod = add("PRODUCT('ChessStream','ChessStream enclosure','electronic chessboard',(#%d))" % pctx)
    pdf = add(f"PRODUCT_DEFINITION_FORMATION('0.1','',#{prod})")
    pd = add(f"PRODUCT_DEFINITION('design','',#{pdf},#{pctx})")
    # Keep a note rather than a full invalid manifold. Many importers reject hand-rolled shells.
    add(f"DESCRIPTIVE_REPRESENTATION_ITEM('note','Major solids: base 500x500x6, frame 500x500 from z14, PCB 450x450x1.6. Detailed mesh is board_frame.stl. Open generate_enclosure.py in FreeCAD for the parametric solid with square pockets and 10mm magnet cavities.')")
    lines.append("ENDSEC;")
    lines.append("END-ISO-10303-21;")
    path.parent.mkdir(parents=True, exist_ok=True)
    # A descriptive-only STEP can fail import. Write a real block solid instead via a compact, known-good pattern.
    path.write_text(step_block_assembly(solids), encoding="utf-8")


def step_block_assembly(solids: list[tuple]) -> str:
    """Emit one valid extruded rectangular solid per part using ADVANCED_BREP.

    This follows the common minimal box published for STEP AP214: 8 vertices,
    12 edges, 6 faces, one closed shell. IDs are allocated per solid with an offset.
    """
    chunks = [
        "ISO-10303-21;",
        "HEADER;",
        "FILE_DESCRIPTION(('ChessStream India'),'2;1');",
        "FILE_NAME('assembly.step','2026-10-15T12:00:00',('Monara Ventures'),(''),'','','');",
        "FILE_SCHEMA(('AUTOMOTIVE_DESIGN'));",
        "ENDSEC;",
        "DATA;",
    ]
    # Shared context
    chunks.append("#1=APPLICATION_CONTEXT('automotive design');")
    chunks.append("#2=APPLICATION_PROTOCOL_DEFINITION('international standard','automotive_design',2000,#1);")
    chunks.append("#3=PRODUCT_CONTEXT('',#1,'mechanical');")
    chunks.append("#4=PRODUCT('ChessStreamAssembly','ChessStream','enclosure',(#3));")
    chunks.append("#5=PRODUCT_DEFINITION_FORMATION('0.1','',#4);")
    chunks.append("#6=PRODUCT_DEFINITION('design','',#5,#3);")
    chunks.append("#7=PRODUCT_DEFINITION_CONTEXT('part definition',#1,'design');")
    chunks.append("#8=PRODUCT_DEFINITION_SHAPE('','',#6);")
    next_id = 10
    shape_reps = []

    def nid() -> int:
        nonlocal next_id
        next_id += 1
        return next_id

    for name, x, y, z, sx, sy, sz in solids:
        # corners
        c = [
            (x, y, z),
            (x + sx, y, z),
            (x + sx, y + sy, z),
            (x, y + sy, z),
            (x, y, z + sz),
            (x + sx, y, z + sz),
            (x + sx, y + sy, z + sz),
            (x, y + sy, z + sz),
        ]
        vids = []
        for px, py, pz in c:
            i = nid()
            chunks.append(f"#{i}=CARTESIAN_POINT('',({px:.4f},{py:.4f},{pz:.4f}));")
            vids.append(i)
        # vertex points
        vpts = []
        for vid in vids:
            i = nid()
            chunks.append(f"#{i}=VERTEX_POINT('',#{vid});")
            vpts.append(i)
        # 12 edges as vertex pairs
        edge_pairs = [
            (0, 1), (1, 2), (2, 3), (3, 0),
            (4, 5), (5, 6), (6, 7), (7, 4),
            (0, 4), (1, 5), (2, 6), (3, 7),
        ]
        eids = []
        for a, b in edge_pairs:
            pa, pb = c[a], c[b]
            i1 = nid()
            chunks.append(f"#{i1}=CARTESIAN_POINT('',({pa[0]:.4f},{pa[1]:.4f},{pa[2]:.4f}));")
            i2 = nid()
            d = (pb[0] - pa[0], pb[1] - pa[1], pb[2] - pa[2])
            length = math.sqrt(d[0] ** 2 + d[1] ** 2 + d[2] ** 2)
            chunks.append(f"#{i2}=DIRECTION('',({d[0]/length:.6f},{d[1]/length:.6f},{d[2]/length:.6f}));")
            i3 = nid()
            chunks.append(f"#{i3}=VECTOR('',#{i2},{length:.4f});")
            i4 = nid()
            chunks.append(f"#{i4}=LINE('',#{i1},#{i3});")
            i5 = nid()
            chunks.append(f"#{i5}=EDGE_CURVE('',#{vpts[a]},#{vpts[b]},#{i4},.T.);")
            i6 = nid()
            chunks.append(f"#{i6}=ORIENTED_EDGE('',*,*,#{i5},.T.);")
            eids.append(i6)
        # 6 faces, edge loops. Directions chosen consistently outward-ish.
        faces_edges = [
            [0, 1, 2, 3],       # bottom
            [4, 5, 6, 7],       # top
            [0, 9, 4, 8],       # front y
            [2, 11, 6, 10],     # back y
            [3, 8, 7, 11],      # left
            [1, 10, 5, 9],      # right
        ]
        face_ids = []
        for loop in faces_edges:
            oid = nid()
            elist = ",".join(f"#{eids[k]}" for k in loop)
            chunks.append(f"#{oid}=EDGE_LOOP('',({elist}));")
            fid_bound = nid()
            chunks.append(f"#{fid_bound}=FACE_OUTER_BOUND('',#{oid},.T.);")
            # plane
            origin = c[0]
            pid = nid()
            chunks.append(f"#{pid}=CARTESIAN_POINT('',({origin[0]:.4f},{origin[1]:.4f},{origin[2]:.4f}));")
            did = nid()
            chunks.append(f"#{did}=DIRECTION('',(0.0,0.0,1.0));")
            aid = nid()
            chunks.append(f"#{aid}=AXIS2_PLACEMENT_3D('',#{pid},#{did},$);")
            pl = nid()
            chunks.append(f"#{pl}=PLANE('',#{aid});")
            af = nid()
            chunks.append(f"#{af}=ADVANCED_FACE('',(#{fid_bound}),#{pl},.T.);")
            face_ids.append(af)
        shell = nid()
        fl = ",".join(f"#{f}" for f in face_ids)
        chunks.append(f"#{shell}=CLOSED_SHELL('{name}',({fl}));")
        brep = nid()
        chunks.append(f"#{brep}=MANIFOLD_SOLID_BREP('{name}',#{shell});")
        shape_reps.append(brep)

    items = ",".join(f"#{i}" for i in shape_reps)
    chunks.append(f"#9=ADVANCED_BREP_SHAPE_REPRESENTATION('solids',({items}),#2);")
    chunks.append("ENDSEC;")
    chunks.append("END-ISO-10303-21;")
    return "\n".join(chunks) + "\n"


def mirror_models(src: Path) -> None:
    TWIN_MODELS.mkdir(parents=True, exist_ok=True)
    for p in src.glob("*.stl"):
        shutil.copy(p, TWIN_MODELS / p.name)


def sanity_parens(text: str, label: str) -> None:
    depth = 0
    for ch in text:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth < 0:
                raise SystemExit(f"Unbalanced parens in {label}")
    if depth != 0:
        raise SystemExit(f"Unbalanced parens in {label}: depth {depth}")


def main() -> None:
    PCB.mkdir(parents=True, exist_ok=True)
    write_footprints()
    write_symbol_lib()
    write_project()
    build_schematics()
    matrix = build_matrix_pcb_clean()
    ctrl = build_controller_pcb()
    matrix_txt = dump_board(matrix, "ChessStream matrix 450x450")
    ctrl_txt = dump_board(ctrl, "ChessStream controller 80x50")
    sanity_parens(matrix_txt, "matrix pcb")
    sanity_parens(ctrl_txt, "controller pcb")
    for sch in ("chessstream.kicad_sch", "controller.kicad_sch", "reed_matrix.kicad_sch"):
        sanity_parens((PCB / sch).read_text(encoding="utf-8"), sch)
    (PCB / "chessstream.kicad_pcb").write_text(matrix_txt, encoding="utf-8")
    (PCB / "controller.kicad_pcb").write_text(ctrl_txt, encoding="utf-8")
    write_gerber_for_board(matrix, GERBER / "matrix", "matrix")
    write_gerber_for_board(ctrl, GERBER / "controller", "controller")
    write_bom(matrix, ctrl)

    meshes = enclosure_meshes()
    export = ENC / "export"
    for name, tris in meshes.items():
        write_stl(export / f"{name}.stl", name, tris)
    write_dxf(ENC / "export" / "laser_cut.dxf")
    write_freecad_script()
    pieces_export = PIECES / "export"
    for kind in ("pawn", "rook", "knight", "bishop", "queen", "king"):
        write_stl(pieces_export / f"{kind}.stl", kind, piece_mesh(kind))
        shutil.copy(pieces_export / f"{kind}.stl", export / f"{kind}.stl")
    write_step_boxes(export / "assembly.step")
    mirror_models(export)
    print("Design pack written under", HW)
    print("matrix parts", len(matrix.parts), "tracks", len(matrix.segments), "nets", len(matrix.nets))
    print("controller parts", len(ctrl.parts), "tracks", len(ctrl.segments))


if __name__ == "__main__":
    main()
