import { Chess } from "chess.js";
import { parseSquare, squareName, startingPieces } from "./Simulator.js";

const CASTLE_ROOK = {
  e1g1: ["h1", "f1"],
  e1c1: ["a1", "d1"],
  e8g8: ["h8", "f8"],
  e8c8: ["a8", "d8"],
};

/**
 * Piece identity + chess rules. Meshes are attached by ChessPieces.
 * Firmware events are occupancy-level; this class turns them back into pieces.
 */
export class BoardState {
  constructor() {
    this.chess = new Chess();
    this.pieces = startingPieces();
    this.raised = null;
    this.listeners = new Set();
  }

  onChange(fn) {
    this.listeners.add(fn);
  }

  notify() {
    for (const fn of this.listeners) fn(this);
  }

  reset() {
    this.chess.reset();
    this.pieces = startingPieces();
    this.raised = null;
    this.notify();
  }

  occupied() {
    return Object.keys(this.pieces);
  }

  /**
   * Apply one firmware/relay message.
   * Returns a short human line for the move log, or null.
   */
  apply(msg) {
    if (!msg || !msg.event) return null;
    if (msg.event === "lift" && msg.square && this.pieces[msg.square]) {
      this.raised = { square: msg.square, piece: this.pieces[msg.square] };
      this.notify();
      return `lift ${msg.square}`;
    }
    if (msg.event === "move") {
      const uci = msg.uci || (msg.from && msg.to ? msg.from + msg.to : null);
      if (!uci) return null;
      const line = this.playUci(uci);
      this.notify();
      return line;
    }
    if (msg.event === "place") {
      this.raised = null;
      this.notify();
      return null;
    }
    if (msg.event === "board_state" && Array.isArray(msg.occupied) && this.chess.history().length === 0) {
      this.notify();
    }
    return null;
  }

  /** Try a UCI move. On success, pieces match the resulting position. */
  playUci(uci) {
    const from = uci.slice(0, 2);
    const to = uci.slice(2, 4);
    const promotion = uci.length > 4 ? uci[4] : "q";
    let move;
    try {
      move = this.chess.move({ from, to, promotion });
    } catch {
      move = null;
    }
    if (!move) return null;
    this.syncFromChess(move);
    this.raised = null;
    return `${move.color === "w" ? "White" : "Black"} ${move.san}`;
  }

  syncFromChess(move) {
    const dest = this.pieces[move.to];
    const mover = this.pieces[move.from] || (this.raised && this.raised.square === move.from ? this.raised.piece : null);
    if (mover) {
      delete this.pieces[move.from];
      if (move.captured && move.flags.includes("e")) {
        const cap = move.to[0] + move.from[1];
        delete this.pieces[cap];
      } else if (dest && dest !== mover) {
        delete this.pieces[move.to];
      }
      if (move.promotion) mover.type = move.promotion === "q" ? "queen" : move.promotion === "r" ? "rook" : move.promotion === "b" ? "bishop" : "knight";
      this.pieces[move.to] = mover;
    }
    const rookMove = CASTLE_ROOK[move.from + move.to];
    if (rookMove && (move.flags.includes("k") || move.flags.includes("q"))) {
      const rook = this.pieces[rookMove[0]];
      if (rook) {
        delete this.pieces[rookMove[0]];
        this.pieces[rookMove[1]] = rook;
      }
    }
  }

  /** Local drag: ask the rules before the simulator commits. */
  legal(from, to) {
    const moves = this.chess.moves({ square: from, verbose: true });
    return moves.some((m) => m.to === to);
  }

  squareCenter(name) {
    const { col, row } = parseSquare(name);
    return { col, row, x: 75 + col * 50, y: 75 + row * 50 };
  }

  pgn() {
    return this.chess.pgn();
  }

  turnLabel() {
    return this.chess.turn() === "w" ? "White to move" : "Black to move";
  }

  fen() {
    return this.chess.fen();
  }
}

export { squareName };
