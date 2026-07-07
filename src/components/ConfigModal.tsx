import { useEffect, useState } from "react";
import { ConfirmModal, DropdownItem, Field, TextField, ToggleField } from "@decky/ui";
import { toaster } from "@decky/api";
import type { ConfigEntry, ConfigFile } from "../api";
import { listConfigs, readConfig, setConfigValue } from "../api";

function EntryRow({ entry, onSave }: {
  entry: ConfigEntry;
  onSave: (entry: ConfigEntry, value: string) => Promise<void>;
}) {
  const [text, setText] = useState(entry.value);
  if (entry.type === "bool") {
    return (
      <ToggleField
        label={entry.key}
        description={entry.section ?? undefined}
        checked={entry.value.trim().toLowerCase() === "true"}
        onChange={(checked) => { void onSave(entry, checked ? "true" : "false"); }}
      />
    );
  }
  return (
    <TextField
      label={`${entry.key}${entry.section ? ` [${entry.section}]` : ""}`}
      value={text}
      mustBeNumeric={entry.type === "number"}
      onChange={(e) => setText(e.target.value)}
      onBlur={() => { if (text !== entry.value) void onSave(entry, text); }}
    />
  );
}

export function ConfigModal({ modId, appid, closeModal }: {
  modId: string; appid: number; closeModal?: () => void;
}) {
  const [files, setFiles] = useState<ConfigFile[] | null>(null);
  const [loader, setLoader] = useState("ual");
  const [selected, setSelected] = useState<string | null>(null);
  const [entries, setEntries] = useState<ConfigEntry[] | null>(null);

  useEffect(() => {
    void listConfigs(modId, appid).then((res) => {
      if (!res.ok) {
        toaster.toast({ title: modId, body: res.message ?? "Failed to find settings" });
        closeModal?.();
        return;
      }
      setFiles(res.configs ?? []);
      setLoader(res.loader ?? "ual");
      if ((res.configs ?? []).length >= 1) setSelected(res.configs![0].relpath);
    }).catch(() => closeModal?.());
  }, []);

  useEffect(() => {
    if (!selected) return;
    setEntries(null);
    void readConfig(modId, appid, selected).then((res) => {
      if (!res.ok) {
        toaster.toast({ title: modId, body: res.message ?? "Failed to read settings" });
        return;
      }
      setEntries(res.entries ?? []);
    }).catch(() => undefined);
  }, [selected]);

  const save = async (entry: ConfigEntry, value: string) => {
    try {
      const res = await setConfigValue(modId, appid, selected!, entry.section, entry.key, value);
      if (!res.ok) {
        toaster.toast({ title: modId, body: res.message ?? "Save failed" });
        return;
      }
      setEntries((prev) => prev?.map(e =>
        e.line === entry.line ? { ...e, value } : e) ?? prev);
    } catch {
      toaster.toast({ title: modId, body: "Something went wrong — check the Decky log" });
    }
  };

  return (
    <ConfirmModal strTitle={`${modId} settings`} strOKButtonText="Done"
      onOK={closeModal} onCancel={closeModal} bCancelDisabled>
      {files === null && <Field description="Looking for config files…" />}
      {files !== null && files.length === 0 && (
        <Field description={loader === "bepinex"
          ? "No config file yet — BepInEx fixes create their settings on the game's first launch. Run the game once, then come back."
          : "No config file found for this fix."} />
      )}
      {files !== null && files.length > 1 && (
        <DropdownItem
          label="Config file"
          rgOptions={files.map(f => ({ label: f.relpath, data: f.relpath }))}
          selectedOption={selected}
          onChange={(opt) => setSelected(opt.data as string)}
        />
      )}
      {selected && entries === null && <Field description="Loading settings…" />}
      {entries !== null && entries.length === 0 && <Field description="This config file has no settings." />}
      {entries?.map((entry) => (
        <EntryRow key={`${entry.line}`} entry={entry} onSave={save} />
      ))}
    </ConfirmModal>
  );
}
