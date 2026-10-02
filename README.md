# vision-pokayoke

**Layered machine-vision error-proofing (poka-yoke)** for an automated assembly cell. Each part is located, aligned to its nominal frame, and checked for orientation, fixture position, hole pattern, connector presence and surface defects. Every result is written to a **traceability log**, and repeated rejects trigger a **line-stop interlock**.

![One example of each class](docs/demo.png)

## Inspection layers

| Layer | Check | Method | Catches |
|---|---|---|---|
| Sensor | `presence_sensor` | discrete sensor input | empty nest |
| Vision | `orientation` | min-area rectangle pose, plus the position of the asymmetric notch | part loaded 180° or mirrored |
| Vision | `position` | offset of the part centre from the fixture datum | mis-seated part |
| Vision | `hole_count` / `hole_pattern` | blobs filtered by size, aspect and fill ratio in the part frame, matched to nominal hole positions | undrilled hole, **wrong product variant** |
| Vision | `connector` | ROI brightness at the expected location | missing component |
| Vision | `surface` | aligned difference against a golden image, with expected feature edges masked | scratches and marks |
| Station | interlock | N consecutive rejects stop the line | systematic faults (feeder, fixture, wrong batch) |

Each check reports **why** a part failed and logs its measurements (offset, angle, hole count, connector brightness, defect area) per serial number for traceability and root-cause analysis.

## Run

```bash
pip install -e ".[dev]"
python examples/evaluate.py --plot
pytest
```

100 synthetic parts per class, with pose jitter and sensor noise:

```
class                pass rate   most common failed check
ok                        100%   -
missing_hole                0%   hole_count
missing_connector           0%   connector
flipped                     0%   orientation
misplaced                   0%   position
scratch                     0%   surface
wrong_variant               0%   hole_pattern

false reject rate (good parts rejected): 0.0%
escape rate (defective parts passed):    0.0%
```

Every defect is caught by the *intended* check, which matters for root-cause analysis. An early version flagged scratches as "extra holes" until the hole detector was made shape-aware; the tests now pin each defect to its check.

On real lines, lighting, reflections and part variation make the thresholds the hard part. A golden-image difference is usually complemented by a learned anomaly detector, and limits are set from measured process capability rather than synthetic data.

## License

MIT
