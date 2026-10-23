// Modelos PROCEDURAIS dos equipamentos do seed (compressor, bomba, motor). Escala em metros.
// Sao representacoes ilustrativas de TIPOS de maquina; nao ha CAD, medidas nem especificacao real.
import * as THREE from "three";
import { RoundedBoxGeometry } from "three/addons/geometries/RoundedBoxGeometry.js";
import * as M from "./materials.js";

const TAU = Math.PI * 2;

function put(geometry, material, { cast = true, receive = true } = {}) {
  const node = new THREE.Mesh(geometry, material);
  node.castShadow = cast;
  node.receiveShadow = receive;
  return node;
}

function rbox(w, h, d, material, radius = 0.012) {
  return put(new RoundedBoxGeometry(w, h, d, 4, Math.min(radius, w / 2, h / 2, d / 2)), material);
}

function cyl(rTop, rBottom, height, material, segments = 64) {
  return put(new THREE.CylinderGeometry(rTop, rBottom, height, segments, 1), material);
}

function at(node, x, y, z) {
  node.position.set(x, y, z);
  return node;
}

// Cilindro com o eixo ao longo de X (a geometria padrao e ao longo de Y).
function cylX(rTop, rBottom, length, material, segments = 64) {
  const node = cyl(rTop, rBottom, length, material, segments);
  node.rotation.z = Math.PI / 2;
  return node;
}

function tube(points, radius, material, segments = 96) {
  const curve = new THREE.CatmullRomCurve3(points.map((p) => new THREE.Vector3(...p)), false, "catmullrom", 0.05);
  return put(new THREE.TubeGeometry(curve, segments, radius, 20, false), material);
}

// Carcaca aletada ao longo de X: corpo + aletas instanciadas em volta.
function finnedBody({ radius, length, fins, finDepth, finThickness, bodyMaterial, finMaterial }) {
  const group = new THREE.Group();
  group.add(cylX(radius, radius, length, bodyMaterial, 72));
  const geometry = new RoundedBoxGeometry(length * 0.96, finDepth, finThickness, 2, finThickness * 0.4);
  const instanced = new THREE.InstancedMesh(geometry, finMaterial, fins);
  instanced.castShadow = true;
  instanced.receiveShadow = true;
  const matrix = new THREE.Matrix4();
  const quaternion = new THREE.Quaternion();
  const position = new THREE.Vector3();
  const one = new THREE.Vector3(1, 1, 1);
  for (let i = 0; i < fins; i += 1) {
    const a = (i / fins) * TAU;
    quaternion.setFromAxisAngle(new THREE.Vector3(1, 0, 0), a);
    position.set(0, Math.cos(a) * (radius + finDepth / 2 - 0.004), Math.sin(a) * (radius + finDepth / 2 - 0.004));
    matrix.compose(position, quaternion, one);
    instanced.setMatrixAt(i, matrix);
  }
  group.add(instanced);
  return group;
}

// Anel de parafusos num disco (flange): eixo ao longo de Y.
function boltRing(radius, count, boltRadius, height, material) {
  const group = new THREE.Group();
  const geometry = new THREE.CylinderGeometry(boltRadius, boltRadius, height, 6);
  const instanced = new THREE.InstancedMesh(geometry, material, count);
  instanced.castShadow = true;
  const matrix = new THREE.Matrix4();
  for (let i = 0; i < count; i += 1) {
    const a = (i / count) * TAU;
    matrix.makeTranslation(Math.cos(a) * radius, 0, Math.sin(a) * radius);
    instanced.setMatrixAt(i, matrix);
  }
  group.add(instanced);
  return group;
}

// Flange com parafusos; `axis`: "y" (padrao) ou "x".
function flange(radius, thickness, steel, bolts, axis = "y") {
  const group = new THREE.Group();
  group.add(cyl(radius, radius, thickness, steel, 56));
  const ring = boltRing(radius * 0.78, bolts, radius * 0.07, thickness * 1.5, M.darkSteel());
  group.add(ring);
  if (axis === "x") group.rotation.z = Math.PI / 2;
  return group;
}

// Pe de montagem com parafuso de ancoragem.
function foot(w, h, d, paintMaterial, steel) {
  const group = new THREE.Group();
  group.add(rbox(w, h, d, paintMaterial, 0.01));
  const bolt = cyl(0.014, 0.014, h + 0.02, steel, 6);
  bolt.position.y = 0.004;
  group.add(bolt);
  return group;
}

