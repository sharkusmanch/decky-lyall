import { ButtonItem, Field, PanelSectionRow, showModal } from "@decky/ui";
import { toaster } from "@decky/api";
import type { GameRow } from "../api";
import { installMod, uninstallMod } from "../api";
import { dispatchDlo, hasDLO, manualLaunchOption } from "../lib/launchOptions";
import { ConfigModal } from "./ConfigModal";

function statusText(row: GameRow): string {
  if (row.busy) return `${row.busy.phase}… ${row.busy.pct != null ? `${row.busy.pct}%` : ""}`;
  switch (row.status) {
    case "installed": {
      const warn = row.override_status === "not_registered" || row.override_status === "registered_disabled";
      return warn ? `Installed ${row.installed_version} — launch override not enabled`
        : `Installed ${row.installed_version}`;
    }
    case "update_available": return `Installed ${row.installed_version} · ${row.latest_version} available`;
    case "needs_launch_option": return `Installed ${row.installed_version} — add launch option`;
    case "needs_curation": return "Awaiting catalog data";
    case "not_installed": return row.blocked_by ? `Blocked: ${row.blocked_by} installed` : `${row.latest_version} available`;
    default: return "Unknown";
  }
}

export function GameRowItem({ row, onAction }: { row: GameRow; onAction: () => void }) {
  const installed = row.status === "installed" || row.status === "update_available"
    || row.status === "needs_launch_option";
  const overrideWarn = installed && hasDLO()
    && (row.override_status === "not_registered" || row.override_status === "registered_disabled");

  const run = async (fn: () => Promise<{ ok: boolean; message?: string }>) => {
    try {
      const res = await fn();
      if (!res.ok) toaster.toast({ title: row.mod_id, body: res.message ?? "Failed" });
    } catch {
      // Last-resort net for bridge bugs — backend callables normally never reject.
      toaster.toast({ title: row.mod_id, body: "Something went wrong — check the Decky log" });
    }
    onAction();
  };

  return (
    <>
      <PanelSectionRow>
        <Field label={`${row.name} — ${row.mod_id}`} description={statusText(row)} />
      </PanelSectionRow>
      {!row.busy && row.status === "not_installed" && !row.blocked_by && (
        <PanelSectionRow>
          <ButtonItem layout="below" onClick={() => run(() => installMod(row.mod_id, row.appid))}>
            Install
          </ButtonItem>
        </PanelSectionRow>
      )}
      {!row.busy && row.status === "update_available" && (
        <PanelSectionRow>
          <ButtonItem layout="below" onClick={() => run(() => installMod(row.mod_id, row.appid))}>
            Update to {row.latest_version}
          </ButtonItem>
        </PanelSectionRow>
      )}
      {!row.busy && overrideWarn && (
        <PanelSectionRow>
          <ButtonItem layout="below" onClick={() => {
            dispatchDlo(row.mod_id, row.wine_dll_override);
            toaster.toast({ title: row.mod_id, body: "Sent to Launch Options — accept the import dialog" });
          }}>
            Register launch option
          </ButtonItem>
        </PanelSectionRow>
      )}
      {!row.busy && row.status === "needs_launch_option" && (
        <PanelSectionRow>
          <ButtonItem layout="below" onClick={() => {
            void navigator.clipboard?.writeText(manualLaunchOption(row.wine_dll_override));
            toaster.toast({ title: row.mod_id, body: "Launch option copied" });
          }}>
            Copy launch option
          </ButtonItem>
        </PanelSectionRow>
      )}
      {!row.busy && installed && (
        <PanelSectionRow>
          <ButtonItem layout="below" onClick={() => showModal(<ConfigModal modId={row.mod_id} appid={row.appid} />)}>
            Fix settings
          </ButtonItem>
        </PanelSectionRow>
      )}
      {!row.busy && installed && (
        <PanelSectionRow>
          <ButtonItem layout="below" onClick={() => run(() => uninstallMod(row.mod_id, row.appid))}>
            Uninstall
          </ButtonItem>
        </PanelSectionRow>
      )}
    </>
  );
}
