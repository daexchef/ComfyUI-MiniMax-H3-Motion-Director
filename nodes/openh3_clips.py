"""Local LLM clip writing without loading H3 weights or conditioning."""
from __future__ import annotations

import json
import math
from dataclasses import replace

from ..director.openh3_bridge import pack_compiled_clips

EXAMPLE_CLIPS = json.dumps([
    {"id": "arrival", "intent": "A courier in a yellow raincoat arrives at a quiet lighthouse.", "seconds": 5},
    {"id": "lamp", "intent": "The courier climbs the lighthouse stairs and lights the lamp.", "seconds": 5},
], indent=2)


def parse_clips(text):
    rows = json.loads(text)
    if not isinstance(rows, list) or not 1 <= len(rows) <= 100:
        raise ValueError("clips_json must be a list of 1–100 clips.")
    seen = set()
    for index, row in enumerate(rows, 1):
        if not isinstance(row, dict) or set(row) - {"id", "intent", "seconds", "dialogue"}:
            raise ValueError(f"Clip {index}: use id, intent, seconds and optional dialogue only.")
        row.setdefault("id", f"clip-{index}")
        if not isinstance(row["id"], str) or not row["id"].strip() or row["id"] in seen:
            raise ValueError(f"Clip {index}: IDs must be non-empty and unique.")
        seen.add(row["id"])
        if not isinstance(row.get("intent"), str) or not row["intent"].strip():
            raise ValueError(f"Clip {index}: intent is required.")
        seconds = row.get("seconds")
        if isinstance(seconds, bool) or not isinstance(seconds, (int, float)) or not math.isfinite(seconds) or not 1.2 <= seconds <= 15:
            raise ValueError(f"Clip {index}: seconds must be between 1.2 and 15.")
        dialogue = row.get("dialogue", [])
        if not isinstance(dialogue, list) or any(not isinstance(line, str) or not line.strip() for line in dialogue):
            raise ValueError(f"Clip {index}: dialogue must be a list of non-empty strings.")
    return rows


class MiniMaxH3OpenH3Clips:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "clips_json": ("STRING", {"multiline": True, "default": EXAMPLE_CLIPS}),
            "shared_context": ("STRING", {"multiline": True, "default": "Same courier throughout: yellow raincoat, brown satchel. Overcast coastal evening."}),
            "llm_url": ("STRING", {"default": "http://127.0.0.1:1234/v1"}),
            "llm_model": ("STRING", {"default": "qwen/qwen3.5-9b"}),
            "width": ("INT", {"default": 864, "min": 32, "max": 8192, "step": 32}),
            "height": ("INT", {"default": 480, "min": 32, "max": 8192, "step": 32}),
            "creativity": (["restrained", "balanced", "bold", "extreme"], {"default": "balanced"}),
            "direction": ("STRING", {"multiline": True, "default": ""}),
            "seed": ("INT", {"default": 7, "min": 0, "max": 0xFFFFFFFF}),
            "timeout_s": ("FLOAT", {"default": 600, "min": 10, "max": 3600}),
        }}

    RETURN_TYPES = ("MMX_MOTION_DIR_INPUTS", "STRING", "STRING")
    RETURN_NAMES = ("director_inputs", "compiled_clips_json", "report")
    FUNCTION = "compile"
    OUTPUT_NODE = True
    CATEGORY = "MiniMaxH3/Director"
    DESCRIPTION = "Compile individual T2V clip prompts with a local LLM through OpenH3-IR. Connect directly to Director.director_inputs. The clip list owns this run's timeline, duration and canvas."

    def compile(self, clips_json, shared_context, llm_url, llm_model, width, height,
                creativity, direction, seed, timeout_s):
        rows = parse_clips(clips_json)
        if width % 32 or height % 32:
            raise ValueError("Width and height must be multiples of 32.")
        if not llm_model.strip():
            raise ValueError("Name the LM Studio model explicitly; the bridge never chooses one.")
        try:
            from h3ir.clips import ClipRequest, compile_clips
            from h3ir.backend import Backend
            from h3ir.config import get_config
            from h3ir.models import Brief, DialogueLine, Mode
        except ImportError as exc:
            raise RuntimeError("Install the open-h3-ir integration fork in ComfyUI's Python. See docs/OPENH3_INTEGRATION.md.") from exc
        cfg = get_config()
        cfg = replace(cfg, llm=replace(cfg.llm, base_url=llm_url.rstrip("/"),
                                     model=llm_model.strip(), timeout_s=timeout_s))
        requests = [ClipRequest(row["id"], Brief(
            intent=row["intent"], seconds=row["seconds"], aspect=f"{width}:{height}",
            canvas=(width, height), mode=Mode.T2VA, shots=1, creativity=creativity,
            dialogue=[DialogueLine(line) for line in row.get("dialogue", [])],
            director_profile={"name": "Workflow direction", "notes": direction} if direction.strip() else None,
        )) for row in rows]
        backend = Backend(cfg)
        try:
            compiled = compile_clips(requests, backend=backend, seed=seed,
                                     shared_context=shared_context)
        finally:
            backend.close()
        clips = [clip.to_dict() for clip in compiled]
        payload = pack_compiled_clips(clips)
        report = [f"OpenH3-IR: {len(clips)} clips · {llm_model} · {llm_url}",
                  "Clip list controls this run's timeline and canvas. Director UI cards are not rewritten."]
        for clip in clips:
            report.append(f"{clip['id']}: {clip['requested_seconds']:g}s requested → {clip['frames']} frames / {clip['seconds']:.3f}s; source={clip['source']}")
            if clip["fallback_reason"]:
                report.append("DRAFT FALLBACK: " + clip["fallback_reason"])
            report.extend(clip["findings"])
        compiled_json = json.dumps(clips, indent=2, ensure_ascii=False)
        report_text = "\n".join(report)
        return {"ui": {"text": [report_text], "compiled_clips": [compiled_json]},
                "result": (payload, compiled_json, report_text)}
