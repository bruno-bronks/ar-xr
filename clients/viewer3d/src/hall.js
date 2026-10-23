// Galpao industrial PROCEDURAL: piso de concreto, paredes de chapa, colunas, tubulacoes e luzes.
import * as THREE from "three";
import { RoundedBoxGeometry } from "three/addons/geometries/RoundedBoxGeometry.js";
import * as M from "./materials.js";

function mesh(geometry, material, { cast = true, receive = true } = {}) {
  const node = new THREE.Mesh(geometry, material);
  node.castShadow = cast;
  node.receiveShadow = receive;
  return node;
}

// `mapW` x `mapD` metros = a area da planta 2D (as zonas em % se aplicam a ela).
export function buildHall(scene, { zones, mapW, mapD }) {
  const hall = new THREE.Group();
  const floorW = mapW + 8;
  const floorD = mapD + 8;
  const wallZ = -(mapD / 2 + 2.2);
  const wallH = 7;

  // piso
  const c = M.concrete();
  const floor = mesh(
    new THREE.PlaneGeometry(floorW, floorD),
    new THREE.MeshStandardMaterial({ ...c, color: 0xa9abae, roughness: 1, metalness: 0, bumpScale: 1.4 }),
    { cast: false },
  );
  floor.rotation.x = -Math.PI / 2;
  hall.add(floor);

  // faixas e rotulos de zona (decal por cima do piso)
  const decal = mesh(
    new THREE.PlaneGeometry(mapW, mapD),
    new THREE.MeshStandardMaterial({
      map: M.floorDecals(zones, mapW, mapD),
      transparent: true,
      roughness: 0.55,
      metalness: 0,
      depthWrite: false,
      polygonOffset: true,
      polygonOffsetFactor: -2,
    }),
    { cast: false },
  );
  decal.rotation.x = -Math.PI / 2;
  decal.position.y = 0.004;
  hall.add(decal);

  // parede de fundo e laterais (chapa corrugada + rodape de concreto)
  const wallTex = M.corrugated(Math.round(floorW / 0.9));
  const wallMaterial = new THREE.MeshStandardMaterial({ ...wallTex, color: 0xcdd3da, roughness: 0.55, metalness: 0.65, bumpScale: 2.2 });
  const back = mesh(new THREE.BoxGeometry(floorW, wallH, 0.3), wallMaterial);
  back.position.set(0, wallH / 2, wallZ);
  hall.add(back);
  const sideTex = M.corrugated(Math.round(floorD / 0.9));
  const sideMaterial = new THREE.MeshStandardMaterial({ ...sideTex, color: 0xcdd3da, roughness: 0.55, metalness: 0.65, bumpScale: 2.2 });
  for (const sign of [-1, 1]) {
    const side = mesh(new THREE.BoxGeometry(0.3, wallH, floorD), sideMaterial);
    side.position.set(sign * (floorW / 2), wallH / 2, 0);
    hall.add(side);
  }
  const plinthMaterial = new THREE.MeshStandardMaterial({ color: 0x7b7e82, roughness: 0.9, metalness: 0 });
  const plinth = mesh(new THREE.BoxGeometry(floorW, 1.1, 0.36), plinthMaterial);
  plinth.position.set(0, 0.55, wallZ + 0.04);
  hall.add(plinth);

  // colunas em H com base de aviso
  const steel = new THREE.MeshStandardMaterial({ color: 0x5d6b7b, metalness: 0.8, roughness: 0.42 });
  const stripes = new THREE.MeshStandardMaterial({ map: M.hazardStripes(), roughness: 0.6, metalness: 0.1 });
  const columnCount = 5;
  for (let i = 0; i < columnCount; i += 1) {
    const x = -floorW / 2 + 2.2 + (i * (floorW - 4.4)) / (columnCount - 1);
    const column = new THREE.Group();
    column.add(mesh(new RoundedBoxGeometry(0.34, wallH, 0.04, 2, 0.01), steel)); // alma
    for (const dx of [-0.17, 0.17]) {
      const flange = mesh(new RoundedBoxGeometry(0.04, wallH, 0.3, 2, 0.01), steel); // mesas
      flange.position.x = dx;
      column.add(flange);
    }
    const plate = mesh(new RoundedBoxGeometry(0.62, 0.05, 0.62, 2, 0.01), steel);
    plate.position.y = -wallH / 2 + 0.025;
    column.add(plate);
    const guard = mesh(new THREE.BoxGeometry(0.4, 1.1, 0.4), stripes);
    guard.position.y = -wallH / 2 + 0.55 + 0.05;
    column.add(guard);
    column.position.set(x, wallH / 2, wallZ + 0.42);
    hall.add(column);
  }

  // tubulacoes ao longo da parede de fundo (agua, ar, gas) com suportes
  const pipeColors = [0x2f6fbf, 0x2ea36a, 0xd9a21b];
  pipeColors.forEach((color, index) => {
    const y = 3.4 + index * 0.52;
    const pipe = mesh(
      new THREE.CylinderGeometry(0.11, 0.11, floorW - 0.4, 40),
      new THREE.MeshStandardMaterial({ color, metalness: 0.5, roughness: 0.36 }),
    );
    pipe.rotation.z = Math.PI / 2;
    pipe.position.set(0, y, wallZ + 0.4);
    hall.add(pipe);
    for (let x = -floorW / 2 + 1.5; x < floorW / 2; x += 3) {
      const bracket = mesh(new RoundedBoxGeometry(0.06, 0.34, 0.22, 2, 0.01), steel);
      bracket.position.set(x, y - 0.1, wallZ + 0.3);
      hall.add(bracket);
    }
  });

  // postes de protecao no limite das zonas
  const bollardGeometry = new THREE.CylinderGeometry(0.07, 0.07, 0.9, 20);
  const yellow = new THREE.MeshStandardMaterial({ color: 0xe8bb1c, roughness: 0.4, metalness: 0.2 });
  const bollards = new THREE.InstancedMesh(bollardGeometry, yellow, 14);
  bollards.castShadow = true;
  bollards.receiveShadow = true;
  const matrix = new THREE.Matrix4();
  for (let i = 0; i < 14; i += 1) {
    const x = -mapW / 2 + 1 + (i * (mapW - 2)) / 13;
    matrix.makeTranslation(x, 0.45, mapD / 2 - 0.35);
    bollards.setMatrixAt(i, matrix);
  }
  hall.add(bollards);

  // luzes: "sol" de clarabóia + preenchimento hemisferico fraco
  const key = new THREE.DirectionalLight(0xfff1de, 2.1);
  key.position.set(7, 16, 9);
  key.castShadow = true;
  key.shadow.mapSize.set(2048, 2048);
  key.shadow.camera.left = -16;
  key.shadow.camera.right = 16;
  key.shadow.camera.top = 12;
  key.shadow.camera.bottom = -12;
  key.shadow.camera.near = 1;
  key.shadow.camera.far = 40;
  key.shadow.bias = -0.0003;
  key.shadow.normalBias = 0.025;
  key.shadow.radius = 4;
  key.target.position.set(0, 0, 0);
  hall.add(key, key.target);
  const fill = new THREE.HemisphereLight(0xdfe8ff, 0x4a4036, 0.35);
  hall.add(fill);

  scene.add(hall);
  return { hall, key, floorW, floorD, wallZ };
}