function gauge(faceTexture) {
  const group = new THREE.Group();
  group.add(at(cyl(0.075, 0.075, 0.045, M.steel(), 48), 0, 0, 0));
  group.children[0].rotation.x = Math.PI / 2;
  const face = put(new THREE.CircleGeometry(0.066, 48), new THREE.MeshStandardMaterial({ map: faceTexture, color: 0x8a8a86, roughness: 0.85, metalness: 0 }), { cast: false });
  face.position.z = 0.0235;
  group.add(face);
  const lens = put(new THREE.CircleGeometry(0.066, 48), M.glass(), { cast: false, receive: false });
  lens.position.z = 0.0245;
  group.add(lens);
  const bezel = put(new THREE.TorusGeometry(0.07, 0.007, 14, 48), M.brass());
  bezel.position.z = 0.0225;
  group.add(bezel);
  return group;
}

function nameplate(line1, line2, w = 0.26, h = 0.13) {
  const plate = put(new THREE.PlaneGeometry(w, h), new THREE.MeshStandardMaterial({ map: M.namePlate(line1, line2), roughness: 0.5, metalness: 0.6 }), {
    cast: false,
  });
  return plate;
}

// ---- sinalizador luminoso (torre de 3 cores) -----------------------------------------------------
export function beacon(poleHeight) {
  const group = new THREE.Group();
  group.add(at(cyl(0.09, 0.1, 0.03, M.darkSteel(), 32), 0, 0.015, 0));
  const pole = at(cyl(0.028, 0.028, poleHeight, M.darkSteel(), 16), 0, 0.03 + poleHeight / 2, 0);
  group.add(pole);
  const lenses = {};
  const colors = { green: 0x19c96b, amber: 0xffb400, red: 0xff2a2a };
  let y = 0.03 + poleHeight;
  for (const key of ["green", "amber", "red"]) {
    const material = new THREE.MeshStandardMaterial({
      color: colors[key],
      emissive: colors[key],
      emissiveIntensity: 0,
      roughness: 0.25,
      metalness: 0,
      transparent: true,
      opacity: 0.94,
    });
    const lens = put(new THREE.CylinderGeometry(0.085, 0.085, 0.11, 40), material, { cast: false });
    lens.position.y = y + 0.055;
    lens.userData.lens = key;
    group.add(lens);
    const band = cyl(0.09, 0.09, 0.012, M.darkSteel(), 40);
    band.position.y = y;
    group.add(band);
    lenses[key] = lens;
    y += 0.12;
  }
  group.add(at(cyl(0.07, 0.09, 0.04, M.darkSteel(), 40), 0, y + 0.02, 0));
  const light = new THREE.PointLight(0xffffff, 0, 3.2, 1.6);
  light.position.y = y;
  group.add(light);
  return { group, lenses, light, topY: y + 0.08 };
}

