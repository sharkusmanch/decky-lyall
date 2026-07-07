import { useEffect, useState } from "react";
import { PanelSection, PanelSectionRow, ButtonItem, Field } from "@decky/ui";
import { getState, refresh, type StateResult } from "../api";
import { sortRows } from "../lib/sort";
import { hasDLO } from "../lib/launchOptions";
import { subscribe, progressByAppid } from "../store";
import { GameRowItem } from "./GameRowItem";

function age(iso?: string | null): string {
  if (!iso) return "never";
  const mins = Math.max(0, Math.round((Date.now() - Date.parse(iso)) / 60000));
  return mins < 60 ? `${mins}m ago` : `${Math.round(mins / 60)}h ago`;
}

export function Panel() {
  const [state, setState] = useState<StateResult | null>(null);
  const load = () => { void getState().then(setState).catch(() => undefined); };

  useEffect(() => {
    load();
    return subscribe(load);
  }, []);

  const rows = (state?.games ?? []).map(r =>
    ({ ...r, busy: progressByAppid.get(r.appid) ?? r.busy }));

  return (
    <>
      {!hasDLO() && (
        <PanelSection title="Recommended">
          <PanelSectionRow>
            <Field description={'Install the "Launch Options" plugin from the Decky store for one-toggle activation. Without it you must paste launch options manually.'} />
          </PanelSectionRow>
        </PanelSection>
      )}
      <PanelSection title="Games">
        {state === null && <PanelSectionRow><Field description="Loading…" /></PanelSectionRow>}
        {state !== null && rows.length === 0 && (
          <PanelSectionRow><Field description="No installed games with available fixes." /></PanelSectionRow>
        )}
        {sortRows(rows).map(row => (
          <GameRowItem key={`${row.appid}-${row.mod_id}`} row={row} onAction={load} />
        ))}
      </PanelSection>
      <PanelSection title="Catalog">
        <PanelSectionRow>
          <Field label="Catalog updated" description={age(state?.catalog_updated_at)} />
        </PanelSectionRow>
        <PanelSectionRow>
          <ButtonItem layout="below" onClick={() => { void refresh().then(setState).catch(() => undefined); }}>
            Refresh
          </ButtonItem>
        </PanelSectionRow>
      </PanelSection>
    </>
  );
}
