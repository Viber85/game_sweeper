import {
  ButtonItem, PanelSection, PanelSectionRow, staticClasses
} from "@decky/ui";
import { call, callable, definePlugin } from "@decky/api";
import { useEffect, useMemo, useState } from "react";
import {
  FaBroom, FaCog, FaDownload, FaExclamationTriangle,
  FaHdd, FaInfoCircle, FaSearch, FaShieldAlt, FaSyncAlt
} from "react-icons/fa";

type ItemStatus = "installed" | "candidate" | "review";
type ScanEntry = {
  id: string; name: string; name_source: string;
  status: ItemStatus; reason: string; library: string;
  prefix_path: string; shader_path: string;
  prefix_bytes: number; shader_bytes: number; bytes: number;
};
type ScanData = {
  scanned_at: string;
  libraries: string[];
  missing_libraries: string[];
  entries: ScanEntry[];
  summary: {
    items: number; installed: number; candidate: number;
    review: number; bytes: number; candidate_bytes: number;
  };
};
type UpdateInfo = {
  available: boolean; version: string; url: string;
  notes?: string; sha256?: string; error?: string;
};
type NameInfo = { found: boolean; name: string; error?: string };
type Filter = "all" | "candidate" | "review" | "installed";

const scanStorage = callable<[], ScanData>("scan_storage");
const checkUpdate = callable<[], UpdateInfo>("check_update");
const resolveName = callable<[appid: string], NameInfo>("resolve_name");

function formatBytes(size: number): string {
  if (size <= 0) return "0 B";
  const exp = Math.min(Math.floor(Math.log(size) / Math.log(1024)), 4);
  const properUnits = ["B", "KB", "MB", "GB", "TB"];
  return (size / Math.pow(1024, exp)).toFixed(exp ? 1 : 0) + " " + properUnits[exp];
}

const palette = {
  body: "#dce6f2", muted: "#91a0ae", border: "rgba(255,255,255,0.09)",
  bg: "#192530", blue: "#74baff", amber: "#f2c27d", green: "#80d1b2"
};

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div style={{
      flex: 1, padding: "12px", borderRadius: "10px",
      border: "1px solid " + palette.border, background: palette.bg
    }}>
      <div style={{ color: palette.muted, fontSize: "12px" }}>{label}</div>
      <div style={{ color: palette.body, fontSize: "20px", fontWeight: 700, marginTop: "3px" }}>{value}</div>
    </div>
  );
}

function Chip({ text, color }: { text: string; color: string }) {
  return (
    <span style={{
      display: "inline-block", color, fontSize: "11px", borderRadius: "5px",
      border: "1px solid " + color, padding: "2px 6px", whiteSpace: "nowrap"
    }}>{text}</span>
  );
}

