import { definePlugin, addEventListener, removeEventListener, toaster } from "@decky/api";
import { showModal, staticClasses } from "@decky/ui";
import { FaScrewdriverWrench } from "react-icons/fa6";
import { Panel } from "./components/Panel";
import { PostInstallModal } from "./components/PostInstallModal";
import { ManualLaunchOptionModal } from "./components/ManualLaunchOptionModal";
import { dispatchDlo, hasDLO } from "./lib/launchOptions";
import { setLaunchOptionHandled } from "./api";
import { setProgress, markStateDirty } from "./store";

export default definePlugin(() => {
  // Module-scope listeners: completion handling must work with the QAM closed.
  const onProgress = addEventListener<[string, number, string, number | null]>(
    "qf_progress", (_modId, appid, phase, pct) => {
      setProgress(appid, { op: "install", phase, pct });
    });

  const onDone = addEventListener<[string, string, number, boolean, string, string, string]>(
    "qf_done", (op, modId, appid, okFlag, code, dll, loader) => {
      setProgress(appid, null);
      markStateDirty();
      if (!okFlag) {
        toaster.toast({ title: modId, body: `Failed: ${code}` });
        return;
      }
      if (op === "install") {
        if (hasDLO()) {
          dispatchDlo(modId, dll);
          void setLaunchOptionHandled(modId, appid, "dlo");
          showModal(<PostInstallModal modId={modId} loader={loader} />);
        } else {
          showModal(<ManualLaunchOptionModal modId={modId} appid={appid} dll={dll} loader={loader} />);
        }
      } else {
        toaster.toast({
          title: modId,
          body: hasDLO()
            ? "Uninstalled — turn OFF its toggle in Launch Options"
            : "Uninstalled — remove its line from Launch Options",
        });
      }
    });

  return {
    name: "Lyall Fixes",
    titleView: <div className={staticClasses.Title}>Lyall Fixes</div>,
    content: <Panel />,
    icon: <FaScrewdriverWrench />,
    onDismount() {
      removeEventListener("qf_progress", onProgress);
      removeEventListener("qf_done", onDone);
    },
  };
});
