import { useEffect, useState } from "react";
import { ButtonItem, Field, ModalRoot, PanelSectionRow, Spinner } from "@decky/ui";
import { toaster } from "@decky/api";
import type { DetectCandidate } from "../api";
import { detectSubdir, setSubdirOverride, installMod } from "../api";

// A "game root" fallback is always offered last — sometimes root is correct,
// and the user (who can see the game) is the one confirming.
const ROOT: DetectCandidate = { subdir: ".", exe: "game install root" };

export function DetectModal({ modId, appid, gameName, onDone, closeModal }: {
  modId: string; appid: number; gameName: string;
  onDone: () => void; closeModal?: () => void;
}) {
  const [cands, setCands] = useState<DetectCandidate[] | null>(null);
  const [working, setWorking] = useState(false);

  useEffect(() => {
    void detectSubdir(modId, appid).then((res) => {
      const found = res.ok ? (res.candidates ?? []) : [];
      // de-dup root if detection already returned it
      setCands([...found.filter(c => c.subdir !== "."), ROOT]);
    }).catch(() => setCands([ROOT]));
  }, []);

  const choose = async (subdir: string) => {
    setWorking(true);
    try {
      const ov = await setSubdirOverride(modId, appid, subdir);
      if (!ov.ok) { toaster.toast({ title: modId, body: ov.message ?? "Failed" }); return; }
      const res = await installMod(modId, appid);
      if (!res.ok) toaster.toast({ title: modId, body: res.message ?? "Install failed" });
      onDone();
      closeModal?.();
    } catch {
      toaster.toast({ title: modId, body: "Something went wrong — check the Decky log" });
    } finally {
      setWorking(false);
    }
  };

  return (
    <ModalRoot onCancel={closeModal} onEscKeypress={closeModal}>
      <h2>Where does {gameName}'s game run from?</h2>
      <p>Pick the folder that holds the game's main <b>.exe</b> — the fix installs there.
        The top choice is usually right.</p>
      {cands === null && <PanelSectionRow><Spinner /></PanelSectionRow>}
      {(working) && <PanelSectionRow><Field description="Installing…" /></PanelSectionRow>}
      {!working && cands?.map((c) => (
        <PanelSectionRow key={c.subdir}>
          <ButtonItem layout="below" onClick={() => choose(c.subdir)}
            description={c.subdir === "." ? undefined : c.exe}>
            {c.subdir === "." ? "Game install root" : c.subdir}
          </ButtonItem>
        </PanelSectionRow>
      ))}
    </ModalRoot>
  );
}
