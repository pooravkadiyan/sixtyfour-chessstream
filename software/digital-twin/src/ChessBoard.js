import * as THREE from "three";
import { STLLoader } from "three/addons/loaders/STLLoader.js";

const BOARD_PARTS = [
  ["board_base.stl", 0x4a3428],
  ["board_walls.stl", 0x3a281f],
  ["board_frame.stl", 0x6b4a32],
  ["board_top.stl", 0x2c211b],
];

/**
 * Loads the mechanical STL (millimetres, Z up) into one group.
 * Square pickers sit in that same space so raycasts match the CAD.
 */
export async function loadBoard(parent) {
  const loader = new STLLoader();
  const group = new THREE.Group();
  group.name = "enclosure";
  parent.add(group);

  await Promise.all(
    BOARD_PARTS.map(async ([file, color]) => {
      const geo = await loader.loadAsync(`./models/${file}`);
      geo.computeVertexNormals();
      const mesh = new THREE.Mesh(
        geo,
        new THREE.MeshStandardMaterial({ color, roughness: 0.72, metalness: 0.05 })
      );
      mesh.castShadow = true;
      mesh.receiveShadow = true;
      group.add(mesh);
    })
  );

  const files = "abcdefgh";
  const light = new THREE.MeshStandardMaterial({ color: 0xf0d9b5, roughness: 0.85 });
  const dark = new THREE.MeshStandardMaterial({ color: 0xb58863, roughness: 0.85 });
  const pickMat = new THREE.MeshBasicMaterial({ visible: false });
  const squares = new THREE.Group();
  squares.name = "squares";
  group.add(squares);

  for (let row = 0; row < 8; row++) {
    for (let col = 0; col < 8; col++) {
      const name = files[col] + "12345678"[row];
      const tile = new THREE.Mesh(new THREE.BoxGeometry(46, 46, 0.6), (col + row) % 2 === 0 ? dark : light);
      tile.position.set(75 + col * 50, 75 + row * 50, 22.4);
      tile.receiveShadow = true;
      squares.add(tile);

      const pick = new THREE.Mesh(new THREE.BoxGeometry(48, 48, 4), pickMat);
      pick.position.set(75 + col * 50, 75 + row * 50, 24);
      pick.userData.square = name;
      squares.add(pick);
    }
  }

  return { group, squares };
}
