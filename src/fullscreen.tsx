import { ButtonItem, Focusable, Navigation, Router } from "@decky/ui";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import {
  FaArrowLeft, FaBroom, FaCog, FaDatabase, FaDownload,
  FaExclamationTriangle, FaHdd, FaHome, FaLayerGroup,
  FaList, FaSearch, FaShieldAlt, FaSyncAlt
} from "react-icons/fa";
import {
  bytes, checkUpdate, requestDeckyUpdate, resolveName, scanStorage,
  prepareCleanup, deleteStorage
} from "./api";
import type { Disk, Entry, Filter, ScanData, Tab, UpdateInfo, CleanupPreview, CleanupKind } from "./api";
import { style } from "./styles";

const TABS: Array<{ id: Tab; label: string; icon: ReactNode }> = [
  { id: "overview", label: "Overview", icon: <FaHome /> },
  { id: "libraries", label: "Libraries", icon: <FaLayerGroup /> },
  { id: "results", label: "Scan Results", icon: <FaList /> },
  { id: "review", label: "Review", icon: <FaShieldAlt /> },
  { id: "settings", label: "Settings", icon: <FaCog /> }
];

function StatCard({ icon, label, value, note, accent = false, wide = false }: {
  icon: ReactNode; label: string; value: string; note: string;
  accent?: boolean; wide?: boolean
}) {
  return (
    <div className={"gs-card gs-metric" + (accent ? " gs-metric-accent" : "") + (wide ? " gs-wide" : "")}>
      <span className="gs-metric-icon">{icon}</span>
      <div>
        <div className="gs-metric-title">{label}</div>
        <div className="gs-metric-value">{value}</div>
        <div className="gs-metric-note">{note}</div>
      </div>
    </div>
  );
}

function Ring({ disk, candidateBytes }: { disk: Disk | undefined; candidateBytes: number }) {
  const total = disk?.total || 0;
  const used = disk?.used || 0;
  const free = disk?.free || 0;
  const pct = total > 0 ? Math.max(0, Math.min(100, (used / total) * 100)) : 0;
  const degrees = (pct / 100) * 360;
  return (
    <div className="gs-card gs-meter-card">
      <div className="gs-meter" role="img" aria-label={"Disk storage " + pct.toFixed(0) + "% used"}
        style={{
          background: "conic-gradient(from -90deg, #44ddcf 0deg, #3b75f5 " +
            degrees.toFixed(2) + "deg, #29384a " + degrees.toFixed(2) + "deg, #29384a 360deg)"
        }}>
        <div className="gs-meter-text">
          <FaHdd className="gs-meter-icon" />
          <div className="gs-meter-big">{disk ? bytes(total) : "—"}</div>
          <div className="gs-meter-label">Total Storage</div>
          <div className="gs-meter-rule" />
          <div className="gs-meter-small">
            <span>{bytes(used)} used</span>
            <span><strong>{bytes(free)}</strong> free</span>
          </div>
        </div>
      </div>
      <div className="gs-meter-foot">
        {disk ? pct.toFixed(1) + "% used" : "No accessible Steam library"}
        {" · "} {bytes(candidateBytes)} potential leftovers
      </div>
    </div>
  );
}

function StatusPill({ status }: { status: Entry["status"] }) {
  const label = status === "installed" ? "Installed" :
    status === "candidate" ? "Potential leftover" : "Needs review";
  return <span className={"gs-status " + status}>{label}</span>;
}

