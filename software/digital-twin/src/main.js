import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { loadBoard } from "./ChessBoard.js";
import { ChessPieces } from "./ChessPieces.js";
import { BoardState } from "./BoardState.js";
import { Simulator } from "./Simulator.js";
import { BoardSocket } from "./WebSocketClient.js";

const view = document.getElementById("view");
const statusEl = document.getElementById("status");
const logEl = document.getElementById("log");
const pgnEl = document.getElementById("pgn");
const turnEl = document.getElementById("turn");
const reedsEl = document.getElementById("reeds");
const urlEl = document.getElementById("url");

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(view.clientWidth, view.clientHeight);
renderer.shadowMap.enabled = true;
view.prepend(renderer.domElement);

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x161210);
scene.add(new THREE.HemisphereLight(0xfff2dd, 0x2a1c14, 0.85));
const key = new THREE.DirectionalLight(0xfff6e8, 1.15);
key.position.set(180, 420, 80);
key.castShadow = true;
scene.add(key);

const world = new THREE.Group();
// STL is Z-up. Rotate so Z becomes Y, then park the 500 mm board on the origin.
world.rotation.x = -Math.PI / 2;
world.position.set(-250, 0, 250);
scene.add(world);

const camera = new THREE.PerspectiveCamera(38, view.clientWidth / view.clientHeight, 1, 4000);
camera.position.set(280, 380, 320);
const controls = new OrbitControls(camera, renderer.domElement);
controls.target.set(0, 0, 0);
controls.enableDamping = true;
controls.maxPolarAngle = Math.PI / 2.05;

const state = new BoardState();
const pieces = new ChessPieces(world);
const raycaster = new THREE.Raycaster();
const pointer = new THREE.Vector2();
let boardSquares = null;
let dragging = null;
let live = false;
const lines = [];

const sim = new Simulator((msg) => onFirmware(msg, "local"));
const socket = new BoardSocket(
  (msg) => onFirmware(msg, "remote"),
  (text, kind) => {
    statusEl.textContent = text;
    statusEl.className = kind;
    live = kind === "live";
  }
);

function log(line) {
  if (!line) return;
  lines.unshift(line);
  logEl.textContent = lines.slice(0, 16).join("\n");
}

function onFirmware(msg, source) {
  if (source === "remote" && msg.event === "move" && msg.fen && !msg.uci && !msg.from) {
    return;
  }
  const line = state.apply(msg);
  if (msg.event === "move") log(line || `ignored ${msg.uci || ""}`);
  else if (msg.event === "lift") log(line);
  else if (msg.event === "connected") log(msg.message || "connected");
  refresh();
  if (source === "local") socket.send(msg);
}

function refresh() {
  const seen = new Set();
  for (const [square, piece] of Object.entries(state.pieces)) {
    let mesh = piece.mesh;
    if (!mesh) {
      mesh = pieces.create(piece);
      piece.mesh = mesh;
    } else if (mesh.userData.type !== piece.type) {
      pieces.retarget(mesh, piece);
    }
    if (mesh.parent !== world) world.add(mesh);
    const { x, y } = state.squareCenter(square);
    const raised = state.raised && state.raised.piece === piece;
    mesh.position.set(x, y, raised ? 48 : 23);
    mesh.userData.square = square;
    seen.add(mesh);
  }
  for (const child of [...world.children]) {
    if (child.userData && child.userData.piece && !seen.has(child)) {
      world.remove(child);
    }
  }
  const occupied = new Set(state.occupied());
  if (state.raised) occupied.delete(state.raised.square);
  for (const cell of reedsEl.children) {
    cell.classList.toggle("on", occupied.has(cell.dataset.square));
  }
  turnEl.textContent = state.turnLabel();
  pgnEl.textContent = state.pgn() || "(game not started)";
}

function buildReeds() {
  const files = "abcdefgh";
  const ranks = "12345678";
  // Rank 8 on top, matching a printed board.
  for (let row = 7; row >= 0; row--) {
    for (let col = 0; col < 8; col++) {
      const name = files[col] + ranks[row];
      const cell = document.createElement("span");
      cell.dataset.square = name;
      cell.title = name;
      cell.textContent = name;
      reedsEl.appendChild(cell);
    }
  }
}

function pointerNDC(event) {
  const rect = renderer.domElement.getBoundingClientRect();
  pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
  pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
}

function hitSquare(event) {
  pointerNDC(event);
  raycaster.setFromCamera(pointer, camera);
  const hits = raycaster.intersectObjects(boardSquares.children, true);
  const hit = hits.find((h) => h.object.userData.square);
  return hit ? hit.object.userData.square : null;
}

function hitPiece(event) {
  pointerNDC(event);
  raycaster.setFromCamera(pointer, camera);
  const meshes = world.children.filter((c) => c.userData && c.userData.piece);
  const hits = raycaster.intersectObjects(meshes, false);
  return hits[0] ? hits[0].object.userData : null;
}

renderer.domElement.addEventListener("pointerdown", (event) => {
  if (live || event.button !== 0) return;
  const data = hitPiece(event);
  if (!data || !data.square || !state.pieces[data.square]) return;
  if (!sim.lift(data.square)) return;
  dragging = { square: data.square, color: data.piece.color };
  controls.enabled = false;
});

renderer.domElement.addEventListener("pointerup", (event) => {
  if (!dragging) return;
  const from = dragging.square;
  const color = dragging.color;
  dragging = null;
  controls.enabled = true;
  const to = hitSquare(event) || from;
  const target = to !== from && state.legal(from, to) ? to : from;
  if (target !== to) log(`illegal ${from}${to}`);
  sim.drop(target, color);
});

document.getElementById("connect").onclick = () => socket.connect(urlEl.value.trim());
document.getElementById("disconnect").onclick = () => {
  socket.disconnect();
  live = false;
  statusEl.textContent = "Simulator — drag pieces on the board";
  statusEl.className = "sim";
};
document.getElementById("reset").onclick = () => {
  sim.lifted = null;
  sim.moveNumber = 0;
  state.reset();
  lines.length = 0;
  logEl.textContent = "New game.";
  refresh();
};
document.getElementById("state").onclick = () => {
  socket.send({ cmd: "get_state" });
  log(`occupied ${state.occupied().length}`);
};

window.addEventListener("resize", () => {
  camera.aspect = view.clientWidth / view.clientHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(view.clientWidth, view.clientHeight);
});

function frame() {
  controls.update();
  renderer.render(scene, camera);
  requestAnimationFrame(frame);
}

buildReeds();
const loaded = await loadBoard(world);
boardSquares = loaded.squares;
await pieces.load();
sim.reset();
refresh();
frame();
