"""REQ-UX-004, REQ-UX-005 / D-052: o bundle 3D versionado e rastreavel (hash, versao pinada, sem CDN, sem eval)."""

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "clients" / "viewer3d"
VENDOR = ROOT / "clients" / "web-fallback" / "vendor"
BUNDLE = VENDOR / "viewer3d.js"
MANIFEST = json.loads((VENDOR / "viewer3d.manifest.json").read_text("utf-8"))


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def test_manifest_hash_matches_the_committed_bundle() -> None:
    data = BUNDLE.read_bytes()

    assert MANIFEST["sha256"] == _sha(data)
    assert MANIFEST["bytes"] == len(data)


def test_manifest_source_hashes_match_the_sources_regardless_of_line_endings() -> None:
    for name, expected in MANIFEST["sources"].items():
        text = (SRC / "src" / name).read_text("utf-8").replace("\r\n", "\n")
        assert _sha(text.encode()) == expected, f"{name} mudou sem refazer o build (npm run build)"
    assert set(MANIFEST["sources"]) == {p.name for p in (SRC / "src").glob("*.js")}


def test_dependencies_are_pinned_exactly_and_match_the_lockfile_and_manifest() -> None:
    package = json.loads((SRC / "package.json").read_text("utf-8"))
    lock = json.loads((SRC / "package-lock.json").read_text("utf-8"))

    assert package["dependencies"] == {"three": MANIFEST["three"]["version"]}
    assert package["devDependencies"] == {"esbuild": MANIFEST["esbuild"]}
    assert lock["packages"]["node_modules/three"]["version"] == MANIFEST["three"]["version"]
    assert lock["packages"]["node_modules/three"]["integrity"].startswith("sha512-")
    assert lock["packages"]["node_modules/esbuild"]["version"] == MANIFEST["esbuild"]
    assert MANIFEST["three"]["license"] == "MIT"
    assert (VENDOR / "THREE-LICENSE.txt").read_text("utf-8").startswith("The MIT License")


def test_bundle_has_no_cdn_references_and_no_dynamic_code_execution() -> None:
    """A CSP do painel e `script-src 'self'` (sem 'unsafe-eval'): nada de eval/new Function."""
    text = BUNDLE.read_text("utf-8")

    for host in ("unpkg.com", "jsdelivr", "cdnjs", "googleapis", "gstatic"):
        assert host not in text
    assert not re.search(r"\beval\s*\(", text)
    assert "new Function(" not in text


def test_the_panel_code_never_writes_html_from_strings() -> None:
    """Todo texto da API entra via textContent (comentarios podem citar innerHTML; atribuicoes, nunca)."""
    sinks = re.compile(r"\.(innerHTML|outerHTML)\s*=|insertAdjacentHTML\s*\(|document\.write\s*\(")
    files = [*(SRC / "src").glob("*.js"), ROOT / "clients" / "web-fallback" / "app.js"]
    for path in files:
        assert not sinks.search(path.read_text("utf-8")), path.name


def test_index_loads_the_local_bundle_before_the_app_and_nothing_remote() -> None:
    html = (ROOT / "clients" / "web-fallback" / "index.html").read_text("utf-8")

    assert html.index('src="vendor/viewer3d.js"') < html.index('src="app.js"')
    assert not re.search(r'(src|href)="https?://', html)
