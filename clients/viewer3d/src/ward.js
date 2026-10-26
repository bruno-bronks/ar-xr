// Vista 3D das alas (UTI/enfermaria) — REQ-UX-005. Sala hospitalar PROCEDURAL e ILUSTRATIVA: nao e a planta real.
// Cena SEM pessoas e SEM dado clinico: o estado do leito e o OPERACIONAL por regra (alarmes, chamada, limpeza,
// offline), vindo da API (/api/v1/hacc). Todo texto da API entra via textContent / canvas (nunca HTML).
import * as THREE from "three";
import { RoundedBoxGeometry } from "three/addons/geometries/RoundedBoxGeometry.js";
import { CSS2DObject } from "three/addons/renderers/CSS2DRenderer.js";
import * as M from "./materials.js";
import { LENS_COLOR, Viewer } from "./viewer.js";

const CELL_W = 3.6; // metros por coluna da grade da ala
const CELL_D = 4.4; // metros por linha
const WALL_H = 3.1;
const BED_STATUS_COLOR = { NORMAL: 0x1fa85a, ATTENTION: 0xe0a21a, ALERT: 0xe5383b, BLOCKED: 0xc4622d, OFFLINE: 0x6b7785, UNKNOWN: 0x8c6fe0 };
const BED_LENS = { NORMAL: "green", ATTENTION: "amber", ALERT: "red" };

function put(geometry, material, { cast = true, receive = true } = {}) {
  const node = new THREE.Mesh(geometry, material);
  node.castShadow = cast;
  node.receiveShadow = receive;
  return node;
}
const rbox = (w, h, d, material, r = 0.012) => put(new RoundedBoxGeometry(w, h, d, 3, Math.min(r, w / 2, h / 2, d / 2)), material);
const cyl = (rt, rb, h, material, seg = 40) => put(new THREE.CylinderGeometry(rt, rb, h, seg), material);
const at = (node, x, y, z) => {
  node.position.set(x, y, z);
  return node;
};
const led = (color) =>
  new THREE.MeshStandardMaterial({ color: 0x2a2d31, emissive: color, emissiveIntensity: 0, roughness: 0.3, metalness: 0 });

// ---- lampada de parede (sinalizador de chamada) -----------------------------------------------------------
function wallLamp() {
  const group = new THREE.Group();
  const lenses = {};
  const colors = { green: LENS_COLOR.green, amber: LENS_COLOR.amber, red: LENS_COLOR.red };
  group.add(at(rbox(0.16, 0.5, 0.06, M.darkSteel(), 0.02), 0, 0.25, 0));
  let y = 0.08;
  for (const key of ["green", "amber", "red"]) {
    const material = new THREE.MeshStandardMaterial({ color: 0x2a2d31, emissive: colors[key], emissiveIntensity: 0, roughness: 0.25 });
    const lens = put(new THREE.SphereGeometry(0.052, 28, 20), material, { cast: false });
    lens.position.set(0, y, 0.045);
    group.add(lens);
    lenses[key] = lens;
    y += 0.14;
  }
  const light = new THREE.PointLight(0xffffff, 0, 2.6, 1.8);
  light.position.set(0, 0.25, 0.4);
  group.add(light);
  return { group, lenses, light };
}

