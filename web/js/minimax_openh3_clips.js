import { app } from "../../scripts/app.js";
import { ComfyWidgets } from "../../scripts/widgets.js";

app.registerExtension({
    name: "MiniMaxH3.OpenH3Clips",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "MiniMaxH3OpenH3Clips") return;
        const original = nodeType.prototype.onExecuted;
        nodeType.prototype.onExecuted = function (message) {
            original?.apply(this, arguments);
            let preview = this.widgets?.find((w) => w.name === "compiled_preview");
            if (!preview) {
                preview = ComfyWidgets.STRING(this, "compiled_preview",
                    ["STRING", { multiline: true }], app).widget;
                preview.options ??= {};
                preview.options.serialize = false;
                if (preview.inputEl) preview.inputEl.readOnly = true;
            }
            preview.value = [message.text?.[0] ?? "", message.compiled_clips?.[0] ?? ""].join("\n\n");
            if (preview.inputEl) preview.inputEl.value = preview.value;
            this.setDirtyCanvas(true, true);
        };
    },
});
