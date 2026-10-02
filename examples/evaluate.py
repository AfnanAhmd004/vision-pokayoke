"""Inspect 700 synthetic parts (100 per class) and report detection per defect type.

    python examples/evaluate.py --plot   # writes docs/demo.png
"""
import argparse
from collections import Counter, defaultdict

from pokayoke import DEFECTS, golden_image, inspect, render

ap = argparse.ArgumentParser()
ap.add_argument("--plot", action="store_true")
args = ap.parse_args()

golden = golden_image()
by_class, reasons = defaultdict(list), defaultdict(Counter)
for d in DEFECTS:
    for s in range(100):
        r = inspect(render(d, seed=s), golden)
        by_class[d].append(r.passed)
        reasons[d].update(r.failed_checks or ["-"])

print(f"{'class':<20}{'pass rate':>10}   most common failed check")
for d in DEFECTS:
    rate = sum(by_class[d]) / len(by_class[d])
    print(f"{d:<20}{rate:>10.0%}   {reasons[d].most_common(1)[0][0]}")
false_reject = 1 - sum(by_class["ok"]) / 100
escapes = sum(sum(by_class[d]) for d in DEFECTS[1:]) / (100 * (len(DEFECTS) - 1))
print(f"\nfalse reject rate (good parts rejected): {false_reject:.1%}")
print(f"escape rate (defective parts passed):    {escapes:.1%}")

if args.plot:
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, len(DEFECTS), figsize=(16, 2.6))
    for ax, d in zip(axes, DEFECTS):
        img = render(d, seed=3)
        r = inspect(img, golden)
        ax.imshow(img, cmap="gray", vmin=0, vmax=255); ax.set_xticks([]); ax.set_yticks([])
        ax.set_title(f"{d}\n{'PASS' if r.passed else 'FAIL: ' + ','.join(r.failed_checks)}", fontsize=8,
                     color="green" if r.passed else "red")
    fig.tight_layout(); fig.savefig("docs/demo.png", dpi=100)
    print("wrote docs/demo.png")
