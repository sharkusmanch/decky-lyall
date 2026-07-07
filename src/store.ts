import type { Busy } from "./api";

type Listener = () => void;
const listeners = new Set<Listener>();
export const progressByAppid = new Map<number, Busy>();

export function setProgress(appid: number, busy: Busy | null) {
  if (busy) progressByAppid.set(appid, busy);
  else progressByAppid.delete(appid);
  notify();
}

export function markStateDirty() {
  notify();
}

export function subscribe(fn: Listener) {
  listeners.add(fn);
  return () => { listeners.delete(fn); };
}

function notify() {
  listeners.forEach(fn => fn());
}
