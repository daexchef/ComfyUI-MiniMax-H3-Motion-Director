# Local LLM clip prompts → Motion Director

This experimental fork joins OpenH3-IR's validated prompt compiler to Motion
Director's existing timeline, H3 sampler, motion/audio context and output path.
It adds **MiniMax H3 OpenH3 Clip Prompter**. Each clip gets a complete H3 brief;
the compiler's actual frame count becomes that clip's Director segment length.

## Install

Use this Director fork instead of the upstream Director folder; do not install
both copies, because they register the same Director node IDs.

```bash
git clone --branch feat/openh3-clip-prompter https://github.com/daexchef/ComfyUI-MiniMax-H3-Motion-Director.git
cd ComfyUI-MiniMax-H3-Motion-Director
python -m pip install -r requirements.txt -r requirements-openh3.txt
```

Run pip using **ComfyUI's Python**, including `python_embeded/python.exe` in a
Windows portable installation. Restart ComfyUI and refresh the browser.
The extra compiler dependency is optional: ordinary Director graphs still load
and run when it is absent. No compiler imports happen during node registration.

## Workflow

Import [the two-clip workflow](../example_workflows/openh3_two_clips.json), then
choose your installed H3 files in its four loader nodes. The filenames in the
example are deliberate placeholders. A [prompt-only API graph](../example_workflows/openh3_prompt_only.api.json)
and [complete API graph](../example_workflows/openh3_two_clips.api.json) are also
included for API clients; send an API graph as the `prompt` field of `POST /prompt`.

1. Start LM Studio's local server. Load `qwen/qwen3.5-9b` with 32K context as an
   initial practical choice. Copy the exact API model identifier into the node.
2. Add **MiniMax H3 OpenH3 Clip Prompter**. Its default endpoint is
   `http://127.0.0.1:1234/v1`. Use the computer's reachable address when ComfyUI
   runs elsewhere: loopback always refers to the computer running ComfyUI.
3. Enter a JSON list with `id`, `intent`, `seconds`, and optional `dialogue`:

   ```json
   [
     {"id":"arrival","intent":"A courier arrives at a quiet lighthouse.","seconds":5},
     {"id":"lamp","intent":"The courier lights the lighthouse lamp.","seconds":8,"dialogue":["I'm here, Captain!"]}
   ]
   ```

4. Put persistent appearance, location and lighting details in `shared_context`.
   Put optional camera/lighting/performance preferences in `direction`.
5. Set the canvas on the Clip Prompter. It owns this batch's canvas and durations.
6. Connect its `director_inputs` directly to **Motion Director.director_inputs**.
   An intermediate Director Inputs node is unnecessary. Set Director to **T2V**
   and clear its global prompt. Keep the ordinary H3 model / CLIP / VAE loaders.
7. Queue. The LLM compiles first, then Director generates the segments. The
   Prompter displays its compiled briefs and diagnostic report after execution.

The node is also an output node: disconnect Director or mute it to preview just
the prompts without rendering H3. An unchanged graph uses ComfyUI's normal node
cache; changing the brief seed requests another take. This does not control the
Director's separate sampling seed.

On a GPU shared with H3, first compile with Director muted, inspect the briefs,
then unload the LLM in LM Studio before enabling Director and queueing again.
Keep the Prompter inputs unchanged so ComfyUI reuses its cached outputs. If you
change an input or restart ComfyUI, reload the LLM before recompiling.

## Timeline ownership

Connecting this node explicitly makes its clip list the source of the **run's**
timeline, replacing the Director's UI timeline for that run. It does not edit or
save the Director UI cards. Edit the clip list on the Prompter and read its preview.
Existing internal references, selective-run choices, and source-video cards are
not part of the generated timeline. Disconnect the node to use the UI again.

The bridge rebuilds its timeline from the compiler manifest and refuses altered
prompts, mismatched canvases, unsupported modes and non-grid frame counts. It uses
24 FPS and pins one shot per clip. Five requested seconds becomes 124 frames;
eight seconds becomes 192 frames. Motion context remains Director's responsibility.

## Scope and evidence

- **Supported:** per-clip T2V briefs, shared descriptive context, exact dialogue,
  optional reusable direction, compiler validation, fallback diagnostics, and
  Director's existing continuity/sampling/output paths.
- **Not implemented:** R2V/I2V/FL2V media binding in this new node, Mixed mode,
  automatic story-to-clip planning, or guaranteed character consistency. The
  compiler batch API itself accepts ordinary asset-bearing Brief objects, but
  this adapter intentionally refuses them until media and labels are wired together.
- **No rendered-quality claim:** prompt tests and planner tests cannot establish
  a visual improvement. Render the same clip list with raw versus compiled prompts,
  using the same sampling seed/settings, and compare both videos with sound.

The upstream compiler can fall back to its validated deterministic draft when
the LLM's detailed pass fails. Each clip exposes `source` and `fallback_reason`;
the node report prints draft fallbacks rather than describing them as LLM successes.
An unreachable model raises and no partial batch is submitted to Director.

## Reproduce without H3 weights

Install the compiler fork in a development environment, then:

```bash
python scripts/compile_openh3_demo.py --model qwen/qwen3.5-9b --out ./openh3-demo
python -m pytest tests/test_openh3_bridge.py -q
```

The smoke test writes compiled briefs, the exact timeline and a diagnostic report.
The planner test uses actual compiler output and the actual Director planner,
stubbing only ComfyUI host interfaces. It needs CPU PyTorch, NumPy and Pillow,
but no GPU. The optional UI preview has a Node.js test under `web/js/tests`.

For quality-first experimentation, upstream documents Qwen3.6-27B at 4-bit as its
tested model. For a 16 GB GPU, a smaller Qwen3.5-9B is a more comfortable starting
point, particularly if H3 shares the GPU. This is a hardware-fit recommendation,
not evidence that the smaller model writes better briefs than every alternative.

Compiler code stays in the Apache-2.0 [compiler fork](https://github.com/daexchef/open-h3-ir/tree/feat/motion-director-clips).
Director code stays GPL-3.0 with the upstream notices intact. The two forks depend
on a shared API rather than duplicating the compiler inside the renderer.