// ---- leito hospitalar (sem paciente): cabeceira em -Z, pes em +Z ---------------------------------------------------
function buildBed(label, occupied) {
  const root = new THREE.Group();
  const steel = M.steel();
  const dark = M.darkSteel();
  const frame = M.paint(0xe9edf0, { metalness: 0.15, roughness: 0.4, clearcoat: 0.5 });
  const mattressMat = new THREE.MeshStandardMaterial({ color: 0x4a7ea0, roughness: 0.75, metalness: 0 });
  const sheet = new THREE.MeshStandardMaterial({ color: occupied ? 0xdfe9f2 : 0xf6f8fa, roughness: 0.9, metalness: 0 });
  const blanket = new THREE.MeshStandardMaterial({ color: occupied ? 0x3f78b5 : 0xcfd8de, roughness: 0.95, metalness: 0 });

  // chassi + rodizios
  root.add(at(rbox(0.92, 0.08, 1.95, frame, 0.02), 0, 0.42, 0.05));
  for (const x of [-0.4, 0.4]) {
    for (const z of [-0.72, 0.82]) {
      root.add(at(cyl(0.03, 0.03, 0.32, steel, 16), x, 0.26, z));
      const wheel = put(new THREE.CylinderGeometry(0.075, 0.075, 0.05, 28), M.rubber());
      wheel.rotation.z = Math.PI / 2;
      wheel.position.set(x, 0.075, z);
      root.add(wheel);
    }
  }
  // colchao, lencol e coberta (plana, sem forma de corpo)
  root.add(at(rbox(0.86, 0.2, 1.9, mattressMat, 0.06), 0, 0.57, 0.05));
  root.add(at(rbox(0.88, 0.035, 1.6, sheet, 0.015), 0, 0.685, 0.2));
  root.add(at(rbox(0.9, 0.05, 1.05, blanket, 0.02), 0, 0.71, 0.55));
  root.add(at(rbox(0.5, 0.1, 0.34, sheet, 0.04), 0, 0.74, -0.7)); // travesseiro
  // cabeceira e peseira
  root.add(at(rbox(0.96, 0.62, 0.06, frame, 0.02), 0, 0.82, -0.93));
  root.add(at(rbox(0.96, 0.46, 0.06, frame, 0.02), 0, 0.72, 1.03));
  // grades laterais
  for (const x of [-0.46, 0.46]) {
    for (const [y, h] of [[0.86, 0.035], [0.98, 0.035]]) root.add(at(rbox(0.035, h, 1.2, steel, 0.01), x, y, -0.2));
    for (const z of [-0.78, 0.38]) root.add(at(cyl(0.014, 0.014, 0.2, steel, 12), x, 0.9, z));
  }
  // painel de comando na peseira (so decorativo)
  root.add(at(rbox(0.32, 0.12, 0.04, dark, 0.01), 0, 0.99, 1.05));
  const bedLed = led(0xff3030);
  root.add(at(put(new THREE.SphereGeometry(0.022, 16, 12), bedLed, { cast: false }), 0.1, 0.99, 1.075));

  // coluna de cabeceira (pendant): gases, tomadas, braco do monitor
  const column = new THREE.Group();
  column.add(at(rbox(1.7, 2.3, 0.16, M.paint(0xdfe5ea, { metalness: 0.1, roughness: 0.5, clearcoat: 0.4 }), 0.03), 0, 1.15, 0));
  column.add(at(rbox(1.72, 0.1, 0.18, M.paint(0x4a7ea0, { metalness: 0.2, roughness: 0.4 }), 0.02), 0, 1.78, 0.005));
  for (const [i, color] of [[-1, 0x2aa84a], [0, 0xe0c020], [1, 0xe8e8e8]]) {
    const outlet = put(new THREE.CylinderGeometry(0.045, 0.045, 0.05, 28), new THREE.MeshStandardMaterial({ color, metalness: 0.4, roughness: 0.4 }));
    outlet.rotation.x = Math.PI / 2;
    outlet.position.set(-0.45 + i * 0.16, 1.45, 0.1);
    column.add(outlet);
  }
  for (const dx of [0.18, 0.34]) column.add(at(rbox(0.1, 0.08, 0.04, dark, 0.01), dx + 0.15, 1.45, 0.09));
  // indicadores por regra (decorativos; o texto do rotulo e a fonte de verdade)
  const leds = { iv_pump_alarm: led(0xffb400), call_button: led(0x3ab4ff), bed_exit_alarm: led(0xff3030), cleaning_due: led(0xf2f2f2) };
  Object.values(leds).forEach((material, i) =>
    column.add(at(put(new THREE.SphereGeometry(0.026, 16, 12), material, { cast: false }), 0.52 + i * 0.1, 1.62, 0.09)),
  );
  // monitor em braco articulado, em espera
  column.add(at(rbox(0.05, 0.05, 0.4, steel, 0.01), 0.5, 1.2, 0.3));
  const monitor = new THREE.Group();
  monitor.add(rbox(0.5, 0.34, 0.06, dark, 0.02));
  const screen = put(new THREE.PlaneGeometry(0.45, 0.28), new THREE.MeshStandardMaterial({ map: M.monitorScreen(label), emissive: 0xffffff, emissiveMap: M.monitorScreen(label), emissiveIntensity: 0.35, roughness: 0.4 }), { cast: false });
  screen.position.z = 0.032;
  monitor.add(screen);
  monitor.position.set(0.5, 1.22, 0.52);
  monitor.rotation.y = -0.25;
  column.add(monitor);
  column.position.set(0, 0, -1.28);

  // suporte de soro com bomba de infusao (LED reflete a regra iv_pump_alarm)
  const pole = new THREE.Group();
  pole.add(at(cyl(0.02, 0.02, 1.95, steel, 16), 0, 0.98, 0));
  for (let a = 0; a < 5; a += 1) {
    const leg = rbox(0.36, 0.025, 0.04, steel, 0.008);
    leg.rotation.y = (a / 5) * Math.PI * 2;
    leg.position.y = 0.05;
    pole.add(leg);
  }
  pole.add(at(rbox(0.3, 0.025, 0.025, steel, 0.008), 0, 1.95, 0));
  const pump = rbox(0.24, 0.3, 0.2, M.paint(0xf0f2f4, { metalness: 0.1, roughness: 0.45 }), 0.03);
  pump.position.set(0.0, 1.35, 0.12);
  pole.add(pump);
  pole.add(at(rbox(0.16, 0.1, 0.012, new THREE.MeshStandardMaterial({ color: 0x0c1c24, emissive: 0x2a7090, emissiveIntensity: 0.3 }), 0.004), 0, 1.4, 0.226));
  const pumpLed = led(0xffb400);
  pole.add(at(put(new THREE.SphereGeometry(0.02, 14, 10), pumpLed, { cast: false }), 0.08, 1.28, 0.226));
  const bag = put(new THREE.CapsuleGeometry(0.07, 0.14, 8, 16), new THREE.MeshPhysicalMaterial({ color: 0xcfe6f2, transparent: true, opacity: 0.6, roughness: 0.1, clearcoat: 1 }), { cast: false });
  bag.position.set(0, 1.78, 0);
  pole.add(bag);
  pole.position.set(0.82, 0, -0.55);

  root.add(column, pole);
  return { root, leds, bedLed, pumpLed };
}

