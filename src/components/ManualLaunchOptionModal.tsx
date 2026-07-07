import { ConfirmModal } from "@decky/ui";
import { toaster } from "@decky/api";
import { manualLaunchOption } from "../lib/launchOptions";
import { setLaunchOptionHandled } from "../api";

export function ManualLaunchOptionModal({ modId, appid, dll, loader, closeModal }: {
  modId: string; appid: number; dll: string; loader: string; closeModal?: () => void;
}) {
  const line = manualLaunchOption(dll);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(line);
      toaster.toast({ title: "Copied", body: "Paste into Properties → Launch Options" });
    } catch {
      toaster.toast({ title: "Copy failed", body: "Add the line manually" });
    }
  };
  return (
    <ConfirmModal strTitle="Fix installed — add the launch option"
      strOKButtonText="Copy launch option"
      strCancelButtonText="I've added it"
      onOK={() => { void copy(); }}
      onCancel={() => { void setLaunchOptionHandled(modId, appid, "manual_confirmed"); closeModal?.(); }}>
      <div>
        <p>Without the Launch Options plugin, add this line to the game's
          <b> Properties → Launch Options</b> yourself:</p>
        <pre style={{ whiteSpace: "pre-wrap", wordBreak: "break-all" }}>{line}</pre>
        {loader === "bepinex" && (
          <p>⚠️ First launch can take several minutes (BepInEx builds its cache).</p>
        )}
      </div>
    </ConfirmModal>
  );
}
