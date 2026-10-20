"""SPEC-011 · REQ-CV-001: dataset sintetico deterministico, rotulos validos, splits disjuntos.

Nada aqui e foto real; os testes garantem o gerador, nao a qualidade do detector.
"""

import csv
import hashlib
from pathlib import Path

import numpy as np
import pytest
from spatial_cv.baselines import decode_qr
from spatial_cv.dataset import (
    DEFAULT_PER_CONDITION,
    SPLIT_SEED_BASE,
    build_dataset,
    plan_split,
)
from spatial_cv.scene import CLASSES, CONDITIONS, HEIGHT, WIDTH, render_scene, yolo_lines
from spatial_cv.truth import EQUIPMENT_IDS, LAMP_CLASS, LAMP_STATUSES, sample_truth
from spatial_domain.status import Status
from spatial_storage.seed_data import SEED


def test_same_seed_gives_identical_scene_and_labels() -> None:
    a = render_scene(42, "tilt", "EQ-002", Status.WARNING)
    b = render_scene(42, "tilt", "EQ-002", Status.WARNING)

    assert np.array_equal(a.image, b.image)
    assert a.boxes == b.boxes
    assert a.truth == b.truth


def test_different_seeds_differ() -> None:
    a = render_scene(1, "clean", "EQ-001", Status.NORMAL)
    b = render_scene(2, "clean", "EQ-001", Status.NORMAL)

    assert not np.array_equal(a.image, b.image)


def test_unknown_condition_is_rejected() -> None:
    with pytest.raises(ValueError, match="unknown condition"):
        render_scene(1, "sunny")


@pytest.mark.parametrize("condition", CONDITIONS)
def test_labels_are_valid_in_every_condition(condition: str) -> None:
    for k in range(6):
        scene = render_scene(900 + k, condition, EQUIPMENT_IDS[k % 3], LAMP_STATUSES[k % 3])

        assert scene.image.shape == (HEIGHT, WIDTH, 3)
        assert scene.image.dtype == np.uint8
        assert scene.boxes[0].cls == scene.truth.equipment_type  # equipamento sempre rotulado
        assert (len(scene.boxes) == 2) == scene.lamp_visible
        for box in scene.boxes:
            assert box.cls in CLASSES
            assert 0 <= box.x0 < box.x1 <= WIDTH
            assert 0 <= box.y0 < box.y1 <= HEIGHT
            assert box.area > 4
        if scene.lamp_visible:
            assert scene.boxes[1].cls == LAMP_CLASS[scene.truth.status]


@pytest.mark.parametrize("condition", CONDITIONS)
def test_yolo_lines_are_normalized_and_use_known_classes(condition: str) -> None:
    scene = render_scene(7, condition, "EQ-003", Status.CRITICAL)

    for line in yolo_lines(scene.boxes):
        cls, cx, cy, w, h = line.split()
        assert 0 <= int(cls) < len(CLASSES)
        assert all(0.0 < float(v) <= 1.0 for v in (cx, cy, w, h))


def test_equipment_types_map_one_to_one_to_seeded_org_a_equipment() -> None:
    org_a = [e for e in SEED.equipment if e.org_id == "org-a"]

    assert sorted(EQUIPMENT_IDS) == sorted(e.id for e in org_a)
    types = {render_scene(3, "clean", eq).truth.equipment_type for eq in EQUIPMENT_IDS}
    assert types == {"compressor", "pump", "motor"}
    for eq in EQUIPMENT_IDS:
        assert render_scene(3, "clean", eq).truth.qr_text == next(
            e.marker_id for e in org_a if e.id == eq
        )


@pytest.mark.parametrize("target", LAMP_STATUSES)
def test_lamp_state_truth_comes_from_the_real_status_rule(target: Status) -> None:
    rng = np.random.default_rng(5)
    for eq in EQUIPMENT_IDS:
        truth = sample_truth(rng, eq, target)
        profile = {p.sensor_type: p for p in next(e for e in SEED.equipment if e.id == eq).profile}
        temp = profile["temperature"]

        assert truth.status is target
        if target is Status.NORMAL:
            assert truth.temperature <= temp.warn
        elif target is Status.WARNING:
            assert temp.warn < truth.temperature <= temp.crit
        else:
            assert truth.temperature > temp.crit