function roomShell({ roomW, roomD }) {
  const group = new THREE.Group();
  const floorTex = M.vinylFloor();
  floorTex.map.repeat.set(roomW / 3, roomD / 3);
  floorTex.bumpMap.repeat.set(roomW / 3, roomD / 3);
  const floor = put(new THREE.PlaneGeometry(roomW + 1.2, roomD + 1.2), new THREE.MeshStandardMaterial({ ...floorTex, color: 0x9aa6a9, roughness: 0.42, metalness: 0.02, bumpScale: 0.8 }), { cast: false });
  floor.rotation.x = -Math.PI / 2;
  group.add(floor);
  const paint = new THREE.MeshStandardMaterial({ color: 0xc2ccd0, roughness: 0.85, metalness: 0 });
  const stripe = new THREE.MeshStandardMaterial({ color: 0x4a7ea0, roughness: 0.6, metalness: 0 });
  const trim = new THREE.MeshStandardMaterial({ color: 0xaab5ba, roughness: 0.7, metalness: 0 });
  const back = put(new THREE.BoxGeometry(roomW + 1.2, WALL_H, 0.2), paint);
  back.position.set(0, WALL_H / 2, -roomD / 2 - 0.1);
  group.add(back);
  group.add(at(put(new THREE.BoxGeometry(roomW + 1.2, 0.18, 0.04), stripe, { cast: false }), 0, 1.0, -roomD / 2 + 0.01));
  group.add(at(put(new THREE.BoxGeometry(roomW + 1.2, 0.12, 0.05), trim, { cast: false }), 0, 0.06, -roomD / 2 + 0.01));
  for (const sign of [-1, 1]) {
    const side = put(new THREE.BoxGeometry(0.2, WALL_H, roomD), paint);
    side.position.set(sign * (roomW / 2 + 0.1), WALL_H / 2, 0);
    group.add(side);
    group.add(at(put(new THREE.BoxGeometry(0.04, 0.18, roomD), stripe, { cast: false }), sign * (roomW / 2 - 0.01), 1.0, 0));
  }
  // porta (parede direita)
  const door = new THREE.Group();
  door.add(rbox(0.06, 2.1, 1.1, new THREE.MeshStandardMaterial({ color: 0xc9a77a, roughness: 0.6 }), 0.02));
  door.add(at(rbox(0.1, 2.2, 0.08, M.darkSteel(), 0.01), 0, 1.05, -0.58));
  door.add(at(rbox(0.1, 2.2, 0.08, M.darkSteel(), 0.01), 0, 1.05, 0.58));
  door.add(at(rbox(0.1, 0.08, 1.24, M.darkSteel(), 0.01), 0, 2.17, 0));
  door.add(at(rbox(0.1, 0.04, 0.16, M.steel(), 0.01), -0.07, 1.0, 0.4));
  const glass = put(new THREE.PlaneGeometry(0.3, 0.7), M.glass(), { cast: false, receive: false });
  glass.rotation.y = Math.PI / 2;
  glass.position.set(-0.035, 1.5, 0);
  door.add(glass);
  door.position.set(roomW / 2 - 0.05, 1.05, -roomD / 2 + 1.2);
  group.add(door);
  // posto de enfermagem (balcao + monitor + cadeira) no canto da frente
  const counter = new THREE.Group();
  counter.add(at(rbox(2.4, 1.0, 0.6, M.paint(0x6b8aa0, { metalness: 0.15, roughness: 0.5 }), 0.03), 0, 0.5, 0));
  counter.add(at(rbox(2.5, 0.06, 0.72, new THREE.MeshStandardMaterial({ color: 0xdfe3e6, roughness: 0.3 }), 0.02), 0, 1.03, 0));
  counter.add(at(rbox(0.5, 0.32, 0.04, M.darkSteel(), 0.01), -0.5, 1.28, 0.05));
  counter.add(at(rbox(0.04, 0.2, 0.04, M.steel(), 0.01), -0.5, 1.16, 0.05));
  counter.add(at(rbox(0.46, 0.28, 0.02, new THREE.MeshStandardMaterial({ color: 0x06141c, emissive: 0x1f5d78, emissiveIntensity: 0.4 }), 0.004), -0.5, 1.28, 0.075));
  counter.add(at(cyl(0.2, 0.2, 0.06, M.darkSteel(), 24), 0.55, 0.55, 0.95));
  counter.add(at(cyl(0.03, 0.03, 0.4, M.steel(), 12), 0.55, 0.3, 0.95));
  counter.add(at(rbox(0.46, 0.08, 0.44, M.rubber(), 0.03), 0.55, 0.6, 0.95));
  counter.add(at(rbox(0.46, 0.5, 0.06, M.rubber(), 0.03), 0.55, 0.86, 1.15));
  counter.position.set(-roomW / 2 + 1.7, 0, roomD / 2 - 0.5);
  group.add(counter);
  return group;
}

