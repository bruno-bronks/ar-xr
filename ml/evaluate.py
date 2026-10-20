"""Avalia o detector e compara com QR e com a regra do simulador (SPEC-011, REQ-CV-002/003).

Uso (no ambiente de ML): ml/.venv-ml/Scripts/python ml/evaluate.py --weights ml/runs/<nome>/weights/best.pt
Grava docs/evidence/phase-5/cv-report-<tag>.md e cv-summary-<tag>.json. Roda so sobre o split de TESTE.
"""

import argparse
import csv
import json
import shutil
import sys
import time
from pathlib import Path
from typing import Any

import cv2

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [
    str(ROOT / "ml"),
    str(ROOT / "packages" / "domain" / "src"),
    str(ROOT / "packages" / "storage" / "src"),
]

from spatial_cv.baselines import decode_qr, lamp_state_by_color  # noqa: E402
from spatial_cv.compare import (  # noqa: E402
    STATE_CLASSES,
    ImageResult,
    by_condition,
    confusion,
    render_comparison,
)
from spatial_cv.scene import CLASSES, CONDITIONS  # noqa: E402
from spatial_cv.truth import LAMP_CLASS  # noqa: E402
from spatial_domain.status import Status  # noqa: E402

EQUIPMENT_CLASSES = CLASSES[:3]
LAMP_CLASSES = CLASSES[3:]
CONF = 0.25  # limiar de decisao para identificar/estado (o mAP usa conf baixa)


def _best(boxes: Any, names: tuple[str, ...]) -> str | None:
    best: tuple[float, str] | None = None
    for cls, conf in zip(boxes.cls.tolist(), boxes.conf.tolist(), strict=True):
        name = CLASSES[int(cls)]
        if name in names and (best is None or conf > best[0]):
            best = (float(conf), name)
    return best[1] if best else None


def detection_metrics(
    model: Any, root: Path, rows: list[dict[str, str]], imgsz: int
) -> dict[str, Any]:
    """mAP/precisao/revocacao do YOLO, geral e por condicao, via `model.val` em subconjuntos do TESTE."""
    out: dict[str, Any] = {}
    groups = {"TOTAL": rows, **{c: [r for r in rows if r["condition"] == c] for c in CONDITIONS}}
    for name, subset in groups.items():
        base = root / "_eval" / name
        for sub in ("images/val", "labels/val"):
            shutil.rmtree(base / sub, ignore_errors=True)
            (base / sub).mkdir(parents=True, exist_ok=True)
        for r in subset:
            image = root / r["image"]
            label = root / r["image"].replace("images", "labels").replace(".jpg", ".txt")
            shutil.copy(image, base / "images/val" / image.name)
            shutil.copy(label, base / "labels/val" / label.name)
        names = "\n".join(f"  {i}: {n}" for i, n in enumerate(CLASSES))
        yaml = base / "data.yaml"
        yaml.write_text(
            f"path: {base.resolve().as_posix()}\ntrain: images/val\nval: images/val\nnames:\n{names}\n",
            "utf-8",
        )
        res = model.val(
            data=str(yaml),
            imgsz=imgsz,
            conf=0.001,
            iou=0.6,
            device="cpu",
            workers=0,
            plots=False,
            verbose=False,
            split="val",
        )
        box = res.box
        per_class = {
            res.names[int(c)]: {
                "p": float(box.p[i]),
                "r": float(box.r[i]),
                "ap50": float(box.ap50[i]),
                "ap": float(box.ap[i]),
            }
            for i, c in enumerate(box.ap_class_index)
        }
        out[name] = {
            "images": len(subset),
            "precision": float(box.mp), "recall": float(box.mr), "map50": float(box.map50), "map50_95": float(box.map),
            "per_class": per_class,
        }  # fmt: skip
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", default=str(ROOT / "ml" / "data" / "synth"))
    parser.add_argument("--weights", required=True)
    parser.add_argument("--imgsz", type=int, default=480)
    parser.add_argument("--out", default=str(ROOT / "docs" / "evidence" / "phase-5"))
    parser.add_argument(
        "--tag", default="scratch", help="scratch | pretrained (nome dos arquivos de saida)"
    )
    parser.add_argument(
        "--origin",
        default="YOLOv8n treinado do zero em CPU (sem pesos pré-treinados)",
        help="como o modelo foi obtido (texto do relatório)",
    )
    parser.add_argument(
        "--note", default="", help="texto livre (ex.: epocas, observacoes) para o relatorio"
    )
    args = parser.parse_args()

    from ultralytics import YOLO

    root = Path(args.data_root)
    model = YOLO(args.weights)
    with (root / "manifest.csv").open(encoding="utf-8", newline="") as fh:
        rows = [r for r in csv.DictReader(fh) if r["split"] == "test"]

    results: list[ImageResult] = []
    t_qr = t_yolo = t_hsv = 0.0
    for r in rows:
        image = cv2.imread(str(root / r["image"]))
        t0 = time.perf_counter()
        qr = decode_qr(image)
        t1 = time.perf_counter()
        pred = model.predict(image, imgsz=args.imgsz, conf=CONF, device="cpu", verbose=False)[0]
        t2 = time.perf_counter()
        hsv = lamp_state_by_color(image)
        t3 = time.perf_counter()
        t_qr, t_yolo, t_hsv = t_qr + (t1 - t0), t_yolo + (t2 - t1), t_hsv + (t3 - t2)
        results.append(
            ImageResult(
                condition=r["condition"], truth_type=r["equipment_type"], truth_qr=r["qr_text"],
                truth_state=LAMP_CLASS[Status(r["status"])],
                lamp_visible=bool(int(r["lamp_visible"])), qr_text=qr,
                yolo_type=_best(pred.boxes, EQUIPMENT_CLASSES), yolo_state=_best(pred.boxes, LAMP_CLASSES),
                hsv_state=hsv,
            )
        )  # fmt: skip

    detection = detection_metrics(model, root, rows, args.imgsz)
    n = len(results)
    latency = {"qr_ms": 1000 * t_qr / n, "yolo_ms": 1000 * t_yolo / n, "hsv_ms": 1000 * t_hsv / n}
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"cv-report-{args.tag}.md").write_text(
        render_report(args, rows, results, detection, latency), "utf-8", newline="\n"
    )
    (out / f"cv-summary-{args.tag}.json").write_text(
        json.dumps({"detection": detection, "latency_ms": latency, "images": n, "conf": CONF}, indent=2, ensure_ascii=False) + "\n",
        "utf-8", newline="\n",
    )  # fmt: skip
    print(f"relatorio em {out / f'cv-report-{args.tag}.md'} ({n} imagens de teste)")
    return 0


