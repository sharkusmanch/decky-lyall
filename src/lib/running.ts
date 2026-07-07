import type { GameRow } from "../api";

// Pure split of rows into the foreground game (if any) and the rest.
// Reading Router.MainRunningApp / subscribing to lifetime events is glue in Panel.
export function partitionRows(
  rows: GameRow[],
  runningAppId: number | null,
): { running: GameRow[]; others: GameRow[] } {
  if (runningAppId == null) return { running: [], others: rows };
  const running: GameRow[] = [];
  const others: GameRow[] = [];
  for (const r of rows) (r.appid === runningAppId ? running : others).push(r);
  return { running, others };
}
