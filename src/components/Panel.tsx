import { useEffect, useState } from "react";
import { PanelSection, PanelSectionRow, ButtonItem, Field, Router } from "@decky/ui";
import { getState, refresh, type StateResult } from "../api";
import { sortRows } from "../lib/sort";
import { partitionRows } from "../lib/running";
import { hasDLO } from "../lib/launchOptions";
import { subscribe, progressByAppid } from "../store";
import { GameRowItem } from "./GameRowItem";

function age(iso?: string | null): string {
  if (!iso) return "never";
  const mins = Math.max(0, Math.round((Date.now() - Date.parse(iso)) / 60000));
  return mins < 60 ? `${mins}m ago` : `${Math.round(mins / 60)}h ago`;
}

function runningAppId(): number | null {
  const app = Router.MainRunningApp;
  if (!app) return null;
  const id = Number((app as { appid?: number | string }).appid);
  return Number.isFinite(id) ? id : null;
}

export function Panel() {
  const [state, setState] = useState<StateResult | null>(null);
  const [running, setRunning] = useState<number | null>(runningAppId());
  const load = () => { void getState().then(setState).catch(() => undefined); };

  useEffect(() => {
    load();
    const unsub = subscribe(load);
    const reg = SteamClient.GameSessions.RegisterForAppLifetimeNotifications(() => {
      setRunning(runningAppId());
    });
    return () => { unsub(); reg.unregister(); };
  }, []);

  const rows = (state?.games ?? []).map(r =>
    ({ ...r, busy: progressByAppid.get(r.appid) ?? r.busy }));
  const { running: nowPlaying, others } = partitionRows(rows, running);

  return (
    <>
      {!hasDLO() && (
        <PanelSection title="Recommended">
          <PanelSectionRow>
            <Field description={'Install the "Launch Options" plugin from the Decky store for one-toggle activation. Without it you must paste launch options manually.'} />
          </PanelSectionRow>
        </PanelSection>
      )}
      {nowPlaying.length > 0 && (
        <PanelSection title="Now Playing">
          {sortRows(nowPlaying).map(row => (
            <GameRowItem key={`np-${row.appid}-${row.mod_id}`} row={row} onAction={load} />
          ))}
        </PanelSection>
      )}
      <PanelSection title="Games">
        {state === null && <PanelSectionRow><Field description="Loading…" /></PanelSectionRow>}
        {state !== null && rows.length === 0 && (
          <PanelSectionRow><Field description="No installed games with available fixes." /></PanelSectionRow>
        )}
        {state !== null && rows.length > 0 && others.length === 0 && (
          <PanelSectionRow><Field description="All available fixes are for the game you're playing." /></PanelSectionRow>
        )}
        {sortRows(others).map(row => (
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
