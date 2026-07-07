import { describe, expect, it } from "vitest";
import { dloPayload, manualLaunchOption } from "../launchOptions";

describe("launchOptions", () => {
  it("builds a stable DLO payload", () => {
    expect(dloPayload("ClairObscurFix", "dsound")).toEqual([{
      id: "lyall-ClairObscurFix",
      group: "Lyall Fixes",
      name: "ClairObscurFix (dsound override)",
      on: 'WINEDLLOVERRIDES="dsound=n,b"',
      off: "",
      enableGlobally: false,
    }]);
  });

  it("builds the manual launch option line with lowercase %command%", () => {
    expect(manualLaunchOption("winmm")).toBe('WINEDLLOVERRIDES="winmm=n,b" %command%');
  });
});
