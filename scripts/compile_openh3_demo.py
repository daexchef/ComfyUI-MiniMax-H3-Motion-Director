"""Live prompt-only smoke test. No ComfyUI server or H3 weights required."""
import argparse
import importlib
import json
from pathlib import Path
import sys
import time
import types

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--url", default="http://127.0.0.1:1234/v1")
parser.add_argument("--model", required=True)
parser.add_argument("--out", type=Path, required=True)
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
pkg = types.ModuleType("openh3_demo_pack")
pkg.__path__ = [str(root)]
sys.modules[pkg.__name__] = pkg
module = importlib.import_module(pkg.__name__ + ".nodes.openh3_clips")
start = time.monotonic()
result = module.MiniMaxH3OpenH3Clips().compile(
    module.EXAMPLE_CLIPS,
    "Same courier throughout: yellow raincoat, brown satchel. Overcast coastal evening.",
    args.url, args.model, 864, 480, "restrained", "", 7, 600,
)
payload, clips, report = result["result"]
args.out.mkdir(parents=True, exist_ok=True)
(args.out / "compiled-clips.json").write_text(clips, encoding="utf-8")
(args.out / "timeline.json").write_text(json.dumps(payload["openh3_timeline"], indent=2), encoding="utf-8")
(args.out / "report.txt").write_text(report, encoding="utf-8")
print(report)
print(f"Elapsed: {time.monotonic() - start:.2f}s. Artifacts: {args.out}")