// ---- EQ-001: compressor de ar com reservatorio -----------------------------------------------------
export function compressor() {
  const root = new THREE.Group();
  const blue = M.paint(0x2455a4, { metalness: 0.4, roughness: 0.32 });
  const grey = M.paint(0xd7dbe0, { metalness: 0.2, roughness: 0.4 });
  const steel = M.steel();
  const dark = M.darkSteel();

  // skid de aco
  const skid = M.paint(0x2b2f35, { metalness: 0.6, roughness: 0.5, clearcoat: 0.2 });
  for (const z of [-0.5, 0.5]) root.add(at(rbox(2.5, 0.12, 0.12, skid, 0.015), 0, 0.06, z));
  for (const x of [-1.05, 0, 1.05]) root.add(at(rbox(0.1, 0.1, 1.12, skid, 0.012), x, 0.06, 0));
  for (const x of [-1.15, 1.15]) for (const z of [-0.5, 0.5]) root.add(at(foot(0.18, 0.02, 0.18, skid, steel), x, 0.01, z));

  // reservatorio: casco cilindrico com calotas elipticas (Lathe), eixo ao longo de X
  const L = 1.7;
  const R = 0.42;
  const cap = 0.2;
  const profile = [];
  for (let k = 0; k <= 24; k += 1) {
    const t = (k / 24) * (Math.PI / 2);
    profile.push(new THREE.Vector2(R * Math.sin(t), -L / 2 - cap * Math.cos(t)));
  }
  profile.push(new THREE.Vector2(R, L / 2));
  for (let k = 0; k <= 24; k += 1) {
    const t = (k / 24) * (Math.PI / 2);
    profile.push(new THREE.Vector2(R * Math.cos(t), L / 2 + cap * Math.sin(t)));
  }
  const tank = put(new THREE.LatheGeometry(profile, 96), blue);
  tank.rotation.z = Math.PI / 2;
  const tankY = 0.12 + 0.17 + R - 0.02;
  tank.position.y = tankY;
  root.add(tank);
  for (const x of [-L / 2, L / 2]) {
    const seam = put(new THREE.TorusGeometry(R + 0.002, 0.006, 12, 96), M.darkSteel());
    seam.rotation.y = Math.PI / 2;
    seam.position.set(x, tankY, 0);
    root.add(seam);
  }
  for (const x of [-0.55, 0.55]) {
    const saddle = rbox(0.16, 0.2, 0.62, dark, 0.02);
    saddle.position.set(x, 0.12 + 0.07, 0);
    root.add(saddle);
  }
  const strapTop = tankY + R;

  // placa de montagem + motor + cabecote
  root.add(at(rbox(1.3, 0.045, 0.56, M.paint(0x2b2f35, { metalness: 0.6, roughness: 0.5 }), 0.012), 0.05, strapTop + 0.02, 0));
  const motor = finnedBody({ radius: 0.17, length: 0.55, fins: 28, finDepth: 0.03, finThickness: 0.008, bodyMaterial: grey, finMaterial: grey });
  motor.position.set(-0.36, strapTop + 0.24, 0);
  root.add(motor);
  for (const dx of [-0.5, -0.2]) root.add(at(rbox(0.12, 0.05, 0.3, dark, 0.01), dx, strapTop + 0.07, 0));
  root.add(at(rbox(0.16, 0.1, 0.16, grey, 0.02), -0.36, strapTop + 0.45, 0));
  root.add(at(cylX(0.18, 0.17, 0.12, dark, 56), -0.69, strapTop + 0.24, 0));

  const head = new THREE.Group();
  head.add(at(rbox(0.5, 0.22, 0.34, blue, 0.03), 0, 0.11, 0));
  for (const dx of [-0.14, 0.14]) {
    const cylinder = cyl(0.085, 0.085, 0.3, grey, 48);
    cylinder.position.set(dx, 0.37, 0);
    head.add(cylinder);
    for (let i = 0; i < 9; i += 1) {
      const disc = cyl(0.115, 0.115, 0.012, grey, 48);
      disc.position.set(dx, 0.25 + i * 0.03, 0);
      head.add(disc);
    }
    head.add(at(cyl(0.1, 0.1, 0.04, dark, 48), dx, 0.55, 0));
  }
  head.position.set(0.45, strapTop + 0.04, 0);
  root.add(head);

  // protecao de correia perfurada
  const guardMaterial = new THREE.MeshStandardMaterial({ color: 0xe0b020, metalness: 0.4, roughness: 0.5, alphaMap: M.perforated(14, 10), alphaTest: 0.5, side: THREE.DoubleSide });
  const guard = put(new THREE.BoxGeometry(0.74, 0.34, 0.02), guardMaterial);
  guard.position.set(0.08, strapTop + 0.26, 0.26);
  root.add(guard);

  // manometro com haste no topo do reservatorio
  root.add(at(cyl(0.012, 0.012, 0.16, steel, 16), 0.72, strapTop + 0.1, 0.1));
  const g = gauge(M.gaugeFace());
  g.position.set(0.72, strapTop + 0.24, 0.12);
  g.rotation.x = -0.25;
  root.add(g);

  // tubulacao de saida com valvula
  root.add(
    tube(
      [
        [0.45, strapTop + 0.62, 0],
        [0.85, strapTop + 0.74, 0.0],
        [1.25, strapTop + 0.6, 0.12],
        [1.3, 0.55, 0.3],
        [1.3, 0.24, 0.3],
      ],
      0.028,
      steel,
    ),
  );
  const valve = new THREE.Group();
  valve.add(put(new THREE.SphereGeometry(0.06, 32, 24), M.brass()));
  valve.add(at(cyl(0.012, 0.012, 0.16, steel, 12), 0, 0.12, 0));
  valve.add(at(rbox(0.16, 0.025, 0.03, M.paint(0xc0392b, { metalness: 0.1, roughness: 0.5 }), 0.008), 0, 0.2, 0));
  valve.position.set(1.3, 0.4, 0.3);
  root.add(valve);
  const out = flange(0.07, 0.03, steel, 6);
  out.position.set(1.3, 0.2, 0.3);
  root.add(out);

  // filtro de ar + dreno
  root.add(at(cyl(0.07, 0.07, 0.3, grey, 40), 0.18, strapTop + 0.19, -0.12));
  root.add(at(cyl(0.012, 0.012, 0.1, M.brass(), 12), -0.7, 0.23, 0.34));
  root.add(at(put(new THREE.SphereGeometry(0.03, 20, 16), M.brass()), -0.7, 0.2, 0.34));

  // placa de identificacao (nao e dado real)
  const plate = nameplate("COMPRESSOR", "EQ-001 · DEMO");
  plate.position.set(0.1, tankY + 0.05, R + 0.004);
  root.add(plate);

  return finish(root, { id: "EQ-001", poleHeight: 1.7, poleAt: [-1.1, 0, 0.62], radius: 1.9, topY: strapTop + 1.0 });
}