export class WardViewer extends Viewer {
  buildScene() {
    const group = new THREE.Group();
    const key = new THREE.DirectionalLight(0xf2f6ff, 1.25);
    key.position.set(5, 11, 9);
    key.castShadow = true;
    key.shadow.mapSize.set(2048, 2048);
    key.shadow.camera.near = 1;
    key.shadow.camera.far = 40;
    key.shadow.bias = -0.0003;
    key.shadow.normalBias = 0.025;
    key.shadow.radius = 4;
    group.add(key, key.target);
    group.add(new THREE.HemisphereLight(0xeaf2ff, 0x5a6468, 0.28));
    this.scene.add(group);
    this.scene.fog = new THREE.Fog(0x14171b, 45, 90);
    this.scene.environmentIntensity = 0.22;
    return { hall: group, key };
  }

  buildComposer() {
    super.buildComposer();
    if (this.bloom) {
      this.bloom.threshold = 2.2; // so as lentes emissivas brilham; paredes brancas nao estouram
      this.bloom.strength = 0.5;
    }
  }

  // `data` = corpo de GET /api/v1/hacc/wards/{id}/beds
  update(data) {
    const ward = data.ward;
    if (this.wardId !== ward.ward_id) this.buildRoom(ward);
    const keep = new Set(data.beds.map((b) => b.bed_id));
    let changed = false;
    for (const [id, machine] of [...this.machines]) {
      if (!keep.has(id)) {
        this.removeMachine(id, machine);
        changed = true;
      }
    }
    for (const bed of data.beds) {
      let machine = this.machines.get(bed.bed_id);
      if (!machine) {
        machine = this.addBed(bed);
        changed = true;
      }
      if (this.applyBed(machine, bed, data.evaluated_at)) changed = true;
    }
    this.renderFocusButtons(data.beds.map((b) => ({ equipment: { id: b.bed_id, name: b.label } })));
    this.container.setAttribute("data-machines", String(this.machines.size));
    this.container.setAttribute("data-ward", ward.ward_id);
    this.container.setAttribute("data-dense", String(data.beds.length > 8)); // rotulos compactos em alas grandes
    if (changed) this.dirty = true;
  }

