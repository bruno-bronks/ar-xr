// Visualizador 3D do painel (REQ-UX-004): galpao + equipamentos coloridos pelo estado do twin.
// Todo texto vindo da API entra via textContent. Posicoes dos equipamentos sao ILUSTRATIVAS (D-051).
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";
import { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";
import { RenderPass } from "three/addons/postprocessing/RenderPass.js";
import { GTAOPass } from "three/addons/postprocessing/GTAOPass.js";
import { UnrealBloomPass } from "three/addons/postprocessing/UnrealBloomPass.js";
import { OutputPass } from "three/addons/postprocessing/OutputPass.js";
import { CSS2DObject, CSS2DRenderer } from "three/addons/renderers/CSS2DRenderer.js";
import { buildHall } from "./hall.js";
import { modelFor } from "./machines.js";

const STATUS_COLOR = { NORMAL: 0x1fa85a, WARNING: 0xe0a21a, CRITICAL: 0xe5383b, OFFLINE: 0x6b7785, UNKNOWN: 0x8c6fe0 };
const LENS_FOR = { NORMAL: "green", WARNING: "amber", CRITICAL: "red" };
const LENS_COLOR = { green: 0x19c96b, amber: 0xffb400, red: 0xff2a2a };
const QUALITIES = ["alta", "media", "baixa"];
const UNIT = { celsius: "°C" };
const SENSOR = { temperature: "Temperatura", vibration: "Vibração" };
const MAP = { w: 18, d: 11 }; // metros que a area da planta 2D representa
const OVERVIEW = { position: new THREE.Vector3(0, 7.4, 14.2), target: new THREE.Vector3(0, 0.4, 0.2) };

export function webglAvailable() {
  try {
    const probe = document.createElement("canvas");
    return Boolean(probe.getContext("webgl2"));
  } catch {
    return false;
  }
}

function el(tag, attrs = {}, text = "") {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
  if (text) node.textContent = text;
  return node;
}

function pickQuality(requested) {
  if (QUALITIES.includes(requested)) return requested;
  const small = window.innerWidth < 700 || (navigator.hardwareConcurrency || 4) <= 2;
  return small ? "media" : "alta";
}

export class Viewer {
  constructor(container, options) {
    this.container = container;
    this.options = options;
    this.quality = pickQuality(options.quality);
    this.reduceMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    this.machines = new Map();
    this.visible = true;
    this.dirty = true;
    this.frames = 0;
    this.selectedId = null;
    this.disposed = false;
    this.clock = new THREE.Clock();
    this.anim = null;
    this.build();
  }

  // ---- montagem -----------------------------------------------------------------------------------
  build() {
    const { container } = this;
    container.replaceChildren();
    this.stage = el("div", { class: "v3d-stage" });
    this.canvas = el("canvas", { class: "v3d-canvas", "aria-hidden": "true" });
    this.stage.appendChild(this.canvas);
    this.note = el("p", { class: "v3d-note muted", "data-testid": "viewer3d-note" });
    this.toolbar = el("div", { class: "v3d-toolbar", role: "toolbar", "aria-label": "Controles da vista 3D" });
    container.append(this.stage, this.toolbar, this.note);

    const renderer = new THREE.WebGLRenderer({ canvas: this.canvas, antialias: true, powerPreference: "high-performance" });
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.0;
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.setClearColor(0x14171b, 1);
    this.renderer = renderer;
    this.canvas.addEventListener("webglcontextlost", (event) => {
      event.preventDefault();
      this.fail("O contexto gráfico foi perdido; recarregue a página para ver o 3D.");
    });

    this.scene = new THREE.Scene();
    this.scene.fog = new THREE.Fog(0x14171b, 38, 80);
    const pmrem = new THREE.PMREMGenerator(renderer);
    this.envTexture = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
    pmrem.dispose();
    this.scene.environment = this.envTexture;
    this.scene.environmentIntensity = 0.42;

    this.camera = new THREE.PerspectiveCamera(36, 16 / 9, 0.1, 140);
    this.camera.position.copy(OVERVIEW.position);

    this.hall = buildHall(this.scene, { zones: this.options.zones, mapW: MAP.w, mapD: MAP.d });
    this.world = new THREE.Group();
    this.scene.add(this.world);

    this.labels = new CSS2DRenderer();
    this.labels.domElement.className = "v3d-labels";
    this.stage.appendChild(this.labels.domElement);

    this.controls = new OrbitControls(this.camera, this.canvas);
    this.controls.enableDamping = !this.reduceMotion;
    this.controls.dampingFactor = 0.08;
    this.controls.minDistance = 3;
    this.controls.maxDistance = 30;
    this.controls.minPolarAngle = 0.2;
    this.controls.maxPolarAngle = 1.46;
    this.controls.target.copy(OVERVIEW.target);
    this.controls.addEventListener("change", () => {
      const t = this.controls.target;
      t.x = THREE.MathUtils.clamp(t.x, -11, 11);
      t.z = THREE.MathUtils.clamp(t.z, -6, 6);
      t.y = THREE.MathUtils.clamp(t.y, 0, 3);
      this.dirty = true;
    });
    this.controls.update();

    this.raycaster = new THREE.Raycaster();
    this.setupPicking();
    this.buildComposer();
    this.buildToolbar();
    this.observe();
    this.resize();
    this.container.setAttribute("data-quality", this.quality);
    this.container.setAttribute("data-ready", "true");
    this.container.setAttribute("data-frames", "0");
    this.container.setAttribute("data-selected", "");
    this.container.setAttribute("data-camera-target", "overview");
    this.loop = this.loop.bind(this);
    this.raf = requestAnimationFrame(this.loop);
  }

  buildComposer() {
    this.composer = null;
    this.bloom = null;
    if (this.quality === "baixa") {
      this.renderer.shadowMap.type = THREE.PCFShadowMap;
      this.hall.key.shadow.mapSize.set(1024, 1024);
      return;
    }
    const target = new THREE.WebGLRenderTarget(4, 4, { type: THREE.HalfFloatType, samples: 4 });
    const composer = new EffectComposer(this.renderer, target);
    composer.addPass(new RenderPass(this.scene, this.camera));
    if (this.quality === "alta") {
      const ao = new GTAOPass(this.scene, this.camera, 4, 4);
      ao.blendIntensity = 0.95;
      ao.updateGtaoMaterial({ radius: 0.55, distanceExponent: 1.2, thickness: 1.2, scale: 1.05, samples: 16, distanceFallOff: 1, screenSpaceRadius: false });
      ao.updatePdMaterial({ lumaPhi: 10, depthPhi: 2, normalPhi: 3, radius: 6, radiusExponent: 1, rings: 2, samples: 12 });
      composer.addPass(ao);
      this.ao = ao;
    } else {
      this.hall.key.shadow.mapSize.set(1024, 1024);
    }
    this.bloom = new UnrealBloomPass(new THREE.Vector2(4, 4), 0.42, 0.55, 0.9);
    composer.addPass(this.bloom);
    composer.addPass(new OutputPass());
    this.composer = composer;
  }

  buildToolbar() {
    this.toolbar.replaceChildren();
    const reset = el("button", { type: "button", class: "v3d-btn", "data-testid": "viewer3d-reset" }, "Visão geral");
    reset.addEventListener("click", () => this.reset());
    this.toolbar.appendChild(reset);
    this.focusButtons = el("span", { class: "v3d-focus", "data-testid": "viewer3d-focus" });
    this.toolbar.appendChild(this.focusButtons);
    const label = el("label", { class: "v3d-quality" }, "Qualidade ");
    const select = el("select", { "data-testid": "viewer3d-quality", "aria-label": "Qualidade gráfica" });
    for (const q of QUALITIES) {
      const option = el("option", { value: q }, { alta: "Alta", media: "Média", baixa: "Baixa" }[q]);
      if (q === this.quality) option.selected = true;
      select.appendChild(option);
    }
    select.addEventListener("change", () => this.options.onQuality && this.options.onQuality(select.value));
    label.appendChild(select);
    this.toolbar.appendChild(label);
  }

  observe() {
    this.resizeObserver = new ResizeObserver(() => this.resize());
    this.resizeObserver.observe(this.stage);
    this.intersection = new IntersectionObserver((entries) => {
      this.visible = entries.some((entry) => entry.isIntersecting);
      if (this.visible) this.dirty = true;
    });
    this.intersection.observe(this.stage);
    this.onVisibility = () => {
      if (!document.hidden) this.dirty = true;
    };
    document.addEventListener("visibilitychange", this.onVisibility);
  }

  resize() {
    const width = Math.max(1, this.stage.clientWidth);
    const height = Math.max(1, this.stage.clientHeight);
    const ratio = Math.min(window.devicePixelRatio || 1, { alta: 2, media: 1.5, baixa: 1 }[this.quality]);
    this.renderer.setPixelRatio(ratio);
    this.renderer.setSize(width, height, false);
    this.labels.setSize(width, height);
    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
    if (this.composer) {
      this.composer.setPixelRatio(ratio);
      this.composer.setSize(width, height);
    }
    this.dirty = true;
  }

  // ---- interacao ------------------------------------------------------------------------------------
  setupPicking() {
    let down = null;
    this.canvas.addEventListener("pointerdown", (event) => {
      down = { x: event.clientX, y: event.clientY, t: performance.now() };
    });
    this.canvas.addEventListener("pointerup", (event) => {
      if (!down) return;
      const moved = Math.hypot(event.clientX - down.x, event.clientY - down.y);
      const quick = performance.now() - down.t < 500;
      down = null;
      if (moved > 5 || !quick) return; // arrasto = orbitar, nao clicar
      const rect = this.canvas.getBoundingClientRect();
      const ndc = new THREE.Vector2(((event.clientX - rect.left) / rect.width) * 2 - 1, -((event.clientY - rect.top) / rect.height) * 2 + 1);
      this.raycaster.setFromCamera(ndc, this.camera);
      const hit = this.raycaster.intersectObject(this.world, true).find((h) => h.object.userData.machineId);
      if (hit) this.pick(hit.object.userData.machineId);
    });
    this.canvas.addEventListener("dblclick", () => this.reset());
  }

  pick(id) {
    this.select(id);
    if (this.options.onSelect) this.options.onSelect(id);
  }

  select(id, { focus = true } = {}) {
    this.selectedId = id;
    this.container.setAttribute("data-selected", id || "");
    for (const [machineId, machine] of this.machines) {
      machine.labelEl.toggleAttribute("data-selected", machineId === id);
      machine.ring.material.opacity = machineId === id ? 1 : 0.6;
    }
    if (focus && id && this.machines.has(id)) this.focusOn(id);
    this.dirty = true;
  }

  focusOn(id) {
    const machine = this.machines.get(id);
    if (!machine) return;
    const base = machine.group.position;
    const distance = Math.max(4.2, machine.radius * 2.5);
    this.flyTo(
      new THREE.Vector3(base.x + distance * 0.55, 2.0 + machine.topY * 0.55, base.z + distance * 0.95),
      new THREE.Vector3(base.x, machine.topY * 0.42, base.z),
    );
    this.container.setAttribute("data-camera-target", id);
  }

  reset() {
    this.selectedId = null;
    this.container.setAttribute("data-selected", "");
    for (const machine of this.machines.values()) machine.labelEl.removeAttribute("data-selected");
    this.container.setAttribute("data-camera-target", "overview");
    const wide = this.camera.aspect < 1.3;
    this.flyTo(wide ? new THREE.Vector3(0, 11, 20) : OVERVIEW.position.clone(), OVERVIEW.target.clone());
  }

  flyTo(position, target) {
    if (this.reduceMotion) {
      this.camera.position.copy(position);
      this.controls.target.copy(target);
      this.controls.update();
      this.dirty = true;
      return;
    }
    this.anim = { fromP: this.camera.position.clone(), fromT: this.controls.target.clone(), toP: position, toT: target, t0: performance.now(), dur: 900 };
    this.dirty = true;
  }

  // ---- dados -----------------------------------------------------------------------------------------
  update(details) {
    const keep = new Set(details.map((d) => d.equipment.id));
    let changed = false;
    for (const [id, machine] of [...this.machines]) {
      if (!keep.has(id)) {
        this.removeMachine(id, machine);
        changed = true;
      }
    }
    for (const { equipment, twin } of details) {
      const spot = this.options.spots[equipment.id];
      if (!spot) continue; // sem posicao: nao inventamos; a planta 2D lista esse caso
      let machine = this.machines.get(equipment.id);
      if (!machine) {
        machine = this.addMachine(equipment, spot);
        changed = true;
      }
      if (this.apply(machine, equipment, twin)) changed = true;
    }
    this.renderFocusButtons(details.filter((d) => this.machines.has(d.equipment.id)));
    this.container.setAttribute("data-machines", String(this.machines.size));
    if (changed) this.dirty = true; // o ciclo de 2 s sem mudanca NAO redesenha a cena
  }

  addMachine(equipment, spot) {
    const model = modelFor(equipment);
    model.group.traverse((node) => {
      node.userData.machineId = equipment.id;
    });
    model.group.position.set((spot.x / 100 - 0.5) * MAP.w, 0, (spot.y / 100 - 0.5) * MAP.d);
    this.world.add(model.group);
    const labelEl = el("button", { type: "button", class: "v3d-label", "data-testid": "label3d-" + equipment.id });
    labelEl.append(el("span", { class: "l-title" }), el("span", { class: "l-status" }), el("span", { class: "l-read" }));
    labelEl.addEventListener("click", () => this.pick(equipment.id));
    const labelObject = new CSS2DObject(labelEl);
    labelObject.position.set(0, model.topY + 0.25, 0);
    model.group.add(labelObject);
    const machine = { ...model, labelEl, labelObject, status: "UNKNOWN" };
    this.machines.set(equipment.id, machine);
    return machine;
  }

  removeMachine(id, machine) {
    machine.group.traverse((node) => {
      if (node.geometry) node.geometry.dispose();
      if (node.material) (Array.isArray(node.material) ? node.material : [node.material]).forEach((m) => m.dispose());
    });
    machine.labelEl.remove();
    this.world.remove(machine.group);
    this.machines.delete(id);
    if (this.selectedId === id) this.selectedId = null;
  }

  apply(machine, equipment, twin) {
    const meta = this.options.statusMeta[twin.status] || this.options.statusMeta.UNKNOWN;
    machine.status = this.options.statusMeta[twin.status] ? twin.status : "UNKNOWN";
    const lit = LENS_FOR[machine.status] || null;
    for (const [key, lens] of Object.entries(machine.lamp.lenses)) {
      lens.material.emissiveIntensity = key === lit ? 3.2 : 0.02;
      lens.material.color.setHex(key === lit ? LENS_COLOR[key] : 0x2a2d31);
    }
    machine.lamp.light.color.setHex(lit ? LENS_COLOR[lit] : 0xffffff);
    machine.lamp.light.intensity = lit ? 2.4 : 0;
    const color = STATUS_COLOR[machine.status];
    machine.ring.material.color.setHex(color);
    machine.ring.material.emissive.setHex(color);
    machine.ring.material.emissiveIntensity = machine.status === "OFFLINE" || machine.status === "UNKNOWN" ? 0.35 : 1.1;
    machine.pulse = machine.status === "CRITICAL";

    const label = machine.labelEl;
    label.setAttribute("data-status", machine.status);
    label.setAttribute("aria-label", equipment.name + ", " + meta.label);
    label.title = equipment.id + " · " + equipment.name + " · " + meta.label;
    label.children[0].textContent = meta.icon + " " + equipment.name;
    label.children[1].textContent = meta.label;
    const readings = twin.sensors
      .filter((s) => s.value !== null && s.value !== undefined)
      .map((s) => (SENSOR[s.sensor_type] || s.sensor_type) + " " + s.value.toFixed(1) + " " + (UNIT[s.unit] || s.unit));
    label.children[2].textContent = readings.length ? readings.join(" · ") : "sem leituras";
    const signature = machine.status; // so o estado muda a cena 3D; texto/leituras sao DOM (sem redesenhar o WebGL)
    const changed = signature !== machine.signature;
    machine.signature = signature;
    return changed;
  }

  renderFocusButtons(details) {
    const wanted = details.map((d) => d.equipment.id).join("|");
    if (this.focusKey === wanted) {
      for (const { equipment } of details) {
        const button = this.focusButtons.querySelector('[data-id="' + CSS.escape(equipment.id) + '"]');
        if (button) button.textContent = equipment.name;
      }
      return;
    }
    this.focusKey = wanted;
    this.focusButtons.replaceChildren(
      ...details.map(({ equipment }) => {
        const button = el("button", { type: "button", class: "v3d-btn", "data-id": equipment.id, "data-testid": "viewer3d-focus-" + equipment.id }, equipment.name);
        button.addEventListener("click", () => this.pick(equipment.id));
        return button;
      }),
    );
  }

  setStale(stale) {
    this.container.setAttribute("data-stale", String(stale));
  }

  clear() {
    for (const [id, machine] of [...this.machines]) this.removeMachine(id, machine);
    this.focusKey = null;
    this.focusButtons.replaceChildren();
    this.container.setAttribute("data-machines", "0");
    this.container.setAttribute("data-selected", "");
    this.reset();
  }

  // ---- laco de render (sob demanda: so desenha quando algo mudou) -------------------------------------------
  loop(now) {
    if (this.disposed) return;
    this.raf = requestAnimationFrame(this.loop);
    if (!this.visible || document.hidden) return;
    let animating = false;
    if (this.anim) {
      const t = Math.min(1, (performance.now() - this.anim.t0) / this.anim.dur);
      const e = t * t * (3 - 2 * t);
      this.camera.position.lerpVectors(this.anim.fromP, this.anim.toP, e);
      this.controls.target.lerpVectors(this.anim.fromT, this.anim.toT, e);
      if (t >= 1) this.anim = null;
      animating = true;
    }
    if (this.controls.update()) animating = true;
    const seconds = now / 1000;
    let pulsing = false;
    for (const machine of this.machines.values()) {
      if (!machine.pulse) continue;
      pulsing = true;
      const wave = this.reduceMotion ? 1 : 0.5 + 0.5 * Math.sin(seconds * 6.0);
      machine.lamp.lenses.red.material.emissiveIntensity = 0.6 + 3.2 * wave;
      machine.lamp.light.intensity = 0.6 + 2.2 * wave;
      machine.ring.material.emissiveIntensity = 0.5 + 1.2 * wave;
    }
    if (!(this.dirty || animating || (pulsing && !this.reduceMotion))) return;
    this.dirty = false;
    if (this.composer) this.composer.render();
    else this.renderer.render(this.scene, this.camera);
    this.labels.render(this.scene, this.camera);
    this.frames += 1;
    this.container.setAttribute("data-frames", String(this.frames));
    this.container.setAttribute("data-camera-distance", this.camera.position.distanceTo(this.controls.target).toFixed(1));
  }

  fail(message) {
    this.note.textContent = message;
    this.container.setAttribute("data-ready", "false");
    if (this.options.onFail) this.options.onFail(message);
  }

  destroy() {
    this.disposed = true;
    cancelAnimationFrame(this.raf);
    this.resizeObserver?.disconnect();
    this.intersection?.disconnect();
    document.removeEventListener("visibilitychange", this.onVisibility);
    for (const [id, machine] of [...this.machines]) this.removeMachine(id, machine);
    this.scene.traverse((node) => {
      if (node.geometry) node.geometry.dispose();
      if (node.material) {
        const list = Array.isArray(node.material) ? node.material : [node.material];
        for (const material of list) {
          for (const value of Object.values(material)) if (value && value.isTexture) value.dispose();
          material.dispose();
        }
      }
    });
    this.envTexture?.dispose();
    this.controls.dispose();
    this.composer?.dispose();
    this.renderer.dispose();
    this.container.replaceChildren();
    this.container.setAttribute("data-ready", "false");
  }
}