def render_report(
    args: argparse.Namespace,
    rows: list[dict[str, str]],
    results: list[ImageResult],
    detection: dict[str, Any],
    latency: dict[str, float],
) -> str:
    lines = [
        "# Visão computacional (Fase 5) — PoC com dataset SINTÉTICO — gerado por `ml/evaluate.py`",
        "",
        "> **Escopo e limites.** Dataset **sintético** (equipamentos estilizados + QR + lâmpada), gerado por script "
        "determinístico; **não há foto real**. Os números mostram o pipeline e a comparação metodológica, **não** o "
        f"desempenho em campo. Detector: {args.origin}. A visão é **assistiva**: "
        "não define status nem alertas, e não faz diagnóstico. O YOLO identifica o **tipo** do equipamento; isso equivale ao "
        "id só porque o seed tem um equipamento por tipo. " + args.note,
        "",
        f"Imagens de teste: **{len(results)}** ({len(results) // len(CONDITIONS)} por condição x {len(CONDITIONS)} condições), "
        f"limiar de decisão {CONF}. Latência média por imagem em CPU: QR {latency['qr_ms']:.1f} ms · YOLO {latency['yolo_ms']:.1f} ms · baseline HSV {latency['hsv_ms']:.1f} ms.",
        "",
        "## Detecção (mAP, split de teste; `model.val`, conf 0,001)",
        "",
        "| Condição | imagens | precisão | revocação | mAP50 | mAP50-95 |",
        "|---|---|---|---|---|---|",
    ]
    for name, d in detection.items():
        lines.append(
            f"| {name} | {d['images']} | {d['precision']:.3f} | {d['recall']:.3f} | {d['map50']:.3f} | {d['map50_95']:.3f} |"
        )
    lines += [
        "",
        "Por classe (TOTAL):",
        "",
        "| Classe | precisão | revocação | AP50 | AP50-95 |",
        "|---|---|---|---|---|",
    ]
    for cls, v in detection["TOTAL"]["per_class"].items():
        lines.append(f"| {cls} | {v['p']:.3f} | {v['r']:.3f} | {v['ap50']:.3f} | {v['ap']:.3f} |")
    lines += [
        "",
        "## Comparação mensurável (mesmas imagens de teste)",
        "",
        *render_comparison(results),
    ]
    for title, pick in (("YOLO", lambda r: r.yolo_state), ("baseline HSV", lambda r: r.hsv_state)):
        matrix = confusion(results, pick)
        lines += ["", f"### Matriz de confusão do estado — {title} (linhas = verdade da regra; colunas = previsto)", "",
                  "| verdade \\ previsto | " + " | ".join((*STATE_CLASSES, "(nada)")) + " |", "|---|---|---|---|---|"]  # fmt: skip
        for truth, row in matrix.items():
            lines.append(
                f"| {truth} | " + " | ".join(str(row[c]) for c in (*STATE_CLASSES, "(nada)")) + " |"
            )
    grouped = by_condition(results)
    lines += ["", "## Leitura honesta", "",
              "- Só há afirmação de superioridade quando o teste de McNemar exato dá p < 0,05; caso contrário o relatório diz *sem diferença detectável*.",
              "- O baseline de cor é de propósito simples; os distratores (lâmpada azul/branca, placa vermelha, folhagem verde) foram escolhidos por mim e influenciam o resultado.",
              "- Oclusão pode esconder a lâmpada: nesses casos o estado é impossível para qualquer método visual (a verdade continua sendo a da regra).",
              f"- Condições avaliadas: {', '.join(grouped)}."]  # fmt: skip
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
