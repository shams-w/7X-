"""Sanity checks for the Make.com blueprint (structure + safety defaults)."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "make"))

import build_blueprint  # noqa: E402

BLUEPRINT = ROOT / "make" / "7X_Executive_Connect.blueprint.json"


def _walk(flow, out):
    for m in flow:
        out.append(m)
        for r in m.get("routes", []):
            _walk(r["flow"], out)
        _walk(m.get("onerror", []), out)
    return out


def test_committed_blueprint_matches_builder():
    assert json.loads(BLUEPRINT.read_text(encoding="utf-8")) == build_blueprint.build()


def test_module_ids_unique():
    ids = [m["id"] for m in _walk(build_blueprint.build()["flow"], [])]
    assert len(ids) == len(set(ids))


def test_blueprint_defaults_to_test_mode():
    config = build_blueprint.build()["flow"][0]
    variables = {v["name"]: v["value"] for v in config["mapper"]["variables"]}
    assert variables["APP_MODE"] == "TEST"
    assert "Asia/Dubai" in variables["TODAY_MMDD"]


def test_recipient_is_test_phone_unless_production():
    row = build_blueprint.build()["flow"][2]
    recipient = next(v["value"] for v in row["mapper"]["variables"] if v["name"] == "recipient")
    assert recipient.startswith('{{if(1.APP_MODE = "PRODUCTION";')
    assert recipient.endswith("1.TEST_PHONE_NUMBER)}}")
    sends = [m for m in _walk(build_blueprint.build()["flow"], [])
             if m["module"] == build_blueprint.M_WA_TEMPLATE]
    assert len(sends) == 2 and all(m["mapper"]["to"] == "{{3.recipient}}" for m in sends)
    assert {m["mapper"]["template"] for m in sends} == {"employee_birthday", "work_anniversary"}


def test_every_send_has_duplicate_check_and_claim():
    router = build_blueprint.build()["flow"][3]
    for route in router["routes"]:
        modules = [m["module"] for m in route["flow"]]
        assert modules[:3] == [build_blueprint.M_DS_GET, build_blueprint.M_DS_ADD,
                               build_blueprint.M_WA_TEMPLATE]
        assert route["flow"][1]["mapper"]["overwrite"] is False


def test_no_secrets_in_blueprint():
    text = BLUEPRINT.read_text(encoding="utf-8")
    assert "EAA" not in text  # Meta tokens start with EAA
    assert "+9715" not in text  # no real phone numbers
