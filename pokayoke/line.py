"""Station logic: sensor + vision poka-yoke layers, traceability log and a line-stop interlock."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field

from .inspect import Spec, golden_image, inspect


@dataclass
class Station:
    log_path: str | None = None
    max_consecutive_rejects: int = 3
    spec: Spec = field(default_factory=Spec)

    def __post_init__(self):
        self.golden = golden_image()
        self.consecutive = 0
        self.stopped = False
        self.records: list[dict] = []

    def process(self, serial: str, image, presence_sensor: bool = True) -> dict:
        """Layer 1: presence sensor. Layer 2: vision checks. Layer 3: interlock on repeated rejects."""
        if self.stopped:
            raise RuntimeError("line stopped: clear the fault and call reset()")
        if not presence_sensor:
            rec = {"serial": serial, "passed": False, "failed_checks": ["presence_sensor"], "measurements": {}}
        else:
            rec = {"serial": serial, **inspect(image, self.golden, self.spec).to_record()}
        rec["timestamp"] = time.time()
        self.consecutive = 0 if rec["passed"] else self.consecutive + 1
        if self.consecutive >= self.max_consecutive_rejects:
            self.stopped = True  # likely a systematic fault (fixture, feeder, wrong variant loaded)
            rec["line_stop"] = True
        self.records.append(rec)
        if self.log_path:
            with open(self.log_path, "a") as f:
                f.write(json.dumps(rec) + "\n")
        return rec

    def reset(self):
        self.stopped, self.consecutive = False, 0