def test_unsupported_lamp_status_is_rejected() -> None:
    with pytest.raises(ValueError, match="unsupported"):
        sample_truth(np.random.default_rng(1), "EQ-001", Status.OFFLINE)


def test_plan_is_stratified_by_condition_equipment_and_status() -> None:
    plan = plan_split("test", 18)

    assert len(plan) == 18 * len(CONDITIONS)
    for condition in CONDITIONS:
        rows = [s for s in plan if s.condition == condition]
        assert len(rows) == 18
        assert {eq: sum(1 for s in rows if s.equipment_id == eq) for eq in EQUIPMENT_IDS} == {
            "EQ-001": 6,
            "EQ-002": 6,
            "EQ-003": 6,
        }
        assert [sum(1 for s in rows if s.status_index == i) for i in range(3)] == [6, 6, 6]


def test_seed_ranges_of_the_splits_never_overlap() -> None:
    seeds = {
        split: {s.seed for s in plan_split(split, DEFAULT_PER_CONDITION[split])}
        for split in SPLIT_SEED_BASE
    }

    assert all(len(v) == DEFAULT_PER_CONDITION[k] * len(CONDITIONS) for k, v in seeds.items())
    assert seeds["train"].isdisjoint(seeds["val"])
    assert seeds["train"].isdisjoint(seeds["test"])
    assert seeds["val"].isdisjoint(seeds["test"])


def test_unknown_split_is_rejected() -> None:
    with pytest.raises(ValueError, match="unknown split"):
        plan_split("holdout", 1)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_build_dataset_is_reproducible_consistent_and_leak_free(tmp_path: Path) -> None:
    counts = {"train": 2, "val": 1, "test": 1}
    first = build_dataset(tmp_path / "a", counts)
    second = build_dataset(tmp_path / "b", counts)

    rows = list(csv.DictReader((tmp_path / "a" / "manifest.csv").open(encoding="utf-8")))
    assert len(rows) == (2 + 1 + 1) * len(CONDITIONS)
    assert (tmp_path / "a" / "manifest.csv").read_text("utf-8") == (
        tmp_path / "b" / "manifest.csv"
    ).read_text("utf-8")
    hashes: dict[str, set[str]] = {"train": set(), "val": set(), "test": set()}
    for row in rows:
        image = tmp_path / "a" / row["image"]
        label = tmp_path / "a" / row["image"].replace("images", "labels").replace(".jpg", ".txt")
        assert image.is_file()
        assert label.read_text("utf-8").strip()  # ao menos o equipamento
        assert _sha(image) == _sha(tmp_path / "b" / row["image"])  # byte a byte
        hashes[row["split"]].add(_sha(image))
    assert hashes["train"].isdisjoint(hashes["val"] | hashes["test"])
    assert hashes["val"].isdisjoint(hashes["test"])
    yaml_text = first.read_text("utf-8")
    assert (
        yaml_text.splitlines()[1:] == second.read_text("utf-8").splitlines()[1:]
    )  # so o path difere
    for i, name in enumerate(CLASSES):
        assert f"  {i}: {name}" in yaml_text


def test_qr_is_decodable_on_clean_scenes_and_degrades_with_blur_and_small_scale() -> None:
    def rate(condition: str, n: int) -> float:
        ok = 0
        for k in range(n):
            scene = render_scene(
                5000 + k, condition, EQUIPMENT_IDS[k % 3], LAMP_STATUSES[(k // 3) % 3]
            )
            ok += decode_qr(scene.image) == scene.truth.qr_text
        return ok / n

    clean, blur, small = rate("clean", 18), rate("blur", 12), rate("small", 18)

    assert clean >= 0.75  # o gerador produz QR legivel
    assert blur <= 0.25  # desfoque forte destroi o QR
    assert small < clean  # escala pequena degrada


def test_occlusion_can_hide_the_lamp_and_then_it_has_no_label() -> None:
    scenes = [render_scene(8000 + k, "occlusion", "EQ-001", Status.WARNING) for k in range(40)]

    hidden = [s for s in scenes if not s.lamp_visible]
    assert hidden  # a condicao realmente esconde a lampada em parte das cenas
    assert all(len(s.boxes) == 1 for s in hidden)
    assert any(s.lamp_visible for s in scenes)
