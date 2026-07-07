import { callable } from "@decky/api";

export type Status = "not_installed" | "installed" | "update_available"
  | "needs_curation" | "needs_launch_option" | "unknown";
export type OverrideStatus = "registered_enabled" | "registered_disabled"
  | "not_registered" | "unknown";

export interface Busy { op: "install" | "uninstall"; phase: string; pct: number | null }

export interface GameRow {
  appid: number; mod_id: string; name: string; install_path: string;
  installed_version: string | null; latest_version: string | null;
  wine_dll_override: string; loader: string;
  status: Status; override_status: OverrideStatus;
  busy: Busy | null; blocked_by: string | null;
}

export interface StateResult {
  ok: boolean; code?: string; message?: string;
  catalog_updated_at?: string | null; games?: GameRow[];
}
export interface OpResult { ok: boolean; accepted?: boolean; code?: string; message?: string }

export const getState = callable<[], StateResult>("get_state");
export const refresh = callable<[], StateResult>("refresh");
export const installMod = callable<[mod_id: string, appid: number], OpResult>("install");
export const uninstallMod = callable<[mod_id: string, appid: number], OpResult>("uninstall");
export const setLaunchOptionHandled =
  callable<[mod_id: string, appid: number, value: string], OpResult>("set_launch_option_handled");

export interface ConfigFile { name: string; relpath: string }
export interface ConfigEntry { section: string | null; key: string; value: string; line: number; type: "bool" | "number" | "string" }
export interface ListConfigsResult { ok: boolean; code?: string; message?: string; configs?: ConfigFile[]; loader?: string }
export interface ReadConfigResult { ok: boolean; code?: string; message?: string; entries?: ConfigEntry[] }

export const listConfigs = callable<[mod_id: string, appid: number], ListConfigsResult>("list_configs");
export const readConfig = callable<[mod_id: string, appid: number, relpath: string], ReadConfigResult>("read_config");
export const setConfigValue =
  callable<[mod_id: string, appid: number, relpath: string, section: string | null, key: string, value: string], OpResult>("set_config_value");