function Content() {
  const [data, setData] = useState<ScanData | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [filter, setFilter] = useState<Filter>("all");
  const [selected, setSelected] = useState("");
  const [settings, setSettings] = useState(false);
  const [update, setUpdate] = useState<UpdateInfo | null>(null);
  const [updating, setUpdating] = useState(false);
  const [resolving, setResolving] = useState("");

  async function refresh() {
    if (busy) return;
    setBusy(true);
    setError("");
    try {
      setData(await scanStorage());
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => { void refresh(); }, []);

  async function lookUp(id: string) {
    setResolving(id);
    setError("");
    try {
      const result = await resolveName(id);
      if (result.found) await refresh();
      else setError(result.error || "Steam could not identify this AppID.");
    } catch (err) {
      setError(String(err));
    } finally {
      setResolving("");
    }
  }

  async function findUpdate() {
    setUpdating(true);
    setError("");
    try {
      setUpdate(await checkUpdate());
    } catch (err) {
      setError(String(err));
    } finally {
      setUpdating(false);
    }
  }

  async function applyUpdate() {
    if (!update?.available || !update.url) return;
    setUpdating(true);
    setError("");
    try {
      // Use Decky's own installer, which displays its confirmation modal.
      // InstallType.UPDATE = 2 in decky-loader.
      await call<[string, string, string, string, number], void>(
        "utilities/install_plugin", update.url, "GameSweep", update.version, update.sha256 || "", 2
      );
    } catch (err) {
      setError("Update request failed: " + String(err));
    } finally {
      setUpdating(false);
    }
  }

  const entries = useMemo(
    () => (data?.entries || []).filter(item => filter === "all" || item.status === filter),
    [data, filter]
  );

  return (
    <div style={{ color: palette.body, paddingBottom: "16px" }}>
      <PanelSection title="Storage overview">
        <PanelSectionRow>
          <div style={{ display: "flex", gap: "8px", width: "100%" }}>
            <Stat label="Scanned data" value={formatBytes(data?.summary.bytes || 0)} />
            <Stat label="Possible leftovers" value={formatBytes(data?.summary.candidate_bytes || 0)} />
          </div>
        </PanelSectionRow>
        <PanelSectionRow>
          <div style={{ fontSize: "12px", color: palette.muted, margin: "5px 0" }}>
            {data ? String(data.summary.items) + " entries in " + String(data.libraries.length) + " libraries" : "Not scanned yet"}
            {" • "}Read-only preview
          </div>
        </PanelSectionRow>
        <PanelSectionRow>
          <ButtonItem layout="below" onClick={() => { void refresh(); }} disabled={busy}>
            <FaSyncAlt style={{ marginRight: 8 }} />
            {busy ? "Scanning storage..." : "Scan again"}
          </ButtonItem>
        </PanelSectionRow>
        {!!data?.missing_libraries.length && (
          <PanelSectionRow>
            <div style={{
              color: palette.amber, padding: "9px", border: "1px solid " + palette.amber,
              borderRadius: "8px", fontSize: "12px"
            }}>
              <FaExclamationTriangle style={{ marginRight: 6 }} />
              {data.missing_libraries.length} unavailable library path(s). All uninstalled-looking entries require review.
            </div>
          </PanelSectionRow>
        )}
      </PanelSection>

      <PanelSection title="Compatibility data">
        <PanelSectionRow>
          <div style={{ display: "flex", gap: "4px", width: "100%", flexWrap: "wrap" }}>
            {([
              ["all", "All"], ["candidate", "Possible leftovers"],
              ["review", "Review"], ["installed", "Installed"]
            ] as [Filter, string][]).map(([value, label]) => (
              <div key={value} style={{ flex: "1 1 45%", minWidth: "105px" }}>
                <ButtonItem layout="below" onClick={() => setFilter(value)}>
                  <span style={{ color: filter === value ? palette.blue : palette.body }}>{label}</span>
                </ButtonItem>
              </div>
            ))}
          </div>
        </PanelSectionRow>

        {entries.map(item => {
          const active = selected === item.library + ":" + item.id;
          const key = item.library + ":" + item.id;
          const statusText = item.status === "installed" ? "Installed" :
            item.status === "candidate" ? "Possible leftover" : "Needs review";
          const color = item.status === "installed" ? palette.green :
            item.status === "candidate" ? palette.blue : palette.amber;
          return (
            <PanelSectionRow key={key}>
              <ButtonItem layout="below" onClick={() => setSelected(active ? "" : key)}>
                <div style={{ display: "flex", alignItems: "center", gap: "10px", width: "100%" }}>
                  <FaHdd color={color} style={{ flexShrink: 0 }} />
                  <div style={{ flex: 1, minWidth: 0, textAlign: "left" }}>
                    <div style={{ fontWeight: 600, overflowWrap: "anywhere" }}>{item.name}</div>
                    <div style={{ fontSize: "11px", color: palette.muted }}>AppID {item.id}</div>
                    <Chip text={statusText} color={color} />
                  </div>
                  <strong style={{ whiteSpace: "nowrap" }}>{formatBytes(item.bytes)}</strong>
                </div>
              </ButtonItem>
              {active && (
                <div style={{
                  background: palette.bg, borderRadius: "9px", padding: "10px",
                  fontSize: "12px", color: palette.muted, overflowWrap: "anywhere"
                }}>
                  <div style={{ color: palette.body, marginBottom: "5px" }}>{item.reason}</div>
                  <div>Compatdata: {formatBytes(item.prefix_bytes)}</div>
                  <div>Shader cache: {formatBytes(item.shader_bytes)}</div>
                  <div>Library: {item.library}</div>
                  {!!item.prefix_path && <div>Prefix: {item.prefix_path}</div>}
                  {!!item.shader_path && <div>Shaders: {item.shader_path}</div>}
                  {item.name_source === "unknown" && item.status !== "review" && (
                    <ButtonItem layout="below"
                      disabled={resolving === item.id}
                      onClick={() => { void lookUp(item.id); }}>
                      <FaSearch style={{ marginRight: 8 }} />
                      {resolving === item.id ? "Looking up..." : "Find game name online"}
                    </ButtonItem>
                  )}
                </div>
              )}
            </PanelSectionRow>
          );
        })}
        {!busy && data && entries.length === 0 && (
          <PanelSectionRow>
            <div style={{ color: palette.muted, fontSize: "12px", padding: "8px" }}>
              No items in this filter.
            </div>
          </PanelSectionRow>
        )}
      </PanelSection>

      <PanelSection title="Settings & updates">
        <PanelSectionRow>
          <ButtonItem layout="below" onClick={() => setSettings(!settings)}>
            <FaCog style={{ marginRight: 8 }} />{settings ? "Hide settings" : "Open settings"}
          </ButtonItem>
        </PanelSectionRow>
        {settings && (
          <>
            <PanelSectionRow>
              <div style={{ color: palette.muted, fontSize: "12px", padding: "6px" }}>
                Version 0.1.0 • GitHub: Viber85/game_sweeper
                <div style={{ marginTop: "5px" }}>
                  No file deletion is implemented in this version.
                </div>
              </div>
            </PanelSectionRow>
            <PanelSectionRow>
              <ButtonItem layout="below" disabled={updating} onClick={() => { void findUpdate(); }}>
                <FaSyncAlt style={{ marginRight: 8 }} />
                {updating ? "Checking GitHub..." : "Check GitHub updates"}
              </ButtonItem>
            </PanelSectionRow>
            {update && (
              <PanelSectionRow>
                <div style={{ fontSize: "12px", color: palette.muted, padding: "5px" }}>
                  {update.error ? "Update check failed: " + update.error :
                    update.available ? "New version available: " + update.version :
                    "No newer GitHub release available."}
                </div>
              </PanelSectionRow>
            )}
            {update?.available && (
              <PanelSectionRow>
                <ButtonItem layout="below" disabled={updating} onClick={() => { void applyUpdate(); }}>
                  <FaDownload style={{ marginRight: 8 }} />
                  Update to {update.version} (Decky confirmation)
                </ButtonItem>
              </PanelSectionRow>
            )}
            <PanelSectionRow>
              <div style={{ fontSize: "12px", color: palette.muted, padding: "5px" }}>
                <FaShieldAlt style={{ marginRight: 5 }} />
                Steam save files may live inside compatdata. A missing manifest is not proof that deletion is safe.
              </div>
            </PanelSectionRow>
          </>
        )}
      </PanelSection>

      {!!error && (
        <PanelSection title="Notice">
          <PanelSectionRow>
            <div style={{ fontSize: "12px", color: palette.amber, overflowWrap: "anywhere" }}>
              <FaInfoCircle style={{ marginRight: 6 }} />{error}
            </div>
          </PanelSectionRow>
        </PanelSection>
      )}
    </div>
  );
}

export default definePlugin(() => ({
  name: "GameSweep",
  titleView: <div className={staticClasses.Title}>GameSweep</div>,
  content: <Content />,
  icon: <FaBroom />,
}));
