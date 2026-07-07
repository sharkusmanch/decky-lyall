import { ConfirmModal } from "@decky/ui";

export function PostInstallModal({ modId, loader, closeModal }: {
  modId: string; loader: string; closeModal?: () => void;
}) {
  return (
    <ConfirmModal strTitle="Fix installed — one more step"
      strOKButtonText="Got it" onOK={closeModal} onCancel={closeModal} bCancelDisabled>
      <div>
        <p>To activate <b>{modId}</b>, enable its launch option:</p>
        <ol>
          <li>Open the game's menu (the one with “Properties...”)</li>
          <li>Select <b>Launch Options</b></li>
          <li>Turn ON <b>{modId}</b> under “Lyall Fixes”</li>
        </ol>
        <p>A Launch Options import dialog may also appear — accept it.</p>
        {loader === "bepinex" && (
          <p>⚠️ First launch can take several minutes (BepInEx builds its cache) — don't force-quit.</p>
        )}
      </div>
    </ConfirmModal>
  );
}