  buildRoom(ward) {
    for (const [id, machine] of [...this.machines]) this.removeMachine(id, machine);
    this.focusKey = null;
    if (this.room) {
      this.room.traverse((node) => {
        if (node.geometry) node.geometry.dispose();
        if (node.material) (Array.isArray(node.material) ? node.material : [node.material]).forEach((m) => m.dispose());
      });
      this.world.remove(this.room);
    }
    this.wardId = ward.ward_id;
    this.dims = { roomW: ward.width * CELL_W + 1.2, roomD: ward.height * CELL_D + 1.0, cols: ward.width, rows: ward.height };
    this.room = roomShell(this.dims);
    this.world.add(this.room);
    const { roomW, roomD } = this.dims;
    const radius = Math.max(roomW * 0.62, roomD * 0.95);
    this.overview = {
      position: new THREE.Vector3(0, radius * 0.78 + 1.4, roomD / 2 + radius * 0.8),
      target: new THREE.Vector3(0, 0.7, 0.2),
    };
    this.bounds = { x: roomW / 2 + 1, z: roomD / 2 + 1 };
    this.hall.key.shadow.camera.left = -roomW;
    this.hall.key.shadow.camera.right = roomW;
    this.hall.key.shadow.camera.top = roomD;
    this.hall.key.shadow.camera.bottom = -roomD;
    this.hall.key.shadow.camera.updateProjectionMatrix();
    this.controls.maxDistance = Math.max(30, radius * 3);
    this.camera.position.copy(this.overview.position);
    this.controls.target.copy(this.overview.target);
    this.controls.update();
    this.container.setAttribute("data-camera-target", "overview");
    this.dirty = true;
  }

  addBed(bed) {
    const { cols, rows } = this.dims;
    const built = buildBed(bed.label, bed.occupied);
    const group = new THREE.Group();
    group.add(built.root);
    const x = (bed.x - 1 + 0.5 - cols / 2) * CELL_W;
    const z = (bed.y - 1 + 0.5 - rows / 2) * CELL_D + 0.35;
    group.position.set(x, 0, z);
    const lamp = wallLamp();
    lamp.group.position.set(-0.55, 1.9, -1.28 + 0.1);
    built.root.add(lamp.group);
    const ring = put(
      new THREE.RingGeometry(1.45, 1.52, 96),
      new THREE.MeshStandardMaterial({ color: 0x6b7785, emissive: 0x6b7785, emissiveIntensity: 0.9, roughness: 0.6, transparent: true, opacity: 0.95 }),
      { cast: false },
    );
    ring.rotation.x = -Math.PI / 2;
    ring.position.set(0, 0.014, -0.15);
    group.add(ring);
    // leito BLOQUEADO: barreira listrada aos pes da cama (alem do anel e do texto, nunca so cor)
    const barrier = new THREE.Group();
    const stripes = new THREE.MeshStandardMaterial({ map: M.hazardStripes(), roughness: 0.6, metalness: 0.1 });
    barrier.add(at(put(new THREE.BoxGeometry(1.5, 0.28, 0.06), stripes), 0, 0.62, 1.55));
    for (const sx of [-0.7, 0.7]) barrier.add(at(cyl(0.03, 0.03, 0.62, M.steel(), 12), sx, 0.31, 1.55));
    barrier.visible = false;
    group.add(barrier);
    group.traverse((node) => {
      node.userData.machineId = bed.bed_id;
    });
    this.world.add(group);
    const labelEl = document.createElement("button");
    labelEl.type = "button";
    labelEl.className = "v3d-label";
    labelEl.setAttribute("data-testid", this.labelPrefix + "-" + bed.bed_id);
    for (const cls of ["l-title", "l-status", "l-read"]) {
      const span = document.createElement("span");
      span.className = cls;
      labelEl.appendChild(span);
    }
    labelEl.addEventListener("click", () => this.pick(bed.bed_id));
    const labelObject = new CSS2DObject(labelEl);
    labelObject.position.set(0, 2.55, -1.1);
    group.add(labelObject);
    const machine = { id: bed.bed_id, group, lamp, ring, radius: 2.0, topY: 2.1, labelEl, labelObject, barrier, leds: built.leds, bedLed: built.bedLed, pumpLed: built.pumpLed, status: "UNKNOWN" };
    this.machines.set(bed.bed_id, machine);
    return machine;
  }

