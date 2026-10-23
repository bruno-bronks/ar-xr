// Materiais PBR e texturas PROCEDURAIS (sem arquivos externos: a CSP do painel so permite 'self').
import * as THREE from "three";

// PRNG deterministico: a mesma cena sai identica em qualquer maquina (texturas inclusive).
export function rng(seed) {
  let a = seed >>> 0;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function canvas(width, height) {
  const node = document.createElement("canvas");
  node.width = width;
  node.height = height;
  return node;
}

function asTexture(node, { srgb = true, repeat = null, anisotropy = 8 } = {}) {
  const texture = new THREE.CanvasTexture(node);
  texture.colorSpace = srgb ? THREE.SRGBColorSpace : THREE.NoColorSpace;
  texture.anisotropy = anisotropy;
  if (repeat) {
    texture.wrapS = texture.wrapT = THREE.RepeatWrapping;
    texture.repeat.set(repeat[0], repeat[1]);
  }
  texture.needsUpdate = true;
  return texture;
}

// Concreto polido: cor, rugosidade e relevo vem do mesmo ruido (manchas grandes + granulado fino).
export function concrete() {
  const size = 1024;
  const color = canvas(size, size);
  const rough = canvas(size, size);
  const bump = canvas(size, size);
  const cc = color.getContext("2d");
  const rc = rough.getContext("2d");
  const bc = bump.getContext("2d");
  const rand = rng(1234);
  cc.fillStyle = "#8d9094";
  cc.fillRect(0, 0, size, size);
  rc.fillStyle = "#9a9a9a";
  rc.fillRect(0, 0, size, size);
  bc.fillStyle = "#808080";
  bc.fillRect(0, 0, size, size);
  for (let i = 0; i < 90; i += 1) {
    const x = rand() * size;
    const y = rand() * size;
    const r = 40 + rand() * 160;
    const tone = rand() < 0.5 ? 255 : 0;
    const alpha = 0.025 + rand() * 0.045;
    for (const [ctx, scale] of [[cc, 1], [rc, 1.2], [bc, 0.6]]) {
      const g = ctx.createRadialGradient(x, y, 0, x, y, r);
      g.addColorStop(0, `rgba(${tone},${tone},${tone},${alpha * scale})`);
      g.addColorStop(1, `rgba(${tone},${tone},${tone},0)`);
      ctx.fillStyle = g;
      ctx.fillRect(x - r, y - r, r * 2, r * 2);
    }
  }
  for (let i = 0; i < 26000; i += 1) {
    const x = rand() * size;
    const y = rand() * size;
    const v = Math.floor(rand() * 255);
    const a = 0.05 + rand() * 0.12;
    cc.fillStyle = `rgba(${v},${v},${v},${a})`;
    cc.fillRect(x, y, 1.4, 1.4);
    bc.fillStyle = `rgba(${v},${v},${v},${a})`;
    bc.fillRect(x, y, 1.4, 1.4);
  }
  // juntas de dilatacao (grade de 4 x 4 por tile)
  cc.strokeStyle = "rgba(30,32,36,0.28)";
  cc.lineWidth = 2;
  rc.strokeStyle = "rgba(255,255,255,0.9)";
  rc.lineWidth = 3;
  bc.strokeStyle = "rgba(0,0,0,0.55)";
  bc.lineWidth = 3;
  for (let i = 0; i <= 2; i += 1) {
    const p = (i * size) / 2;
    for (const ctx of [cc, rc, bc]) {
      ctx.beginPath();
      ctx.moveTo(p, 0);
      ctx.lineTo(p, size);
      ctx.moveTo(0, p);
      ctx.lineTo(size, p);
      ctx.stroke();
    }
  }
  const repeat = [7, 4];
  return {
    map: asTexture(color, { repeat }),
    roughnessMap: asTexture(rough, { srgb: false, repeat }),
    bumpMap: asTexture(bump, { srgb: false, repeat }),
  };
}

// Faixas amarelas de seguranca + rotulos de zona pintados no piso (decal transparente).
export function floorDecals(zones, width, depth) {
  const scale = 64; // px por metro
  const node = canvas(Math.round(width * scale), Math.round(depth * scale));
  const ctx = node.getContext("2d");
  ctx.clearRect(0, 0, node.width, node.height);
  ctx.lineWidth = 9;
  ctx.strokeStyle = "rgba(214,170,24,0.9)";
  ctx.fillStyle = "rgba(222,222,222,0.62)";
  ctx.font = "700 74px system-ui, Segoe UI, sans-serif";
  ctx.textBaseline = "top";
  for (const zone of zones) {
    const x = (zone.x / 100) * node.width;
    const y = (zone.y / 100) * node.height;
    const w = (zone.w / 100) * node.width;
    const h = (zone.h / 100) * node.height;
    ctx.setLineDash([]);
    ctx.strokeRect(x, y, w, h);
    ctx.setLineDash([36, 26]);
    ctx.lineWidth = 4;
    ctx.strokeRect(x + 22, y + 22, w - 44, h - 44);
    ctx.lineWidth = 9;
    ctx.fillText(zone.label.toUpperCase(), x + 46, y + 46);
  }
  const texture = asTexture(node, { anisotropy: 16 });
  return texture;
}

// Chapa corrugada para as paredes (listras verticais no relevo).
export function corrugated(repeatX) {
  const node = canvas(256, 256);
  const ctx = node.getContext("2d");
  const grad = ctx.createLinearGradient(0, 0, 256, 0);
  for (let i = 0; i <= 8; i += 1) {
    grad.addColorStop(i / 8, i % 2 === 0 ? "#2b2b2b" : "#d6d6d6");
  }
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, 256, 256);
  const bump = asTexture(node, { srgb: false, repeat: [repeatX, 1] });
  const color = canvas(64, 64);
  const cctx = color.getContext("2d");
  cctx.fillStyle = "#c9ced4";
  cctx.fillRect(0, 0, 64, 64);
  return { map: asTexture(color, { repeat: [repeatX, 1] }), bumpMap: bump };
}

