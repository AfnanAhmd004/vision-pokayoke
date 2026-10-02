import json

import pytest

from pokayoke import DEFECTS, Station, golden_image, inspect, render

G = golden_image()


def test_good_parts_pass():
    assert all(inspect(render("ok", seed=s), G).passed for s in range(20))


@pytest.mark.parametrize("defect,check", [("missing_hole", "hole_count"), ("missing_connector", "connector"),
                                          ("flipped", "orientation"), ("misplaced", "position"),
                                          ("wrong_variant", "hole_pattern"), ("scratch", "surface")])
def test_each_defect_is_caught_by_the_right_check(defect, check):
    results = [inspect(render(defect, seed=s), G) for s in range(15)]
    assert sum(not r.passed for r in results) >= 14
    assert sum(check in r.failed_checks for r in results) >= 12


def test_station_logs_and_stops_line(tmp_path):
    log = tmp_path / "trace.jsonl"
    st = Station(log_path=str(log), max_consecutive_rejects=2)
    st.process("SN1", render("ok", 1))
    st.process("SN2", render("missing_connector", 2))
    rec = st.process("SN3", render("missing_connector", 3))
    assert rec.get("line_stop") and st.stopped
    with pytest.raises(RuntimeError):
        st.process("SN4", render("ok", 4))
    lines = [json.loads(l) for l in log.read_text().splitlines()]
    assert [l["serial"] for l in lines] == ["SN1", "SN2", "SN3"] and "connector_brightness" in lines[0]["measurements"]


def test_presence_sensor_layer():
    rec = Station().process("SN9", render("ok", 9), presence_sensor=False)
    assert rec["failed_checks"] == ["presence_sensor"]
