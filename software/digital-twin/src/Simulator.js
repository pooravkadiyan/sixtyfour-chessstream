/**
 * In-browser reed-switch board. It emits the same JSON the ESP32 firmware emits.
 * Piece identity and chess rules live in BoardState. This object only speaks the wire protocol.
 */

const FILES = "abcdefgh";
const RANKS = "12345678";

export function squareName(col, row) {
  return FILES[col] + RANKS[row];
}

export function parseSquare(name) {
  return { col: FILES.indexOf(name[0]), row: RANKS.indexOf(name[1]) };
}

const BACK = ["rook", "knight", "bishop", "queen", "king", "bishop", "knight", "rook"];

export function startingPieces() {
  const pieces = {};
  for (let col = 0; col < 8; col++) {
    pieces[squareName(col, 0)] = { type: BACK[col], color: "w" };
    pieces[squareName(col, 1)] = { type: "pawn", color: "w" };
    pieces[squareName(col, 6)] = { type: "pawn", color: "b" };
    pieces[squareName(col, 7)] = { type: BACK[col], color: "b" };
  }
  return pieces;
}

export class Simulator {
  constructor(emit) {
    this.emit = emit;
    this.lifted = null;
    this.moveNumber = 0;
    this.whiteToMove = true;
    this.t0 = performance.now();
  }

  now() {
    return Math.round(performance.now() - this.t0);
  }

  reset() {
    this.lifted = null;
    this.moveNumber = 0;
    this.whiteToMove = true;
    this.emit({
      event: "connected",
      board_id: "CS001",
      firmware: "0.1.0-sim",
      message: "ChessStream India digital twin",
    });
  }

  lift(square) {
    if (this.lifted) return false;
    this.lifted = square;
    this.emit({
      event: "lift",
      square,
      board_id: "CS001",
      timestamp: this.now(),
    });
    return true;
  }

  /**
   * Firmware order on a real move is move, then place.
   * Putting the piece back down emits place only.
   */
  drop(square, color) {
    if (!this.lifted) return null;
    const from = this.lifted;
    this.lifted = null;
    if (from !== square) {
      const movingWhite = color === "w";
      this.moveNumber += 1;
      this.whiteToMove = !movingWhite;
      this.emit({
        event: "move",
        from,
        to: square,
        move_number: this.moveNumber,
        color: movingWhite ? "white" : "black",
        board_id: "CS001",
        timestamp: this.now(),
        uci: from + square,
      });
    }
    this.emit({
      event: "place",
      square,
      board_id: "CS001",
      timestamp: this.now(),
    });
    return from === square ? null : from + square;
  }
}
