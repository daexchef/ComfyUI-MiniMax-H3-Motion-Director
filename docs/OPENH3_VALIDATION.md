# Integration validation — 2026-10-14

This is evidence about prompt compilation and Director planning. No H3 video was
rendered during this validation, and no comparative visual-quality claim is made.

## New checks

- Compiler clip tests: **6 passed**. Real compiler, deterministic draft path:
  separate clip prompts, exact dialogue, frame snapping, shared context,
  preflight refusal and progress order.
- Compiler mutation checks: frame drift makes its test fail; bypassing preflight
  makes all five invalid-batch cases fail. Source restored; all six tests pass again.
- Director integration checks: **16 passed**. Actual compiler output traverses
  the actual external-input normalizer and Director planner. Five and eight
  seconds produce frame ranges `[0,124)` and `[124,316)` with distinct prompts.
  Includes node execution, optional-dependency import isolation, invalid clip
  inputs, manifest mismatch refusals and example API contract checks.
- Browser preview unit test: **passed**. Compiled text and fallback diagnostics
  appear in a read-only, non-serialized widget; subsequent runs reuse the widget.
- Compiler control gate: **23/23**.

## Broader suites and upstream controls

- Compiler: **996 passed, 1 failed** on Windows. The failure is
  `test_upload_store.py::test_an_abandoned_part_file_is_swept`. It reproduces in
  an untouched archive of upstream commit
  `fd031e136ae3d89147324c0d1b2aa65e838c21f5`.
- Director: **92 passed, 4 failed** before three additional integration tests
  were added; those three also pass in the final focused run. The four failing
  refine-latent tests expect `nodes.VAEDecode` / `nodes.VAEEncode` in a standalone
  environment. An untouched archive of upstream commit
  `f99390645533c0993a8914f2585d7199ebc3e8e2` produces the same failures (**79 passed,
  4 failed**).
- Full JavaScript run: **23 passed, 3 failed**. Three existing browser suites
  require ComfyUI's `scripts/app.js` / `scripts/api.js`, absent from the standalone
  checkout. The new preview test passes independently.

## Live LM Studio test

Hardware: RTX 5060 Ti 16 GB, 64 GB system RAM. Model:
`qwen/qwen3.5-9b`, Q8_0, loaded with a 32,768-token context. Endpoint:
`http://127.0.0.1:1234/v1`.

The first clip returned a validated **written** brief with 124 frames at 864×480.
Its [unmodified compiler manifest](examples/openh3-qwen35-9b-first-clip.json) is
included. The compiler issued its usual token-band warning because this short
brief contains 157 tokens; it remained valid.

During the second clip, LM Studio returned HTTP 400: **Model unloaded by user or
API request**. The compiler returned its validated deterministic draft, and the
integration's diagnostic report explicitly marked `source=draft` and the fallback
reason. This is a partial live test, not a successful two-clip LLM benchmark.

A Windows console encoding failure happened after the smoke-test artifacts were
written. The smoke script now explicitly uses UTF-8 for console output.

The evidence supports Qwen3.5-9B as a workable starting point on this hardware;
it does not establish that it is the best creative writer. The upstream compiler
documents Qwen3.6-27B 4-bit as its tested model. Larger-model comparisons and a
raw-prompt versus compiled-prompt H3 render remain future experiments.