// ---- EQ-002: bomba centrifuga horizontal ------------------------------------------------------------
export function pump() {
  const root = new THREE.Group();
  const casing = M.paint(0x31363d, { metalness: 0.6, roughness: 0.55, clearcoat: 0.25 });
  const motorPaint = M.paint(0x4c76b0, { metalness: 0.4, roughness: 0.34 });
  const base = M.paint(0x2b2f35, { metalness: 0.6, roughness: 0.5, clearcoat: 0.2 });
  const steel = M.steel();
  const dark = M.darkSteel();

  // bloco de concreto + base metalica
  root.add(at(rbox(2.0, 0.08, 0.86, new THREE.MeshStandardMaterial({ color: 0x8a8d90, roughness: 0.95, metalness: 0 }), 0.01), 0, 0.04, 0));
  root.add(at(rbox(1.9, 0.08, 0.74, base, 0.014), 0, 0.12, 0));
  for (const x of [-0.82, 0.82]) for (const z of [-0.31, 0.31]) root.add(at(cyl(0.022, 0.022, 0.05, dark, 6), x, 0.185, z));

  // motor eletrico
  const motor = finnedBody({ radius: 0.21, length: 0.78, fins: 32, finDepth: 0.035, finThickness: 0.009, bodyMaterial: motorPaint, finMaterial: motorPaint });
  motor.position.set(-0.4, 0.16 + 0.21 + 0.06, 0);
  root.add(motor);
  for (const dx of [-0.65, -0.2]) root.add(at(rbox(0.16, 0.06, 0.4, base, 0.012), dx, 0.19, 0));
  const cover = cylX(0.215, 0.205, 0.2, dark, 56);
  cover.position.set(-0.84, 0.43, 0);
  root.add(cover);
  const grille = put(
    new THREE.CircleGeometry(0.205, 56),
    new THREE.MeshStandardMaterial({ color: 0x20242a, metalness: 0.7, roughness: 0.5, alphaMap: M.perforated(10, 10), alphaTest: 0.5, side: THREE.DoubleSide }),
  );
  grille.rotation.y = -Math.PI / 2;
  grille.position.set(-0.945, 0.43, 0);
  root.add(grille);
  root.add(at(rbox(0.2, 0.12, 0.2, motorPaint, 0.02), -0.42, 0.7, 0));
  root.add(at(rbox(0.205, 0.012, 0.205, dark, 0.004), -0.42, 0.765, 0));

  // eixo + protecao do acoplamento (meio cilindro amarelo)
  root.add(at(cylX(0.035, 0.035, 0.36, steel, 32), 0.08, 0.43, 0));
  const guardGeometry = new THREE.CylinderGeometry(0.115, 0.115, 0.36, 40, 1, true, -Math.PI / 2, Math.PI);
  const guard = put(guardGeometry, new THREE.MeshStandardMaterial({ color: 0xe0b020, roughness: 0.5, metalness: 0.4, side: THREE.DoubleSide }));
  guard.rotation.set(0, 0, Math.PI / 2);
  guard.position.set(0.08, 0.43, 0);
  guard.rotation.order = "XYZ";
  guard.rotation.x = Math.PI / 2;
  root.add(guard);

  // corpo da bomba: suporte de mancal + voluta + bocais
  root.add(at(cylX(0.105, 0.12, 0.3, casing, 40), 0.32, 0.43, 0));
  const volute = put(new THREE.CylinderGeometry(0.29, 0.29, 0.22, 72), casing);
  volute.rotation.z = Math.PI / 2;
  volute.position.set(0.58, 0.43, 0);
  root.add(volute);
  const frontCover = put(new THREE.CylinderGeometry(0.265, 0.265, 0.06, 72), casing);
  frontCover.rotation.z = Math.PI / 2;
  frontCover.position.set(0.72, 0.43, 0);
  root.add(frontCover);
  const bolts = boltRing(0.235, 10, 0.014, 0.05, dark);
  bolts.rotation.z = Math.PI / 2;
  bolts.position.set(0.745, 0.43, 0);
  root.add(bolts);
  root.add(at(cylX(0.1, 0.1, 0.34, casing, 40), 0.9, 0.43, 0));
  const suctionFlange = flange(0.14, 0.04, steel, 8, "x");
  suctionFlange.position.set(1.09, 0.43, 0);
  root.add(suctionFlange);
  root.add(at(cyl(0.075, 0.075, 0.33, casing, 40), 0.55, 0.43 + 0.29 + 0.1, 0));
  const dischargeFlange = flange(0.12, 0.04, steel, 8, "y");
  dischargeFlange.position.set(0.55, 0.43 + 0.29 + 0.285, 0);
  root.add(dischargeFlange);
  root.add(at(rbox(0.3, 0.09, 0.34, casing, 0.014), 0.58, 0.19, 0));

  // tubulacoes
  root.add(
    tube(
      [
        [1.12, 0.43, 0],
        [1.55, 0.43, 0],
        [1.85, 0.3, 0.08],
        [1.9, 0.0, 0.1],
      ],
      0.095,
      M.paint(0x6b7c8f, { metalness: 0.5, roughness: 0.45 }),
    ),
  );
  root.add(
    tube(
      [
        [0.55, 1.03, 0],
        [0.55, 1.45, 0],
        [0.85, 1.68, 0],
        [1.5, 1.7, -0.05],
        [1.9, 1.6, -0.1],
      ],
      0.07,
      M.paint(0x6b7c8f, { metalness: 0.5, roughness: 0.45 }),
    ),
  );
  const g = gauge(M.gaugeFace());
  g.position.set(0.55, 1.2, 0.17);
  root.add(g);
  root.add(at(cyl(0.012, 0.012, 0.12, steel, 12), 0.55, 1.12, 0.09));
  root.children[root.children.length - 1].rotation.x = Math.PI / 2;

  const plate = nameplate("BOMBA CENTRIFUGA", "EQ-002 · DEMO", 0.24, 0.12);
  plate.position.set(-0.4, 0.5, 0.215);
  root.add(plate);

  return finish(root, { id: "EQ-002", poleHeight: 1.55, poleAt: [-0.85, 0, 0.45], radius: 1.7, topY: 1.8 });
}

