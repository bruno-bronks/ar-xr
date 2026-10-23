// Gera clients/web-fallback/vendor/viewer3d.js (IIFE minificado, sem CDN) e o manifesto com hashes.
// Uso: npm ci && npm run build   (CI refaz o build e falha se o resultado divergir do commitado)
import { build } from "esbuild";
import { createHash } from "node:crypto";
import { mkdirSync, readFileSync, readdirSync, writeFileSync, copyFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const out = resolve(here, "../web-fallback/vendor");
mkdirSync(out, { recursive: true });

await build({
  entryPoints: [join(here, "src/index.js")],
  bundle: true,
  minify: true,
  format: "iife",
  target: "es2020",
  legalComments: "eof",
  outfile: join(out, "viewer3d.js"),
  logLevel: "info",
});

const sha = (buffer) => createHash("sha256").update(buffer).digest("hex");
const shaText = (path) => sha(readFileSync(path, "utf8").replace(/\r\n/g, "\n"));
const bundle = readFileSync(join(out, "viewer3d.js"));
const sources = Object.fromEntries(
  readdirSync(join(here, "src"))
    .sort()
    .map((name) => [name, shaText(join(here, "src", name))]),
);
const pkg = JSON.parse(readFileSync(join(here, "node_modules/three/package.json"), "utf8"));
const esbuild = JSON.parse(readFileSync(join(here, "node_modules/esbuild/package.json"), "utf8"));
writeFileSync(
  join(out, "viewer3d.manifest.json"),
  JSON.stringify(
    {
      bundle: "viewer3d.js",
      sha256: sha(bundle),
      bytes: bundle.length,
      three: { version: pkg.version, license: pkg.license },
      esbuild: esbuild.version,
      sources,
    },
    null,
    2,
  ) + "\n",
);
copyFileSync(join(here, "node_modules/three/LICENSE"), join(out, "THREE-LICENSE.txt"));
console.log("bundle", bundle.length, "bytes sha256", sha(bundle));
