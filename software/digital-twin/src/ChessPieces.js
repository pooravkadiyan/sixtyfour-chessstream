import * as THREE from "three";
import { STLLoader } from "three/addons/loaders/STLLoader.js";

const KINDS = ["pawn", "rook", "knight", "bishop", "queen", "king"];

export class ChessPieces {
  constructor(parent) {
    this.parent = parent;
    this.geometry = {};
    this.material = {
      w: new THREE.MeshStandardMaterial({ color: 0xf4f0e6, roughness: 0.45, metalness: 0.08 }),
      b: new THREE.MeshStandardMaterial({ color: 0x1c1a18, roughness: 0.5, metalness: 0.12 }),
    };
  }

  async load() {
    const loader = new STLLoader();
    await Promise.all(
      KINDS.map(async (kind) => {
        const geo = await loader.loadAsync(`./models/${kind}.stl`);
        geo.computeVertexNormals();
        this.geometry[kind] = geo;
      })
    );
  }

  create(piece) {
    const mesh = new THREE.Mesh(this.geometry[piece.type], this.material[piece.color]);
    mesh.castShadow = true;
    mesh.userData.piece = piece;
    mesh.userData.type = piece.type;
    this.parent.add(mesh);
    return mesh;
  }

  retarget(mesh, piece) {
    mesh.geometry = this.geometry[piece.type];
    mesh.userData.type = piece.type;
    return mesh;
  }
}