// ---- EQ-003: motor eletrico trifasico em trilhos -----------------------------------------------------
export function motor() {
  const root = new THREE.Group();
  const paint = M.paint(0x5b6f86, { metalness: 0.45, roughness: 0.33 });
  const steel = M.steel();
  const dark = M.darkSteel();
  const base = M.paint(0x2b2f35, { metalness: 0.6, roughness: 0.5, clearcoat: 0.2 });

  for (const z of [-0.36, 0.36]) {
    root.add(at(rbox(1.7, 0.1, 0.12, base, 0.012), 0, 0.05, z));
    for (const x of [-0.7, 0.7]) root.add(at(cyl(0.02, 0.02, 0.06, steel, 6), x, 0.12, z));
  }
  root.add(at(rbox(0.1, 0.08, 0.84, base, 0.01), -0.7, 0.05, 0));
  root.add(at(rbox(0.1, 0.08, 0.84, base, 0.01), 0.7, 0.05, 0));

  const centerY = 0.1 + 0.07 + 0.34;
  const body = finnedBody({ radius: 0.34, length: 1.1, fins: 48, finDepth: 0.045, finThickness: 0.011, bodyMaterial: paint, finMaterial: paint });
  body.position.set(0, centerY, 0);
  root.add(body);
  for (const x of [-0.42, 0.42]) {
    root.add(at(cylX(0.355, 0.355, 0.13, paint, 72), x * 1.32, centerY, 0));
  }
  for (const x of [-0.4, 0.4]) for (const z of [-0.3, 0.3]) root.add(at(foot(0.2, 0.07, 0.16, paint, steel), x, 0.1 + 0.035, z));
  const fan = cylX(0.37, 0.355, 0.26, dark, 72);
  fan.position.set(-0.66, centerY, 0);
  root.add(fan);
  const grille = put(
    new THREE.CircleGeometry(0.355, 64),
    new THREE.MeshStandardMaterial({ color: 0x1f2328, metalness: 0.7, roughness: 0.5, alphaMap: M.perforated(14, 14), alphaTest: 0.5, side: THREE.DoubleSide }),
  );
  grille.rotation.y = -Math.PI / 2;
  grille.position.set(-0.795, centerY, 0);
  root.add(grille);

  root.add(at(cylX(0.1, 0.1, 0.1, steel, 40), 0.63, centerY, 0));
  root.add(at(cylX(0.052, 0.052, 0.42, steel, 40), 0.84, centerY, 0));
  root.add(at(rbox(0.16, 0.015, 0.028, dark, 0.004), 0.9, centerY + 0.05, 0));

  const box = rbox(0.34, 0.22, 0.28, paint, 0.022);
  box.position.set(0.05, centerY + 0.34 + 0.12, 0);
  root.add(box);
  root.add(at(rbox(0.35, 0.02, 0.29, dark, 0.006), 0.05, centerY + 0.34 + 0.24, 0));
  const lid = boltRing(0.1, 4, 0.012, 0.03, steel);
  lid.position.set(0.05, centerY + 0.34 + 0.26, 0);
  root.add(lid);
  root.add(
    tube(
      [
        [0.2, centerY + 0.5, 0.0],
        [0.32, centerY + 0.42, 0.16],
        [0.34, 0.45, 0.4],
        [0.34, 0.1, 0.44],
      ],
      0.026,
      M.paint(0x1d1f22, { metalness: 0.2, roughness: 0.7, clearcoat: 0.1 }),
    ),
  );
  const eye = put(new THREE.TorusGeometry(0.04, 0.009, 12, 28), steel);
  eye.rotation.y = Math.PI / 2;
  eye.position.set(0.32, centerY + 0.4, 0);
  root.add(eye);
  const plate = nameplate("MOTOR ELÉTRICO", "EQ-003 · DEMO", 0.3, 0.15);
  plate.position.set(-0.1, centerY + 0.05, 0.345);
  root.add(plate);

  return finish(root, { id: "EQ-003", poleHeight: 1.45, poleAt: [-0.88, 0, 0.5], radius: 1.55, topY: centerY + 0.95 });
}