function ItemList({ entries, selected, onSelect, onLookup, lookupBusy, maxRows, onDelete, cleanupBusy }: {
  entries: Entry[];
  selected: string;
  onSelect: (key: string) => void;
  onLookup: (id: string) => void;
  lookupBusy: string;
  maxRows?: number;
  onDelete: (entry: Entry, kind: CleanupKind) => void;
  cleanupBusy: boolean;
}) {
  const showing = maxRows ? entries.slice(0, maxRows) : entries;
  return (
    <>
      <div className="gs-list-heading">
        <div>Game / Prefix</div>
        <div>AppID</div>
        <div>Status</div>
        <div style={{ textAlign: "right" }}>Size</div>
      </div>
      {!showing.length && <div className="gs-empty">Nothing to show in this filter.</div>}
      {showing.map((entry) => {
        const key = entry.library + ":" + entry.id;
        const expanded = key === selected;
        const initials = entry.name === "Unknown game (" + entry.id + ")" ?
          "?" : entry.name.trim().slice(0, 2).toUpperCase();
        return (
          <div className="gs-list-row-wrap" key={key}>
            <ButtonItem layout="below" onClick={() => onSelect(expanded ? "" : key)}>
              <div className="gs-list-row">
                <div className="gs-game-name">
                  <div className="gs-game-initial">{initials}</div>
                  <div style={{ minWidth: 0 }}>
                    <div className="gs-game-title">{entry.name}</div>
                    <div className="gs-game-hint">{entry.prefix_bytes ? "Compatdata" : "Shader cache"}
                      {entry.prefix_bytes && entry.shader_bytes ? " + shader cache" : ""}</div>
                  </div>
                </div>
                <div className="gs-col-text">{entry.id}</div>
                <div><StatusPill status={entry.status} /></div>
                <div className="gs-col-size">{bytes(entry.bytes)}</div>
              </div>
            </ButtonItem>
            {expanded && (
              <div className="gs-details">
                <strong>{entry.reason}</strong>
                <div>Compatdata: {bytes(entry.prefix_bytes)} · Shader cache: {bytes(entry.shader_bytes)}</div>
                <div>Library: {entry.library}</div>
                {!!entry.prefix_path && <div>Compatdata path: {entry.prefix_path}</div>}
                {!!entry.shader_path && <div>Shader path: {entry.shader_path}</div>}
                <div>Title source: {entry.name_source}</div>
                {entry.status !== "installed" && (
                  <div className="gs-action gs-delete-row">
                    {!!entry.prefix_path && (
                      <ButtonItem layout="below" disabled={cleanupBusy}
                        onClick={() => onDelete(entry, "prefix")}>
                        Delete compatdata…
                      </ButtonItem>
                    )}
                    {!!entry.shader_path && (
                      <ButtonItem layout="below" disabled={cleanupBusy}
                        onClick={() => onDelete(entry, "shader")}>
                        Delete shader cache…
                      </ButtonItem>
                    )}
                  </div>
                )}
                {entry.name_source === "unknown" && entry.status !== "review" && (
                  <div className="gs-action">
                    <ButtonItem layout="below"
                      disabled={lookupBusy === entry.id}
                      onClick={() => onLookup(entry.id)}>
                      <FaSearch style={{ marginRight: 7 }} />
                      {lookupBusy === entry.id ? "Looking up..." : "Find title on Steam"}
                    </ButtonItem>
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}
    </>
  );
}

function exitFullscreen(): void {
  Router.CloseSideMenus();
  try {
    Navigation.NavigateBack();
  } catch {
    try {
      Navigation.Navigate("/library/home");
    } catch {
      Router.Navigate("/library/home");
    }
  }
}

export function GameSweepFullScreen() {
  const [tab, setTab] = useState<Tab>("overview");
  const [data, setData] = useState<ScanData | null>(null);
  const [diskId, setDiskId] = useState("");
  const [filter, setFilter] = useState<Filter>("all");
  const [selected, setSelected] = useState("");
  const [busy, setBusy] = useState(false);
  const [lookupBusy, setLookupBusy] = useState("");
  const [updateBusy, setUpdateBusy] = useState(false);
  const [updateInfo, setUpdateInfo] = useState<UpdateInfo | null>(null);
  const [updateRequestSent, setUpdateRequestSent] = useState(false);
  const [error, setError] = useState("");
  const scanPending = useRef(false);
  const navRef = useRef<HTMLDivElement>(null);
  const dialogRef = useRef<HTMLDivElement>(null);
  const [deletePreview, setDeletePreview] = useState<CleanupPreview | null>(null);
  const [deleteAcknowledged, setDeleteAcknowledged] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [cleanupPreparing, setCleanupPreparing] = useState(false);
  const [cleanupNotice, setCleanupNotice] = useState("");

  const refresh = useCallback(async () => {
    if (scanPending.current) return;
    scanPending.current = true;
    setBusy(true);
    setError("");
    try {
      const result = await scanStorage();
      setData(result);
      setDiskId(prev => result.disks?.some(d => d.library === prev) ?
        prev : result.disks?.[0]?.library || "");
    } catch (e) {
      setError("Storage scan failed: " + String(e));
    } finally {
      scanPending.current = false;
      setBusy(false);
    }
  }, []);

  useEffect(() => { void refresh(); }, [refresh]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      const node = navRef.current?.querySelector<HTMLElement>(".DialogButton");
      node?.focus();
    }, 180);
    return () => window.clearTimeout(timer);
  }, []);

  useEffect(() => {
    if (!deletePreview) return;
    const timer = window.setTimeout(() => {
      dialogRef.current?.querySelector<HTMLElement>(".DialogButton")?.focus();
    }, 80);
    return () => window.clearTimeout(timer);
  }, [deletePreview]);

  const disk = useMemo(
    () => data?.disks?.find(d => d.library === diskId) || data?.disks?.[0],
    [data, diskId]
  );
  const driveItems = useMemo(
    () => data?.entries.filter(item => item.library === disk?.library) || [],
    [data, disk]
  );
  const drivePrefix = driveItems.reduce((sum, item) => sum + item.prefix_bytes, 0);
  const driveShader = driveItems.reduce((sum, item) => sum + item.shader_bytes, 0);
  const driveCandidate = driveItems.reduce(
    (sum, item) => sum + (item.status === "candidate" ? item.bytes : 0), 0
  );
  const allEntries = data?.entries || [];
  const filtered = allEntries.filter(entry => filter === "all" || entry.status === filter);

  async function nameLookup(id: string) {
    setError("");
    setLookupBusy(id);
    try {
      const result = await resolveName(id);
      if (result.found) await refresh();
      else setError(result.error || "Steam could not identify this AppID.");
    } catch (e) {
      setError("Steam lookup failed: " + String(e));
    } finally {
      setLookupBusy("");
    }
  }

  async function findUpdate() {
    setError("");
    setUpdateBusy(true);
    setUpdateRequestSent(false);
    try {
      const info = await checkUpdate();
      setUpdateInfo(info);
      if (info.error) setError(info.error);
    } catch (e) {
      setError("Update check failed: " + String(e));
    } finally {
      setUpdateBusy(false);
    }
  }

  async function applyUpdate() {
    if (!updateInfo?.available) return;
    setError("");
    setUpdateBusy(true);
    setUpdateRequestSent(false);
    try {
      await requestDeckyUpdate(updateInfo);
      setUpdateRequestSent(true);
    } catch (e) {
      setError("Decky update request failed: " + String(e));
    } finally {
      setUpdateBusy(false);
    }
  }

  async function requestDeletion(entry: Entry, kind: CleanupKind) {
    if (entry.status === "installed" || cleanupPreparing || deleting) return;
    setCleanupNotice("");
    setError("");
    setCleanupPreparing(true);
    try {
      const result = await prepareCleanup(entry.library, entry.id, kind);
      if (!result.ok || !result.token) {
        setError("Delete refused: " + (result.error || "Unable to verify the folder"));
        return;
      }
      setDeleteAcknowledged(false);
      setDeletePreview(result);
    } catch (e) {
      setError("Delete preview failed: " + String(e));
    } finally {
      setCleanupPreparing(false);
    }
  }

  async function confirmDeletion() {
    if (!deletePreview?.token || !deleteAcknowledged || deleting) return;
    setDeleting(true);
    setError("");
    try {
      const result = await deleteStorage(deletePreview.token, "PERMANENT_DELETE");
      if (!result.ok || !result.success) {
        setError("Cleanup failed: " + (result.error || "Unknown error"));
        setDeletePreview(null);
        return;
      }
      setCleanupNotice(
        "Removed " + (result.kind === "prefix" ? "compatdata" : "shader cache") +
        " for " + (result.name || deletePreview.name || deletePreview.appid) +
        " (" + bytes(result.bytes || 0) + " estimated)."
      );
      setDeletePreview(null);
      setSelected("");
      await refresh();
    } catch (e) {
      setError("Cleanup failed: " + String(e));
      setDeletePreview(null);
    } finally {
      setDeleting(false);
    }
  }

  const title = tab === "overview" ? "Storage Overview" :
    tab === "libraries" ? "Steam Libraries" :
    tab === "results" ? "Scan Results" :
    tab === "review" ? "Review Candidates" : "Settings";

  const filterBar = (
    <div className="gs-filters">
      {([
        ["all", "All"], ["candidate", "Potential leftovers"],
        ["review", "Needs review"], ["installed", "Installed"]
      ] as Array<[Filter, string]>).map(([value, label]) => (
        <div className={"gs-filter" + (filter === value ? " gs-selected" : "")} key={value}>
          <ButtonItem layout="below" onClick={() => setFilter(value)}>
            {label}
          </ButtonItem>
        </div>
      ))}
    </div>
  );

  return (
    <Focusable onCancelButton={() => {
      if (deletePreview) setDeletePreview(null);
      else exitFullscreen();
    }} style={{ width: "100%", height: "100%", minHeight: 0 }}>
      <style>{style}</style>
      <div className="gs-screen">
        <aside className="gs-sidebar">
          <div className="gs-brand">
            <FaBroom className="gs-brand-icon" />GameSweep
          </div>
          <div className="gs-subbrand">SteamOS Utility</div>
          <div className="gs-nav" ref={navRef}>
            {TABS.map(item => (
              <div className={"gs-nav-wrap" + (tab === item.id ? " gs-active" : "")} key={item.id}>
                <ButtonItem layout="below" onClick={() => {
                  setSelected("");
                  setTab(item.id);
                }}>
                  <span className="gs-nav-label">{item.icon}{item.label}</span>
                </ButtonItem>
              </div>
            ))}
          </div>
          <div className="gs-sidebar-bottom">
            <div style={{ marginBottom: 10 }}>Game Mode · Storage Manager</div>
            <ButtonItem layout="below" onClick={exitFullscreen}>
              <FaArrowLeft style={{ marginRight: 6 }} />Exit fullscreen
            </ButtonItem>
          </div>
        </aside>
        <main className="gs-main">
          <header className="gs-heading">
            <div>
              <h1 className="gs-title">GameSweep <span style={{ color: "#6f859f" }}>/</span> {title}</h1>
              <div className="gs-subtitle">Compatdata and shader cache overview for SteamOS</div>
            </div>
            <div className="gs-right-tag">Game Mode · v0.3.1</div>
          </header>

          {!!error && <div className="gs-note"><FaExclamationTriangle style={{ marginRight: 8 }} />{error}</div>}
          {!!cleanupNotice && <div className="gs-cleanup-success">{cleanupNotice}</div>}
          {!!data?.missing_libraries?.length && (
            <div className="gs-note">
              {data.missing_libraries.length} Steam library path(s) are unavailable.
              Possible leftovers must be reviewed; never delete based on missing manifests alone.
            </div>
          )}

          {tab === "overview" && (
            <>
              <div className="gs-overview">
                <Ring disk={disk} candidateBytes={driveCandidate} />
                <div className="gs-metrics">
                  <StatCard icon={<FaHdd />} label="Used storage"
                    value={disk ? bytes(disk.used) : "—"}
                    note={disk ? "On selected filesystem" : "No disk detected"} />
                  <StatCard icon={<FaDatabase />} label="Compatdata"
                    value={bytes(drivePrefix)}
                    note={String(driveItems.filter(x => !!x.prefix_path).length) + " prefix folders"} />
                  <StatCard icon={<FaLayerGroup />} label="Shader Cache"
                    value={bytes(driveShader)}
                    note={String(driveItems.filter(x => !!x.shader_path).length) + " shader directories"} />
                  <StatCard icon={<FaBroom />} label="Potential leftovers"
                    value={bytes(driveCandidate)} accent
                    note="Review required · not verified safe" />
                  <StatCard icon={<FaHdd />} label="Available Steam libraries"
                    value={String(data?.libraries.length || 0)}
                    note={disk ? disk.library : "No active library"} wide />
                </div>
              </div>
              <section className="gs-card gs-section">
                <div className="gs-section-heading">
                  <div>
                    <span className="gs-section-title">Scan Results</span>
                    <span className="gs-section-detail"> · {data?.summary.items || 0} items</span>
                  </div>
                  <div className="gs-action" style={{ marginTop: 0 }}>
                    <ButtonItem layout="below" disabled={busy} onClick={() => { void refresh(); }}>
                      <FaSyncAlt style={{ marginRight: 7 }} />{busy ? "Scanning..." : "Scan again"}
                    </ButtonItem>
                    <div className="gs-action-primary">
                      <ButtonItem layout="below" onClick={() => setTab("results")}>
                        View full results
                      </ButtonItem>
                    </div>
                  </div>
                </div>
                {filterBar}
                <ItemList entries={filtered} selected={selected} onSelect={setSelected}
                  lookupBusy={lookupBusy} onLookup={(id) => { void nameLookup(id); }} maxRows={6}
                  cleanupBusy={cleanupPreparing || deleting} onDelete={(e, k) => { void requestDeletion(e, k); }} />
              </section>
            </>
          )}

          {tab === "libraries" && (
            <div className="gs-library-grid">
              {(data?.disks || []).map((d, i) => {
                const percent = d.total ? Math.round(d.used * 100 / d.total) : 0;
                return (
                  <div className="gs-card gs-library" key={d.library}>
                    <div className="gs-library-name">Library {i + 1} · {d.library}</div>
                    <div className="gs-library-free">{bytes(d.free)} free</div>
                    <div className="gs-muted">{bytes(d.used)} used of {bytes(d.total)}</div>
                    <div className="gs-progress">
                      <div className="gs-progress-fill" style={{ width: percent + "%" }} />
                    </div>
                    <div className="gs-action">
                      <ButtonItem layout="below" onClick={() => {
                        setDiskId(d.library);
                        setTab("overview");
                      }}>
                        View disk overview
                      </ButtonItem>
                    </div>
                  </div>
                );
              })}
              {!data?.disks?.length && <div className="gs-empty">No accessible Steam libraries found.</div>}
            </div>
          )}

          {tab === "results" && (
            <section className="gs-card gs-section">
              <div className="gs-section-heading">
                <span className="gs-section-title">All detected data</span>
                <span className="gs-section-detail">{allEntries.length} entries · {bytes(data?.summary.bytes || 0)}</span>
              </div>
              {filterBar}
              <ItemList entries={filtered} selected={selected} onSelect={setSelected}
                lookupBusy={lookupBusy} onLookup={(id) => { void nameLookup(id); }}
                cleanupBusy={cleanupPreparing || deleting} onDelete={(e, k) => { void requestDeletion(e, k); }} />
              <div className="gs-action">
                <ButtonItem layout="below" disabled={busy} onClick={() => { void refresh(); }}>
                  <FaSyncAlt style={{ marginRight: 7 }} />{busy ? "Scanning..." : "Scan again"}
                </ButtonItem>
              </div>
            </section>
          )}

          {tab === "review" && (
            <>
              <div className="gs-note">
                <FaShieldAlt style={{ marginRight: 8 }} />
                Cleanup is permanent. A missing manifest is not proof that a folder is safe to delete.
                Open an entry and choose compatdata or shader cache to review the confirmation.
                Close running games first. Proton prefixes may contain unique saves.
              </div>
              <section className="gs-card gs-section">
                <div className="gs-section-heading">
                  <span className="gs-section-title">Items requiring verification</span>
                  <span className="gs-section-detail">
                    {allEntries.filter(item => item.status !== "installed").length} items
                  </span>
                </div>
                <ItemList entries={allEntries.filter(item => item.status !== "installed")}
                  selected={selected} onSelect={setSelected}
                  lookupBusy={lookupBusy} onLookup={(id) => { void nameLookup(id); }}
                cleanupBusy={cleanupPreparing || deleting} onDelete={(e, k) => { void requestDeletion(e, k); }} />
              </section>
            </>
          )}

          {tab === "settings" && (
            <div className="gs-card gs-settings">
              <h2 style={{ marginTop: 0 }}>GameSweep</h2>
              <p className="gs-muted">Version 0.3.1 · GitHub: Viber85/game_sweeper</p>
              <p className="gs-muted">Fullscreen SteamOS Game Mode interface with guarded, opt-in deletion.</p>
              <div className="gs-settings-row">
                <div>
                  <strong>GitHub updates</strong>
                  <div className="gs-muted">Check releases and request installation through Decky.</div>
                </div>
                <ButtonItem layout="below" disabled={updateBusy} onClick={() => { void findUpdate(); }}>
                  <FaSyncAlt style={{ marginRight: 7 }} />{updateBusy ? "Checking..." : "Check for updates"}
                </ButtonItem>
              </div>
              {updateRequestSent && (
                <div className="gs-muted" style={{ padding: "12px 0", color: "#80d1b2" }}>
                  Update request sent to Decky Loader. Approve the installation in Decky's confirmation dialog.
                  This message does not confirm installation is complete.
                </div>
              )}
              {updateInfo && (
                <div className="gs-settings-row">
                  <span className="gs-muted">{updateInfo.error ? "Failed: " + updateInfo.error :
                    updateInfo.available ? "Update available: " + updateInfo.version :
                    "Already on the latest available release."}</span>
                  {updateInfo.available &&
                    <ButtonItem layout="below" disabled={updateBusy} onClick={() => { void applyUpdate(); }}>
                      <FaDownload style={{ marginRight: 7 }} />Install update
                    </ButtonItem>}
                </div>
              )}
              <div className="gs-settings-row">
                <div>
                  <strong>Storage scan</strong>
                  <div className="gs-muted">Refresh installed manifests, compatdata, caches, and available disks.</div>
                </div>
                <ButtonItem layout="below" disabled={busy} onClick={() => { void refresh(); }}>
                  <FaSyncAlt style={{ marginRight: 7 }} />{busy ? "Scanning..." : "Scan now"}
                </ButtonItem>
              </div>
              <div className="gs-note" style={{ marginTop: 20 }}>
                Deletion is permanent. No backup or undo is available. Verify the game and save files first.
              </div>
            </div>
          )}

          {busy && !data && <div className="gs-loading">Scanning Steam libraries…</div>}
        </main>
        {deletePreview && (
          <div className="gs-modal-layer" role="dialog" aria-modal="true" aria-label="Confirm permanent deletion">
            <div className="gs-modal" ref={dialogRef}>
              <div className="gs-modal-symbol"><FaExclamationTriangle /></div>
              <h2>Confirm permanent deletion</h2>
              <p className="gs-modal-subtitle">
                This operation cannot be undone. No backup is created.
              </p>
              <div className="gs-modal-details">
                <strong>{deletePreview.name || "Unknown game"}</strong>
                <span>AppID {deletePreview.appid}</span>
                <span>
                  {deletePreview.kind === "prefix" ? "Proton compatdata" : "Shader cache"}
                  {" · "}{bytes(deletePreview.bytes || 0)}
                </span>
                <span style={{ overflowWrap: "anywhere" }}>{deletePreview.path}</span>
              </div>
              <div className="gs-modal-warning">
                {deletePreview.kind === "prefix" ?
                  "Compatdata can contain save files, configurations, and launcher data. Deleting it can permanently erase progress." :
                  "Shader caches must be regenerated. Loading may be slower or stutter initially."}
                {deletePreview.status === "review" &&
                  " This may be a removed Non-Steam game, and its identity or ownership cannot be verified."}
              </div>
              <div className="gs-modal-action">
                <ButtonItem layout="below" disabled={deleting}
                  onClick={() => { setDeletePreview(null); setDeleteAcknowledged(false); }}>
                  Cancel
                </ButtonItem>
                <ButtonItem layout="below" disabled={deleting}
                  onClick={() => setDeleteAcknowledged(!deleteAcknowledged)}>
                  {deleteAcknowledged ? "✓ I understand permanent data loss" : "□ I understand permanent data loss"}
                </ButtonItem>
                <div className="gs-delete-button">
                  <ButtonItem layout="below" disabled={!deleteAcknowledged || deleting}
                    onClick={() => { void confirmDeletion(); }}>
                    {deleting ? "Deleting…" : "Delete permanently"}
                  </ButtonItem>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </Focusable>
  );
}