// Listras de aviso preto/amarelo (base das colunas e guardas).
export function hazardStripes() {
  const node = canvas(128, 128);
  const ctx = node.getContext("2d");
  ctx.fillStyle = "#e8bb1c";
  ctx.fillRect(0, 0, 128, 128);
  ctx.fillStyle = "#17181a";
  for (let i = -2; i < 6; i += 1) {
    ctx.beginPath();
    ctx.moveTo(i * 32, 128);
    ctx.lineTo(i * 32 + 32, 128);
    ctx.lineTo(i * 32 + 96, 0);
    ctx.lineTo(i * 32 + 64, 0);
    ctx.closePath();
    ctx.fill();
  }
  return asTexture(node, { repeat: [1, 6] });
}

// Grade/perfuracao para protecoes (alphaMap): furos redondos regulares.
export function perforated(cols = 12, rows = 8) {
  const node = canvas(256, 256);
  const ctx = node.getContext("2d");
  ctx.fillStyle = "#fff";
  ctx.fillRect(0, 0, 256, 256);
  ctx.fillStyle = "#000";
  for (let i = 0; i < cols; i += 1) {
    for (let j = 0; j < rows; j += 1) {
      ctx.beginPath();
      ctx.arc(((i + 0.5) * 256) / cols, ((j + 0.5) * 256) / rows, 7, 0, Math.PI * 2);
      ctx.fill();
    }
  }
  return asTexture(node, { srgb: false });
}