// Anexa sinalizador + anel de estado no piso e etiqueta a cadeia de malhas com o id (picking).
function finish(root, { id, poleHeight, poleAt, radius, topY }) {
  const lamp = beacon(poleHeight);
  lamp.group.position.set(...poleAt);
  root.add(lamp.group);
  const ring = put(
    new THREE.RingGeometry(radius - 0.07, radius, 128),
    new THREE.MeshStandardMaterial({ color: 0x6b7785, emissive: 0x6b7785, emissiveIntensity: 0.9, roughness: 0.6, metalness: 0, transparent: true, opacity: 0.95 }),
    { cast: false },
  );
  ring.rotation.x = -Math.PI / 2;
  ring.position.y = 0.014;
  root.add(ring);
  root.traverse((node) => {
    node.userData.machineId = id;
  });
  return { id, group: root, lamp, ring, radius, topY };
}

// Equipamento de tipo desconhecido: unidade generica sobre skid (nunca finge ser outra maquina).
export function generic(id) {
  const root = new THREE.Group();
  const body = M.paint(0x7a8794, { metalness: 0.4, roughness: 0.4 });
  const base = M.paint(0x2b2f35, { metalness: 0.6, roughness: 0.5, clearcoat: 0.2 });
  root.add(at(rbox(1.5, 0.1, 0.9, base, 0.014), 0, 0.05, 0));
  root.add(at(rbox(1.2, 0.8, 0.7, body, 0.05), 0, 0.5, 0));
  root.add(at(cyl(0.16, 0.16, 0.25, M.steel(), 40), 0.3, 1.02, 0));
  const plate = nameplate("EQUIPAMENTO", id + " · DEMO");
  plate.position.set(0, 0.55, 0.352);
  root.add(plate);
  return finish(root, { id, poleHeight: 1.3, poleAt: [-0.65, 0, 0.5], radius: 1.4, topY: 1.4 });
}

// Escolhe o modelo pelo TIPO cadastrado (texto), nao pelo id.
export function modelFor(equipment) {
  const type = String(equipment.type || "").toLowerCase();
  if (type.includes("compressor")) return compressor();
  if (type.includes("bomba")) return pump();
  if (type.includes("motor")) return motor();
  return generic(equipment.id);
}
