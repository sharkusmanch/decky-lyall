import type { GameRow } from "../api";

function rank(row: GameRow): number {
  if (row.busy) return 0;
  if (row.status === "update_available") return 1;
  const overrideWarning = row.override_status === "not_registered"
    || row.override_status === "registered_disabled";
  if (row.status === "needs_launch_option") return 2;
  if (row.status === "installed" && overrideWarning) return 2;
  if (row.status === "installed") return 3;
  if (row.status === "not_installed") return 4;
  if (row.status === "needs_curation") return 5;
  return 6;
}

export function sortRows(rows: GameRow[]): GameRow[] {
  return [...rows].sort((a, b) =>
    rank(a) - rank(b) || a.name.localeCompare(b.name) || a.mod_id.localeCompare(b.mod_id));
}
