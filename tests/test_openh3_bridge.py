"""Exercise real compiler output through the real Director planner, without a GPU."""
import importlib.util
import json
from pathlib import Path
import sys
import types

import pytest

ROOT = Path(__file__).resolve().parents[1]
PKG = "openh3_bridge_test_pack"
pkg = types.ModuleType(PKG)
pkg.__path__ = [str(ROOT)]
sys.modules[PKG] = pkg
bridge = importlib.import_module(PKG + ".director.openh3_bridge")
writer = importlib.import_module(PKG + ".nodes.openh3_clips")


def manifest():
    from h3ir.clips import ClipRequest, compile_clips
    from h3ir.models import Brief, Mode
    class Backend:
        cfg = types.SimpleNamespace(model="test")
        def require_available(self): pass
        def server_version(self): return "test"
    docs = compile_clips([
        ClipRequest("arrival", Brief(intent="A courier arrives.", seconds=5, shots=1,
                                     canvas=(864, 480), mode=Mode.T2VA)),
        ClipRequest("lamp", Brief(intent="The courier lights a lamp.", seconds=8, shots=1,
                                  canvas=(864, 480), mode=Mode.T2VA)),
    ], backend=Backend(), llm=False)
    return [doc.to_dict() for doc in docs]


def test_real_compiler_to_real_director_plan(monkeypatch):
    monkeypatch.setitem(sys.modules, "folder_paths", types.ModuleType("folder_paths"))
    utils = types.ModuleType("comfy.utils")
    def no_resize(*a, **kw):
        pytest.fail("Text-only planning unexpectedly resized media")
    utils.common_upscale = no_resize
    monkeypatch.setitem(sys.modules, "comfy", types.ModuleType("comfy"))
    monkeypatch.setitem(sys.modules, "comfy.utils", utils)
    clips = manifest()
    payload = bridge.pack_compiled_clips(clips)
    encoded, timeline = bridge.resolve_compiled_timeline(payload, task_key="t2v", global_prompt="")
    inputs = importlib.import_module(PKG + ".director.director_inputs")
    planner = importlib.import_module(PKG + ".director.plan")
    encoded, normalized = inputs.prepare_timeline_for_director_inputs(
        encoded, task_type="t2v", director_inputs=payload, motion_context_enabled=False)
    plan = planner.build_director_plan(encoded, global_task_type="t2v",
                                       global_prompt="", total_frames=316,
                                       frame_rate=24, width=864, height=480, ref_max_size=864)
    inputs.apply_director_inputs_to_plan(plan, normalized)
    assert [s.prompt for s in plan.segments] == [c["prompt"] for c in clips]
    assert [(s.start_frame, s.end_frame) for s in plan.segments] == [(0, 124), (124, 316)]
    assert timeline["totalFrames"] == 316


def test_plain_director_inputs_are_unchanged():
    assert bridge.resolve_compiled_timeline({"groups": {}}, task_key="i2v", global_prompt="x") is None


@pytest.mark.parametrize("mode,prompt", [("mixed", ""), ("r2v", ""), ("t2v", "extra")])
def test_contradictory_director_settings_are_refused(mode, prompt):
    with pytest.raises(ValueError):
        bridge.resolve_compiled_timeline(bridge.pack_compiled_clips(manifest()),
                                         task_key=mode, global_prompt=prompt)


def test_prompt_tampering_is_refused():
    payload = bridge.pack_compiled_clips(manifest())
    payload["groups"][1]["prompt"] = "changed"
    with pytest.raises(ValueError, match="differ"):
        bridge.resolve_compiled_timeline(payload, task_key="t2v", global_prompt="")


@pytest.mark.parametrize("value", ['{}', '[]', '[{"intent":"fox","seconds":0}]',
    '[{"intent":"fox","seconds":5,"assets":[]}]',
    '[{"intent":"fox","seconds":5,"dialogue":"hello"}]',
    '[{"id":"x","intent":"fox","seconds":5},{"id":"x","intent":"dog","seconds":5}]'])
def test_bad_clip_json(value):
    with pytest.raises(ValueError):
        writer.parse_clips(value)


def test_node_schema():
    schema = writer.MiniMaxH3OpenH3Clips.INPUT_TYPES()
    assert schema["required"]["llm_url"][1]["default"] == "http://127.0.0.1:1234/v1"
    assert writer.MiniMaxH3OpenH3Clips.RETURN_TYPES[0] == "MMX_MOTION_DIR_INPUTS"


def test_node_executes_real_compiler_and_reports_fallback(monkeypatch):
    import h3ir.backend
    import h3ir.clips
    real_compile = h3ir.clips.compile_clips
    class OfflineBackend:
        def __init__(self, cfg):
            self.cfg = cfg.llm
        def require_available(self): pass
        def server_version(self): return "offline"
        def close(self): self.closed = True
    monkeypatch.setattr(h3ir.backend, "Backend", OfflineBackend)
    monkeypatch.setattr(h3ir.clips, "compile_clips", lambda *a, **kw: real_compile(*a, **kw, llm=False))
    result = writer.MiniMaxH3OpenH3Clips().compile(
        writer.EXAMPLE_CLIPS, "Yellow raincoat.", "http://127.0.0.1:1234/v1",
        "test-model", 864, 480, "restrained", "", 7, 10)
    payload, clips_json, report = result["result"]
    assert len(json.loads(clips_json)) == 2
    assert payload["openh3_timeline"]["totalFrames"] == 248
    assert "DRAFT FALLBACK" in report
    assert result["ui"]["text"] == [report]
    assert result["ui"]["compiled_clips"] == [clips_json]


def test_importing_node_does_not_require_optional_compiler():
    import subprocess
    code = '''
import importlib, sys, types
class Block:
    def find_spec(self, name, *args):
        if name == "h3ir" or name.startswith("h3ir."):
            raise AssertionError("compiler imported during node registration")
sys.meta_path.insert(0, Block())
p = types.ModuleType("isolated_pack")
p.__path__ = [sys.argv[1]]
sys.modules[p.__name__] = p
m = importlib.import_module("isolated_pack.nodes.openh3_clips")
assert m.MiniMaxH3OpenH3Clips.INPUT_TYPES()
'''
    subprocess.run([sys.executable, "-c", code, str(ROOT)], check=True)


def test_examples_match_node_contract():
    api = json.loads((ROOT / "example_workflows/openh3_two_clips.api.json").read_text(encoding="utf-8"))
    assert api["6"]["inputs"]["director_inputs"] == ["5", 0]
    assert api["6"]["inputs"]["global_prompt"] == ""
    assert set(api["5"]["inputs"]) == set(writer.MiniMaxH3OpenH3Clips.INPUT_TYPES()["required"])
    assert len(writer.parse_clips(api["5"]["inputs"]["clips_json"])) == 2