// Mostrador de manometro: ticks, numeros, faixa vermelha. Valor FIXO decorativo (nao e leitura).
export function gaugeFace() {
  const node = canvas(256, 256);
  const ctx = node.getContext("2d");
  ctx.fillStyle = "#f4f4f1";
  ctx.beginPath();
  ctx.arc(128, 128, 126, 0, Math.PI * 2);
  ctx.fill();
  ctx.strokeStyle = "#1b1b1b";
  ctx.fillStyle = "#1b1b1b";
  ctx.lineWidth = 3;
  ctx.font = "700 20px system-ui, sans-serif";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  const start = (135 * Math.PI) / 180;
  const sweep = (270 * Math.PI) / 180;
  ctx.strokeStyle = "#c62828";
  ctx.lineWidth = 9;
  ctx.beginPath();
  ctx.arc(128, 128, 100, start + sweep * 0.78, start + sweep, false);
  ctx.stroke();
  ctx.strokeStyle = "#1b1b1b";
  for (let i = 0; i <= 10; i += 1) {
    const a = start + (sweep * i) / 10;
    const major = i % 2 === 0;
    const r1 = major ? 80 : 88;
    ctx.lineWidth = major ? 4 : 2;
    ctx.beginPath();
    ctx.moveTo(128 + Math.cos(a) * r1, 128 + Math.sin(a) * r1);
    ctx.lineTo(128 + Math.cos(a) * 104, 128 + Math.sin(a) * 104);
    ctx.stroke();
    if (major) ctx.fillText(String(i), 128 + Math.cos(a) * 62, 128 + Math.sin(a) * 62);
  }
  ctx.font = "600 16px system-ui, sans-serif";
  ctx.fillText("bar", 128, 176);
  // agulha em posicao neutra (decorativa)
  const needle = start + sweep * 0.42;
  ctx.strokeStyle = "#b71c1c";
  ctx.lineWidth = 5;
  ctx.beginPath();
  ctx.moveTo(128, 128);
  ctx.lineTo(128 + Math.cos(needle) * 86, 128 + Math.sin(needle) * 86);
  ctx.stroke();
  ctx.fillStyle = "#222";
  ctx.beginPath();
  ctx.arc(128, 128, 9, 0, Math.PI * 2);
  ctx.fill();
  return asTexture(node);
}

export function namePlate(line1, line2) {
  const node = canvas(256, 128);
  const ctx = node.getContext("2d");
  ctx.fillStyle = "#bfc4c9";
  ctx.fillRect(0, 0, 256, 128);
  ctx.strokeStyle = "#5a6068";
  ctx.lineWidth = 4;
  ctx.strokeRect(4, 4, 248, 120);
  ctx.fillStyle = "#23262a";
  ctx.font = "700 26px system-ui, sans-serif";
  ctx.textAlign = "center";
  ctx.fillText(line1, 128, 54);
  ctx.font = "500 20px system-ui, sans-serif";
  ctx.fillText(line2, 128, 92);
  return asTexture(node);
}

// ---- materiais fisicos reutilizaveis ------------------------------------------------------------
export function paint(color, { metalness = 0.35, roughness = 0.38, clearcoat = 0.7 } = {}) {
  return new THREE.MeshPhysicalMaterial({
    color,
    metalness,
    roughness,
    clearcoat,
    clearcoatRoughness: 0.22,
  });
}

export const steel = () => new THREE.MeshStandardMaterial({ color: 0xaab0b7, metalness: 0.95, roughness: 0.32 });
export const darkSteel = () => new THREE.MeshStandardMaterial({ color: 0x4a4f56, metalness: 0.9, roughness: 0.45 });
export const castIron = () => new THREE.MeshStandardMaterial({ color: 0x3d4248, metalness: 0.7, roughness: 0.62 });
export const rubber = () => new THREE.MeshStandardMaterial({ color: 0x151617, metalness: 0.0, roughness: 0.9 });
export const brass = () => new THREE.MeshStandardMaterial({ color: 0xc8a24a, metalness: 1.0, roughness: 0.28 });
export const glass = () =>
  new THREE.MeshPhysicalMaterial({
    color: 0xffffff,
    metalness: 0,
    roughness: 0.05,
    transmission: 0.0,
    transparent: true,
    opacity: 0.22,
    clearcoat: 1,
  });
