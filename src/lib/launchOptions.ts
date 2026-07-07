export const DLO_EVENT = "dlo-add-launch-options";

export const dloPayload = (modId: string, dll: string) => [{
  id: `lyall-${modId}`,           // stable id → re-dispatch upserts, never duplicates
  group: "Lyall Fixes",
  name: `${modId} (${dll} override)`,
  on: `WINEDLLOVERRIDES="${dll}=n,b"`,  // env-only; DLO merges WINEDLLOVERRIDES with ';'
  off: "",
  enableGlobally: false,
}];

export const manualLaunchOption = (dll: string) =>
  `WINEDLLOVERRIDES="${dll}=n,b" %command%`;

// Read live on every use — DLO may load after us or be installed later.
export const hasDLO = () => (window as any).hasDeckyLaunchOptions === true;

export const dispatchDlo = (modId: string, dll: string) =>
  window.dispatchEvent(new CustomEvent(DLO_EVENT, { detail: dloPayload(modId, dll) }));