  applyBed(machine, bed, evaluatedAt) {
    const known = this.options.statusMeta[bed.status] ? bed.status : "UNKNOWN";
    const meta = this.options.statusMeta[known];
    const lit = BED_LENS[known] || null;
    for (const [key, lens] of Object.entries(machine.lamp.lenses)) {
      lens.material.emissiveIntensity = key === lit ? 3.4 : 0;
      lens.material.color.setHex(key === lit ? LENS_COLOR[key] : 0x2a2d31);
    }
    machine.lamp.light.color.setHex(lit ? LENS_COLOR[lit] : 0xffffff);
    machine.lamp.light.intensity = lit ? 1.6 : 0;
    const color = BED_STATUS_COLOR[known];
    machine.ring.material.color.setHex(color);
    machine.ring.material.emissive.setHex(color);
    machine.ring.material.emissiveIntensity = known === "OFFLINE" || known === "UNKNOWN" ? 0.35 : 1.1;
    machine.barrier.visible = known === "BLOCKED";
    machine.pulse = known === "ALERT";
    const rules = new Set(bed.alerts.map((a) => a.rule));
    for (const [rule, material] of Object.entries(machine.leds)) material.emissiveIntensity = rules.has(rule) ? 3 : 0;
    machine.pumpLed.emissiveIntensity = rules.has("iv_pump_alarm") ? 3 : 0.25;
    machine.bedLed.emissiveIntensity = rules.has("bed_exit_alarm") ? 3 : 0;
    const names = bed.alerts.map((a) => (this.options.ruleLabels[a.rule] || a.rule)).join(", ");
    let age = "sem leitura";
    if (bed.observed_at) {
      const seconds = Math.max(0, Math.round((Date.parse(evaluatedAt) - Date.parse(bed.observed_at)) / 1000));
      age = "leitura há " + seconds + " s";
    }
    const label = machine.labelEl;
    label.setAttribute("data-status", known);
    label.setAttribute("aria-label", bed.label + ", " + meta.label + (names ? ", " + names : ""));
    label.title = bed.bed_id + " · " + bed.label + " · " + meta.label;
    label.children[0].textContent = meta.icon + " " + bed.label;
    label.children[1].textContent = meta.label;
    label.children[2].textContent = (bed.occupied ? "Ocupado" : "Livre") + " · " + (names || age);
    const signature = known + "|" + [...rules].sort().join(",") + "|" + bed.occupied;
    const changed = signature !== machine.signature;
    machine.signature = signature;
    machine.status = known;
    return changed;
  }

  focusOn(id) {
    const machine = this.machines.get(id);
    if (!machine) return;
    const base = machine.group.position;
    this.flyTo(new THREE.Vector3(base.x + 2.4, 2.6, base.z + 3.4), new THREE.Vector3(base.x, 0.9, base.z - 0.4));
    this.container.setAttribute("data-camera-target", id);
  }
}
