import { describe, expect, it } from "vitest";
import { partitionRows } from "../running";
import type { GameRow } from "../../api";

const row = (appid: number, mod_id: string): GameRow => ({
  appid, mod_id, name: `G${appid}`, install_path: "/g",
  installed_version: null, latest_version: "1",
  wine_dll_override: "dsound", loader: "ual",
  status: "not_installed", override_status: "unknown",
  busy: null, blocked_by: null,
});

describe("partitionRows", () => {
  it("puts rows for the running app first, keeps the rest", () => {
    const rows = [row(1, "A"), row(2, "B"), row(2, "C")];
    const { running, others } = partitionRows(rows, 2);
    expect(running.map(r => r.mod_id)).toEqual(["B", "C"]);
    expect(others.map(r => r.mod_id)).toEqual(["A"]);
  });

  it("returns everything as others when no game is running", () => {
    const rows = [row(1, "A")];
    expect(partitionRows(rows, null)).toEqual({ running: [], others: rows });
  });

  it("running is empty when the foreground game has no fix", () => {
    const rows = [row(1, "A")];
    const { running, others } = partitionRows(rows, 999);
    expect(running).toEqual([]);
    expect(others).toEqual(rows);
  });
});
