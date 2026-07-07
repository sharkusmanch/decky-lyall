import { describe, expect, it } from "vitest";
import { sortRows } from "../sort";
import type { GameRow } from "../../api";

const row = (over: Partial<GameRow>): GameRow => ({
  appid: 1, mod_id: "M", name: "G", install_path: "/g",
  installed_version: null, latest_version: "1",
  wine_dll_override: "dsound", loader: "ual",
  status: "not_installed", override_status: "unknown",
  busy: null, blocked_by: null, ...over,
});

describe("sortRows", () => {
  it("orders busy > update > warning > installed > not_installed > needs_curation", () => {
    const rows = [
      row({ mod_id: "curation", status: "needs_curation" }),
      row({ mod_id: "plain", status: "installed", override_status: "registered_enabled" }),
      row({ mod_id: "warn", status: "installed", override_status: "registered_disabled" }),
      row({ mod_id: "manual", status: "needs_launch_option" }),
      row({ mod_id: "upd", status: "update_available" }),
      row({ mod_id: "busy", busy: { op: "install", phase: "download", pct: 5 } }),
      row({ mod_id: "not", status: "not_installed" }),
    ];
    expect(sortRows(rows).map(r => r.mod_id))
      .toEqual(["busy", "upd", "manual", "warn", "plain", "not", "curation"]);
  });
});
