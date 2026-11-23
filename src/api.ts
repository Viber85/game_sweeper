import { callable } from "@decky/api";

export type Status = "installed" | "candidate" | "review";
export type Tab = "overview" | "libraries" | "results" | "review" | "settings";
export type Filter = "all" | Status;

export type Entry = {
  id: string;
  name: string;
  name_source: string;
  status: Status;
  reason: string;
  library: string;
  prefix_path: string;
  shader_path: string;
  prefix_bytes: number;
  shader_bytes: number;
  bytes: number;
};

export type Disk = {
  library: string;
  total: number;
  used: number;
  free: number;
};

export type ScanData = {
  scanned_at: string;
  libraries: string[];
  missing_libraries: string[];
  disks: Disk[];
  entries: Entry[];
  summary: {
    items: number;
    installed: number;
    candidate: number;
    review: number;
    bytes: number;
    candidate_bytes: number;
  };
};

export type UpdateInfo = {
  available: boolean;
  version: string;
  url: string;
  notes?: string;
  sha256?: string;
  error?: string;
};

export type NameInfo = { found: boolean; name: string; error?: string };

export const scanStorage = callable<[], ScanData>("scan_storage");
export const checkUpdate = callable<[], UpdateInfo>("check_update");
export const resolveName = callable<[appid: string], NameInfo>("resolve_name");

export type CleanupKind = "prefix" | "shader";
export type CleanupPreview = {
  ok: boolean;
  error?: string;
  token?: string;
  name?: string;
  appid?: string;
  kind?: CleanupKind;
  status?: Status;
  bytes?: number;
  path?: string;
};
export type CleanupResult = {
  ok: boolean;
  error?: string;
  success?: boolean;
  name?: string;
  kind?: CleanupKind;
  bytes?: number;
};
export const prepareCleanup = callable<
  [library: string, appid: string, kind: CleanupKind], CleanupPreview
>("prepare_cleanup");
export const deleteStorage = callable<
  [token: string, confirmation: string], CleanupResult
>("delete_storage");


/** Decky Loader's global installer route (not @decky/api's plugin-scoped call). */
type InstallerBridge = {
  callable: (route: string) => (...args: unknown[]) => Promise<unknown>;
};

export async function requestDeckyUpdate(info: UpdateInfo): Promise<void> {
  if (!info.available || !info.url) throw new Error("No update available");
  const bridge = (window as Window & { DeckyBackend?: InstallerBridge }).DeckyBackend;
  if (typeof bridge?.callable !== "function") {
    throw new Error(
      "Decky's installer API is not available on this Loader version. " +
      "Use Decky's 'Install Plugin from URL' option with the release ZIP."
    );
  }

  // This queues Decky's confirmation prompt. Only the Loader can replace
  // the currently running plugin (and reload it after user confirmation).
  // Decky Loader: PluginInstallType.UPDATE = 2.
  await bridge.callable("utilities/install_plugin")(
    info.url,
    "GameSweep",
    info.version,
    info.sha256 || "",
    2
  );
}

export function bytes(value: number): string {
  if (!Number.isFinite(value) || value <= 0) return "0 B";
  const unitIndex = Math.min(Math.floor(Math.log(value) / Math.log(1024)), 4);
  const units = ["B", "KB", "MB", "GB", "TB"];
  return (value / Math.pow(1024, unitIndex)).toFixed(unitIndex ? 1 : 0) + " " + units[unitIndex];
}
