"""Construcao do dataset YOLO sintetico (SPEC-011, REQ-CV-001): determinismo, splits disjuntos e
estratificacao por condicao/equipamento/estado."""

import csv
from dataclasses import dataclass
from pathlib import Path

import cv2

from spatial_cv.scene import CLASSES, CONDITIONS, render_scene, yolo_lines
from spatial_cv.truth import EQUIPMENT_IDS, LAMP_STATUSES

SPLIT_SEED_BASE = {"train": 0, "val": 1_000_000, "test": 2_000_000}  # faixas de semente disjuntas
DEFAULT_PER_CONDITION = {"train": 160, "val": 30, "test": 60}
MANIFEST_COLUMNS = [
    "split", "image", "seed", "condition", "equipment_id", "equipment_type", "qr_text",
    "status", "lamp_visible", "temperature", "vibration",
]  # fmt: skip


@dataclass(frozen=True)
class SceneSpec:
    split: str
    index: int
    seed: int
    condition: str
    equipment_id: str
    status_index: int


def plan_split(split: str, per_condition: int) -> list[SceneSpec]:
    """Plano deterministico: cada condicao recebe `per_condition` cenas, ciclando equipamento e
    estado de forma balanceada (3 x 3 = 9 combinacoes)."""
    if split not in SPLIT_SEED_BASE:
        raise ValueError(f"unknown split: {split}")
    specs: list[SceneSpec] = []
    index = 0
    for condition in CONDITIONS:
        for k in range(per_condition):
            specs.append(
                SceneSpec(
                    split,
                    index,
                    SPLIT_SEED_BASE[split] + index,
                    condition,
                    EQUIPMENT_IDS[k % len(EQUIPMENT_IDS)],
                    (k // len(EQUIPMENT_IDS)) % len(LAMP_STATUSES),
                )
            )
            index += 1
    return specs


def build_dataset(root: Path, per_condition: dict[str, int] | None = None) -> Path:
    """Gera imagens, rotulos YOLO, `manifest.csv` e `data.yaml` sob `root`. Devolve o data.yaml."""
    counts = {**DEFAULT_PER_CONDITION, **(per_condition or {})}
    root.mkdir(parents=True, exist_ok=True)
    manifest_rows: list[dict[str, object]] = []
    for split in SPLIT_SEED_BASE:
        (root / "images" / split).mkdir(parents=True, exist_ok=True)
        (root / "labels" / split).mkdir(parents=True, exist_ok=True)
        for spec in plan_split(split, counts[split]):
            scene = render_scene(
                spec.seed, spec.condition, spec.equipment_id, LAMP_STATUSES[spec.status_index]
            )
            name = f"{split}_{spec.index:05d}"
            cv2.imwrite(
                str(root / "images" / split / f"{name}.jpg"),
                scene.image,
                [cv2.IMWRITE_JPEG_QUALITY, 92],
            )
            (root / "labels" / split / f"{name}.txt").write_text(
                "\n".join(yolo_lines(scene.boxes)) + "\n", "utf-8"
            )
            t = scene.truth
            manifest_rows.append(
                {
                    "split": split, "image": f"images/{split}/{name}.jpg", "seed": spec.seed,
                    "condition": spec.condition, "equipment_id": t.equipment_id,
                    "equipment_type": t.equipment_type, "qr_text": t.qr_text, "status": t.status.value,
                    "lamp_visible": int(scene.lamp_visible), "temperature": f"{t.temperature:.2f}",
                    "vibration": f"{t.vibration:.2f}",
                }
            )  # fmt: skip
    with (root / "manifest.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=MANIFEST_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(manifest_rows)
    names = "\n".join(f"  {i}: {name}" for i, name in enumerate(CLASSES))
    data_yaml = root / "data.yaml"
    data_yaml.write_text(
        f"path: {root.resolve().as_posix()}\ntrain: images/train\nval: images/val\ntest: images/test\nnames:\n{names}\n",
        "utf-8",
    )
    return data_yaml
