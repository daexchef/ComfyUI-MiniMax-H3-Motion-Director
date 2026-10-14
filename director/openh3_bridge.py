"""CPU-only adapter from compiled OpenH3 clips to the Director input contract."""
from __future__ import annotations

import json


def pack_compiled_clips(clips: list[dict]) -> dict:
    if not clips:
        raise ValueError("OpenH3 returned no clips.")
    groups = {}
    segments = []
    cursor = 0
    for index, clip in enumerate(clips, 1):
        frames = clip["frames"]
        if clip["mode"] != "t2va" or clip["fps"] != 24:
            raise ValueError("The OpenH3 timeline bridge currently accepts 24 FPS T2V clips only.")
        if type(frames) is not int or frames < 5 or frames % 17 != 5:
            raise ValueError(f"Clip {index}: invalid H3 frame count.")
        if not isinstance(clip["prompt"], str) or not clip["prompt"].strip():
            raise ValueError(f"Clip {index}: compiled prompt is empty.")
        groups[index] = {"prompt_connected": True, "prompt": clip["prompt"]}
        segments.append({"id": clip["id"], "start": cursor, "length": frames,
                         "frameCount": frames, "prompt": "", "taskType": "t2v",
                         "refs": [], "referenceVideo": {}})
        cursor += frames
    canvas = clips[0]["canvas"]
    if any(clip["canvas"] != canvas for clip in clips):
        raise ValueError("All clips must use the same canvas.")
    width, height = canvas
    return {"version": 1, "mode": "t2v", "groups": groups,
            "openh3_batch": {"version": 1, "clips": clips},
            "openh3_timeline": {
                "version": 4, "timelineMode": "prompt_batch", "editMode": "segment",
                "frameRate": 24, "width": width, "height": height,
                "refMaxSize": max(canvas), "totalFrames": cursor,
                "global": {"taskType": "t2v", "prompt": "", "refs": []},
                "output": {"mode": "fixed", "width": width, "height": height,
                           "longEdge": max(canvas), "exportMode": "all",
                           "maxExportFrames": 0, "audioMode": "generate"},
                "segments": segments}}


def resolve_compiled_timeline(payload, *, task_key: str, global_prompt: str):
    """Explicit bridge payload owns the run's timeline; ordinary inputs are unchanged."""
    if not isinstance(payload, dict) or "openh3_batch" not in payload:
        return None
    if task_key != "t2v":
        raise ValueError("OpenH3 clip batches require Director T2V mode; Mixed mode is unsupported.")
    if global_prompt.strip():
        raise ValueError("Clear Director global_prompt: OpenH3 already compiled the complete briefs.")
    batch = payload["openh3_batch"]
    if not isinstance(batch, dict) or batch.get("version") != 1:
        raise ValueError("Unsupported OpenH3 clip batch version.")
    # Rebuild from the manifest, so durations and prompts cannot drift in transit.
    expected = pack_compiled_clips(batch["clips"])
    if payload.get("groups") != expected["groups"]:
        raise ValueError("OpenH3 prompts differ from the compiled manifest; recompile the clips.")
    return json.dumps(expected["openh3_timeline"], ensure_ascii=False), expected["openh3_timeline"]
