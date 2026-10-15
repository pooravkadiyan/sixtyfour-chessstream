"""
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
