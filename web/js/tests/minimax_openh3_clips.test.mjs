import assert from "node:assert/strict";
import fs from "node:fs/promises";
import vm from "node:vm";
import test from "node:test";

test("preview displays compiler diagnostics, is read-only and is reused", async () => {
    let extension;
    const source = (await fs.readFile(new URL("../minimax_openh3_clips.js", import.meta.url), "utf8"))
        .replace(/^import .*;\r?\n/gm, "");
    const context = {
        app: { registerExtension(value) { extension = value; } },
        ComfyWidgets: { STRING(node, name) {
            const widget = { name, inputEl: {}, options: {} };
            node.widgets.push(widget);
            return { widget };
        } },
    };
    vm.runInNewContext(source, context);
    let originalCalls = 0;
    class Writer {
        widgets = [];
        onExecuted() { originalCalls++; }
        setDirtyCanvas() {}
    }
    await extension.beforeRegisterNodeDef(Writer, { name: "MiniMaxH3OpenH3Clips" });
    const node = new Writer();
    node.onExecuted({ text: ["DRAFT FALLBACK: bad prose"], compiled_clips: ['[{"id":"a"}]'] });
    assert.match(node.widgets[0].value, /DRAFT FALLBACK/);
    assert.match(node.widgets[0].value, /"id":"a"/);
    assert.equal(node.widgets[0].inputEl.readOnly, true);
    assert.equal(node.widgets[0].options.serialize, false);
    node.onExecuted({ text: ["written"], compiled_clips: ["new briefs"] });
    assert.equal(node.widgets.length, 1);
    assert.equal(node.widgets[0].value, "written\n\nnew briefs");
    assert.equal(originalCalls, 2);
});
