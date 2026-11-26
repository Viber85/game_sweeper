import { ButtonItem, Focusable, Navigation, Router } from "@decky/ui";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode, CSSProperties } from "react";
import {
  FaBroom, FaCog, FaDownload, FaExclamationTriangle, FaFolderOpen, FaHdd,
  FaHome, FaList, FaSave, FaSearch, FaSyncAlt, FaUndo,
  FaArrowLeft, FaArrowUp, FaInfoCircle,
  FaChevronRight
} from "react-icons/fa";
import {
  bytes, scanStorage, resolveName, checkUpdate, requestDeckyUpdate,
  prepareCleanup, deleteStorage, previewSaveBackup, createSaveBackup,
  listSaveBackups, prepareSaveRestore, restoreSaveBackup, getBackupLocation,
  browseBackupFolders, chooseBackupLocation, resetBackupLocation,
  browseSaveFolders, chooseSaveFolder, resetSaveFolder
} from "./api";
import type {
  Entry, ScanData, Status, GameType, CleanupKind, CleanupPreview,
  SaveSnapshot, SavePreview, RestorePreview, BackupLocation,
  DirectoryBrowser, ManualSaveBrowser, UpdateInfo
} from "./api";
import { modernStyle } from "./modernStyles";
import { focusGameSweepFirstButton, useGameSweepGamepadFocus } from "./focus";

type View = "overview" | "games" | "backups" | "settings";
type Dialog =
  | { kind: "cleanupChoice"; entry: Entry }
  | { kind: "cleanupConfirm"; entry: Entry; preview: CleanupPreview }
  | { kind: "backupPreview"; entry: Entry; preview: SavePreview }
  | { kind: "notFound"; entry: Entry; message: string }
  | { kind: "restoreConfirm"; preview: RestorePreview }
  | { kind: "storagePicker"; browser: DirectoryBrowser }
  | { kind: "savePicker"; entry: Entry; browser: ManualSaveBrowser }
  | null;

const SECTIONS: Array<{id:View;label:string;icon:ReactNode}> = [
  {id:"overview",label:"Overview",icon:<FaHome/>},
  {id:"games",label:"Games",icon:<FaList/>},
  {id:"backups",label:"Save Backups",icon:<FaSave/>},
  {id:"settings",label:"Settings",icon:<FaCog/>},
];

function leave():void{
  Router.CloseSideMenus();
  // Navigation.NavigateBack does not exist in the installed Decky API.
  try { Navigation.Navigate("/library/home"); }
  catch { Router.Navigate("/library/home"); }
}

function Action({children,onClick,kind="secondary",disabled=false}:{
  children:ReactNode;onClick:()=>void;kind?:"primary"|"secondary"|"danger";
  disabled?:boolean;
}){
  return <div className={"gm-"+kind}>
    <ButtonItem layout="below" disabled={disabled} onClick={onClick}>{children}</ButtonItem>
  </div>;
}

function Badge({entry}:{entry:Entry}){
  return <span className={"gm-status "+(entry.status==="installed"?"":entry.status==="review"?"review":"candidate")}>
    {entry.status==="installed"?"Registered":entry.status==="review"?"Needs review":"Potential leftover"}
  </span>;
}

function Source({value}:{value:GameType}){
  return <span className={"gm-source "+(value==="non_steam"?"non":value==="unknown"?"unknown":"")}>
    {value==="steam"?"Steam":value==="non_steam"?"Non-Steam":"Unknown"}
  </span>;
}

function GameTable({items,onOpen}:{items:Entry[];onOpen:(entry:Entry)=>void}){
  if(!items.length)return <div className="gm-empty">No games match these filters. Run a scan or change the filters.</div>;
  return <div className="gm-card gm-game-table">
    <div className="gm-table-head">
      <span>Game / storage</span><span>AppID</span><span className="gm-col-status">Status</span>
      <span style={{textAlign:"right"}}>Size</span><span/>
    </div>
    {items.map(entry=><div className="gm-game-row-wrap" key={entry.library+"|"+entry.id}>
      <ButtonItem layout="below" onClick={()=>onOpen(entry)}>
        <div className="gm-game-row-content">
          <div className="gm-game-cell">
            <div style={{minWidth:0}}>
              <div className="gm-game-name">{entry.name}</div>
              <div className="gm-game-sub">
                <Source value={entry.game_type}/>
                <span>{entry.prefix_bytes>0?"Proton data":entry.shader_bytes>0?"Shader cache":"Game data"}</span>
              </div>
            </div>
          </div>
          <span className="gm-table-id">{entry.id}</span>
          <span className="gm-col-status"><Badge entry={entry}/></span>
          <span className="gm-table-size">{bytes(entry.bytes)}</span>
          <FaChevronRight className="gm-game-chevron"/>
        </div>
      </ButtonItem>
    </div>)}
  </div>;
}

function Metric({title,value,note,accent=false}:{
  title:string;value:string;note:string;accent?:boolean;
}){
  return <div className={"gm-metric"+(accent?" gm-metric-highlight":"")}>
    <div><div className="gm-metric-head">{title}</div><small>{note}</small></div>
    <strong>{value}</strong>
  </div>;
}

function ConfirmCheck({value,onChange,children}:{value:boolean;onChange:(v:boolean)=>void;children:ReactNode}){
  return <label className="gm-check">
    <input type="checkbox" checked={value} onChange={e=>onChange(e.currentTarget.checked)}/>
    <span>{children}</span>
  </label>;
}

function Modal({children,onCancel,title}:{children:ReactNode;onCancel:()=>void;title:string}){
  return <div className="gm-modal-backdrop">
    <div className="gs-modal gm-modal" role="dialog" aria-modal="true" aria-label={title}>
      <h2>{title}</h2>{children}
      <div className="gm-modal-actions">
        <Action onClick={onCancel}>Cancel / Back</Action>
      </div>
    </div>
  </div>;
}

function ErrorBanner({message,onDismiss}:{message:string;onDismiss:()=>void}){
  return message?<div className="gm-banner error" role="alert">
    <FaExclamationTriangle style={{marginRight:9}}/>{message}
    <button onClick={onDismiss} aria-label="Dismiss error" style={{float:"right",color:"inherit",background:"none",border:0}}>×</button>
  </div>:null;
}

export function ModernGameSweep(){
  const rootRef=useRef<HTMLDivElement>(null);
  const mainRef=useRef<HTMLElement>(null);
  const [view,setView]=useState<View>("overview");
  const [scan,setScan]=useState<ScanData|null>(null);
  const [busy,setBusy]=useState(false);
  const [scanning,setScanning]=useState(false);
  const [error,setError]=useState("");
  const [notice,setNotice]=useState("");
  const [entry,setEntry]=useState<Entry|null>(null);
  const [dialog,setDialog]=useState<Dialog>(null);
  const [ack,setAck]=useState(false);
  const [installedAck,setInstalledAck]=useState(false);
  const [choice,setChoice]=useState<CleanupKind>("all");
  const [search,setSearch]=useState("");
  const [status,setStatus]=useState<Status|"all">("all");
  const [source,setSource]=useState<GameType|"all">("all");
  const [sort,setSort]=useState("size");
  const [disk,setDisk]=useState("all");
  const [snapshots,setSnapshots]=useState<SaveSnapshot[]>([]);
  const [location,setLocation]=useState<BackupLocation|null>(null);
  const [update,setUpdate]=useState<UpdateInfo|null>(null);
  const [updateLoading,setUpdateLoading]=useState(false);
  const [returnDialog,setReturnDialog]=useState<Dialog>(null);
  const [visibleLimit,setVisibleLimit]=useState(60);

  useGameSweepGamepadFocus(rootRef,dialog!==null);

  useEffect(()=>{
    const t=window.setTimeout(()=>{
      if(rootRef.current)focusGameSweepFirstButton(rootRef.current,".gs-nav .DialogButton");
    },250);
    return ()=>window.clearTimeout(t);
  },[]);

  useEffect(()=>{
    if(!dialog)return;
    const t=window.setTimeout(()=>{
      if(rootRef.current)focusGameSweepFirstButton(rootRef.current,".gs-modal .DialogButton");
    },90);
    return ()=>window.clearTimeout(t);
  },[dialog?.kind]);

  const refresh=useCallback(async()=>{
    setScanning(true);setError("");
    try{
      const result=await scanStorage();
      setScan(result);
      if(result.missing_libraries?.length){
        setNotice("Some Steam libraries are unavailable. Destructive actions will be blocked.");
      }
    }catch(e){setError("Storage scan failed: "+String(e));}
    finally{setScanning(false);}
  },[]);

  const loadBackups=useCallback(async()=>{
    try{
      const r=await listSaveBackups("");
      if(!r.ok)throw new Error(r.error||"Cannot list save snapshots");
      setSnapshots(r.backups);
    }catch(e){setError("Backups: "+String(e));}
  },[]);

  const loadLocation=useCallback(async()=>{
    try{
      const r=await getBackupLocation();
      if(!r.ok)throw new Error(r.error||"Backup location unavailable");
      setLocation(r);
    }catch(e){setError(String(e));}
  },[]);

  useEffect(()=>{void refresh();void loadBackups();void loadLocation();},[refresh,loadBackups,loadLocation]);

  function navigate(page:View){
    setView(page);setEntry(null);setNotice("");setError("");setVisibleLimit(60);
    mainRef.current?.scrollTo({top:0,behavior:"auto"});
    if(page==="backups"){void loadBackups();void loadLocation();}
  }

  function back(){
    if(busy)return;
    if(dialog){
      setDialog(dialog.kind==="storagePicker"&&returnDialog?returnDialog:null);
      setReturnDialog(null);setError("");return;
    }
    if(entry){setEntry(null);return;}
    leave();
  }

  const all=scan?.entries||[];
  const visible=useMemo(()=>all.filter(item=>
    (disk==="all"||disk===item.library)&&
    (status==="all"||item.status===status)&&
    (source==="all"||item.game_type===source)&&
    (!search||item.name.toLowerCase().includes(search.toLowerCase())||item.id.includes(search))
  ).sort((a,b)=>sort==="name"?a.name.localeCompare(b.name):sort==="status"?a.status.localeCompare(b.status):b.bytes-a.bytes),[scan,disk,status,source,search,sort]);
  const topGames=useMemo(()=>[...all].sort((a,b)=>b.bytes-a.bytes).slice(0,5),[scan]);
  const disks=scan?.disks||[];
  const activeDisk=disks.find(d=>d.library===disk)||disks[0];
  const usedPct=activeDisk?.total?Math.max(0,Math.min(100,Math.round(100*activeDisk.used/activeDisk.total))):0;
  const prefixTotal=all.reduce((s,i)=>s+i.prefix_bytes,0);
  const shaderTotal=all.reduce((s,i)=>s+i.shader_bytes,0);
  const candidates=all.filter(x=>x.status!=="installed");
  const reviewCount=all.filter(x=>x.status==="review").length;
  const potential=scan?.summary.candidate_bytes??candidates.reduce((s,x)=>s+x.bytes,0);
  const loading=scanning||busy;

  async function handleRun(task:()=>Promise<void>){
    if(busy)return;
    setBusy(true);setError("");
    try{await task();}
    catch(e){setError(String(e));}
    finally{setBusy(false);}
  }

  function beginCleanup(item:Entry){
    setEntry(null);setChoice(item.prefix_path&&item.shader_path?"all":item.prefix_path?"prefix":"shader");
    setAck(false);setInstalledAck(false);
    setDialog({kind:"cleanupChoice",entry:item});
  }

  function prepareDelete(item:Entry,kind:CleanupKind){
    void handleRun(async()=>{
      const p=await prepareCleanup(item.library,item.id,kind,item.status==="installed");
      if(!p.ok||!p.token)throw new Error(p.error||"Cleanup preview failed");
      setAck(false);setInstalledAck(false);
      setDialog({kind:"cleanupConfirm",entry:item,preview:p});
    });
  }

  function confirmDelete(p:CleanupPreview){
    if(!p.token)return;
    void handleRun(async()=>{
      const key=p.status==="installed"?"PERMANENT_DELETE_INSTALLED":"PERMANENT_DELETE";
      const result=await deleteStorage(p.token!,key);
      if(!result.ok||!result.success)throw new Error(result.error||"Cleanup failed");
      setNotice("Removed "+(p.kind==="all"?"prefix and shader cache":p.kind==="prefix"?"compatdata":"shader cache")+" for "+(p.name||p.appid)+".");
      setDialog(null);setEntry(null);await refresh();
    });
  }

  function beginSave(item:Entry){
    setEntry(null);
    void handleRun(async()=>{
      const p=await previewSaveBackup(item.library,item.id);
      if(!p.ok)throw new Error(p.error||"Save detection failed");
      if(!p.supported||!p.count){
        setDialog({kind:"notFound",entry:item,message:p.message||"No save files identified. This does not mean the game has no saves."});
      }else{
        setAck(false);setDialog({kind:"backupPreview",entry:item,preview:p});
      }
    });
  }

  function doBackup(item:Entry){
    void handleRun(async()=>{
      const r=await createSaveBackup(item.library,item.id);
      if(!r.ok)throw new Error(r.error||"Save backup failed");
      setNotice("Saved "+(r.count||0)+" save file(s) to "+(r.backup_folder||location?.folder||"the backup folder")+".");
      setDialog(null);await loadBackups();
    });
  }

  function beginRestore(id:string){
    void handleRun(async()=>{
      const r=await prepareSaveRestore(id);
      if(!r.ok||!r.token)throw new Error(r.error||"Restore unavailable");
      setAck(false);
      setDialog({kind:"restoreConfirm",preview:r});
    });
  }

  function doRestore(p:RestorePreview){
    if(!p.token)return;
    void handleRun(async()=>{
      const r=await restoreSaveBackup(p.token!,"RESTORE_OVERWRITE");
      if(!r.ok)throw new Error(r.error||"Restore failed");
      setNotice("Restored "+(r.count||0)+" save files for "+(r.name||p.name)+".");
      setDialog(null);await refresh();
    });
  }

  function openLocationPicker(path:string=""){
    if(!path && dialog?.kind==="backupPreview")setReturnDialog(dialog);
    void handleRun(async()=>{
      const r=await browseBackupFolders(path);
      if(!r.ok)throw new Error(r.error||"Cannot browse folders");
      setDialog({kind:"storagePicker",browser:r});
    });
  }

  function chooseStorage(path:string){
    void handleRun(async()=>{
      const r=await chooseBackupLocation(path);
      if(!r.ok)throw new Error(r.error||"Cannot use selected folder");
      setLocation(r);setDialog(returnDialog);setReturnDialog(null);
      setNotice("Future backups will be saved in "+r.folder+".");
      await loadBackups();
    });
  }

  function defaultStorage(){
    void handleRun(async()=>{
      const r=await resetBackupLocation();
      if(!r.ok)throw new Error(r.error||"Reset failed");
      setLocation(r);setNotice("Backup location reset.");await loadBackups();
    });
  }

  function openSavePicker(item:Entry,rel:string=""){
    void handleRun(async()=>{
      const r=await browseSaveFolders(item.library,item.id,rel);
      if(!r.ok)throw new Error(r.error||"Cannot browse this game prefix");
      setDialog({kind:"savePicker",entry:item,browser:r});
    });
  }

  function chooseSaveDirectory(item:Entry,rel:string){
    void handleRun(async()=>{
      const r=await chooseSaveFolder(item.library,item.id,rel);
      if(!r.ok)throw new Error(r.error||"Invalid save folder");
      const p=await previewSaveBackup(item.library,item.id);
      if(!p.ok||!p.count){setDialog({kind:"notFound",entry:item,message:p.message||"No files found"});return;}
      setDialog({kind:"backupPreview",entry:item,preview:p});
    });
  }

  function resetSaveDirectory(item:Entry){
    void handleRun(async()=>{
      const r=await resetSaveFolder(item.library,item.id);
      if(!r.ok)throw new Error(r.error||"Reset failed");
      const p=await previewSaveBackup(item.library,item.id);
      if(!p.ok||!p.count)setDialog({kind:"notFound",entry:item,message:p.message||"No save files found"});
      else setDialog({kind:"backupPreview",entry:item,preview:p});
    });
  }

  function lookupName(item:Entry){
    void handleRun(async()=>{
      const r=await resolveName(item.id);
      if(!r.found)throw new Error(r.error||"No Steam Store name matches this AppID.");
      setNotice("Resolved "+item.id+": "+r.name);
      setEntry(null);await refresh();
    });
  }

  function checkForUpdates(){
    if(updateLoading)return;
    setUpdateLoading(true);setError("");
    void checkUpdate().then(setUpdate).catch(e=>setError(String(e))).finally(()=>setUpdateLoading(false));
  }

  function installUpdate(){
    if(!update)return;
    void handleRun(async()=>{await requestDeckyUpdate(update);});
  }

  return <Focusable onCancelButton={back} style={{width:"100%",height:"100%",minHeight:0}}>
    <div ref={rootRef} className="gm-shell">
      <style>{modernStyle}</style>
      <aside className="gm-rail">
        <div className="gm-brand"><span className="gm-logo"><FaBroom/></span>
          <div><strong>GameSweep</strong><small>Storage manager</small></div>
        </div>
        <nav className="gs-nav gm-nav">
          {SECTIONS.map(section=><div className={"gm-nav-item"+(view===section.id?" active gs-active":"")} key={section.id}>
            <ButtonItem layout="below" onClick={()=>navigate(section.id)}>
              {section.icon}<span>{section.label}</span>
              {section.id==="games"&&all.length>0?<small className="gm-nav-count">{all.length}</small>:null}
            </ButtonItem>
          </div>)}
        </nav>
        <div className="gm-rail-footer">
          <div>SteamOS Game Mode</div>
          <div>↑↓←→ Navigate · A Select</div>
          <div>B Back / Close</div>
          <div>v0.8.1 test</div>
        </div>
      </aside>
      <main ref={mainRef} className="gs-main gm-main">
        <div className="gm-inner">
          <header className="gm-header">
            <div>
              <h1>{view==="overview"?"Storage overview":view==="games"?"Games":view==="backups"?"Save backups":"Settings"}</h1>
              <p className="gm-lede">{view==="overview"?"Disk usage, Proton data and shader caches.":view==="games"?"Review stored game data before removing it.":view==="backups"?"Back up and restore detected save files.":"Storage, updates and interface settings."}</p>
            </div>
            <div className="gm-header-actions">
              <span className="gm-smallnote">{scan?.scanned_at?"Scanned "+new Date(scan.scanned_at).toLocaleTimeString():"Not scanned"}</span>
              <Action kind="primary" onClick={()=>{void refresh();}} disabled={loading}><FaSyncAlt/> {scanning?"Scanning…":"Scan storage"}</Action>
            </div>
          </header>
          <ErrorBanner message={error} onDismiss={()=>setError("")}/>
          {notice?<div className="gm-banner"><FaInfoCircle style={{marginRight:7}}/>{notice}</div>:null}

          {view==="overview"&&<div>
            <div className="gm-overview-top">
              <div className="gm-card gm-storage">
                <div className="gm-storage-head">
                  <div><div className="gm-card-title">Disk usage</div></div>
                  <select className="gm-select" aria-label="Storage drive" value={disk==="all"?"all":disk}
                    onChange={e=>setDisk(e.currentTarget.value)}>
                    <option value="all">Primary drive</option>
                    {disks.map((d,i)=><option key={d.library} value={d.library}>Drive {i+1} · {d.library.split("/").pop()}</option>)}
                  </select>
                </div>
                <div className="gm-donut-line">
                  <div className="gm-donut" style={{"--fill":`${usedPct}%`} as CSSProperties}>
                    <div className="gm-donut-label"><strong>{activeDisk?`${usedPct}%`:"—"}</strong><small>Used</small></div>
                  </div>
                  <div className="gm-storage-values">
                    <div><strong>{activeDisk?bytes(activeDisk.free):"—"}</strong><small>Free space</small></div>
                    <div><strong>{activeDisk?bytes(activeDisk.used):"—"}</strong><small>Used space</small></div>
                  </div>
                </div>
                <div className="gm-legend"><span>Total capacity</span><strong>{activeDisk?bytes(activeDisk.total):"Not scanned"}</strong></div>
              </div>
              <div className="gm-metrics"><h2>Game data</h2>
                <Metric title="Compatdata" value={bytes(prefixTotal)} note="Proton prefix data"/>
                <Metric title="Shader cache" value={bytes(shaderTotal)} note="Rebuildable graphics data"/>
                <Metric title="Potential cleanup" value={bytes(potential)} note="Review before deletion" accent/>
                <Metric title="Save backups" value={String(snapshots.length)} note="Saved snapshots"/>
              </div>
            </div>
            {reviewCount>0?<div className="gm-review-banner">
              <div><strong>{reviewCount} {reviewCount===1?"game needs":"games need"} review</strong><small>Review uncertain entries before deleting data.</small></div>
              <Action onClick={()=>{setStatus("review");navigate("games");}}>Review games <FaChevronRight/></Action>
            </div>:null}
            <div className="gm-section-head">
              <div><h2>Largest game data</h2><small>Biggest compatdata and shader cache folders</small></div>
              <Action onClick={()=>navigate("games")}>View all games <FaChevronRight/></Action>
            </div>
            <GameTable items={topGames} onOpen={setEntry}/>
          </div>}

          {view==="games"&&<div>
            <div className="gm-filters">
              <input className="gm-search" aria-label="Search games" placeholder="Search game title or AppID…"
                value={search} onChange={e=>setSearch(e.currentTarget.value)}/>
              <select className="gm-filter-select" aria-label="Filter status" value={status} onChange={e=>setStatus(e.currentTarget.value as Status|"all")}>
                <option value="all">All statuses</option><option value="installed">Registered</option>
                <option value="candidate">Potential leftovers</option><option value="review">Needs review</option>
              </select>
              <select className="gm-filter-select" aria-label="Filter source" value={source} onChange={e=>setSource(e.currentTarget.value as GameType|"all")}>
                <option value="all">All sources</option><option value="steam">Steam</option><option value="non_steam">Non-Steam</option><option value="unknown">Unknown source</option>
              </select>
              <select className="gm-filter-select" aria-label="Sort games" value={sort} onChange={e=>setSort(e.currentTarget.value)}>
                <option value="size">Largest first</option><option value="name">Name A–Z</option><option value="status">Status</option>
              </select>
            </div>
            <div className="gm-section-head"><div><h2>Scan results</h2><small>{visible.length} of {all.length} entries · select a game to open details</small></div></div>
            <GameTable items={visible.slice(0,visibleLimit)} onOpen={setEntry}/>
            {visible.length>visibleLimit?<div className="gm-section-head">
              <span className="gm-smallnote">Showing {Math.min(visibleLimit,visible.length)} of {visible.length} entries</span>
              <Action onClick={()=>setVisibleLimit(v=>v+60)}>Show 60 more games</Action>
            </div>:null}
          </div>}

          {view==="backups"&&<div>
            <div className="gm-card gm-settings-card">
              <div className="gm-setting-line">
                <div><div className="gm-card-title">Backup destination</div>
                  <div className="gm-note">Choose internal SSD, microSD or a mounted drive</div></div>
                <Action onClick={()=>openLocationPicker()}><FaFolderOpen/> Choose folder</Action>
              </div>
              <div className="gm-setting-path">{location?.folder||"Default: ~/.local/share/GameSweep/save-backups"}</div>
              <div className="gm-setting-line"><span className="gm-smallnote">{location?.free!==undefined?bytes(location.free)+" free":"Select a destination to view free space"}</span>
                <Action onClick={defaultStorage} disabled={loading}>Use default</Action></div>
            </div>
            <div className="gm-section-head">
              <div><h2>Backup history</h2><small>{snapshots.length} saved snapshots; no full-prefix copies</small></div>
              <Action onClick={()=>{void loadBackups();}}>Refresh <FaSyncAlt/></Action>
            </div>
            <div className="gm-card">
              {!snapshots.length?<div className="gm-empty">No save backups yet. Open Games, select a game and choose Backup Saves.</div>:
                snapshots.map(s=><div className="gm-backup-row" key={s.id}>
                  <div><strong>{s.name}</strong><small>AppID {s.appid} · {s.count} save files · {bytes(s.bytes)} · {new Date(s.created_at).toLocaleString()}</small>
                    <small>{s.backup_folder||s.library}</small>
                  </div>
                  <Action onClick={()=>beginRestore(s.id)} disabled={loading}><FaUndo/> Restore</Action>
                </div>)}
            </div>
          </div>}

          {view==="settings"&&<div>
            <div className="gm-card gm-settings-card">
              <div className="gm-setting-line">
                <div><div className="gm-card-title">GameSweep v0.8.1 test</div><div className="gm-note">Fullscreen interface · test release</div></div>
                <Action onClick={checkForUpdates} disabled={updateLoading}><FaSyncAlt/> {updateLoading?"Checking…":"Check updates"}</Action>
              </div>
              {update?.error?<div className="gm-banner error">{update.error}</div>:
                update?<div className="gm-banner">{update.available?"Update available: "+update.version:"You are on the latest available release."}</div>:null}
              {update?.available?<Action kind="primary" onClick={installUpdate} disabled={loading}><FaDownload/> Install {update.version}</Action>:null}
            </div>
            <div className="gm-card gm-settings-card">
              <div className="gm-setting-line"><div><div className="gm-card-title">Steam libraries</div><div className="gm-note">Registered Steam directories</div></div><span>{scan?.libraries.length||0} found</span></div>
              {(scan?.libraries||[]).map(p=><div key={p} className="gm-setting-path"><FaHdd/> {p}</div>)}
              {(scan?.missing_libraries||[]).map(p=><div key={p} className="gm-banner error">Library offline: {p}</div>)}
            </div>
            <div className="gm-card gm-settings-card">
              <div className="gm-setting-line"><div><div className="gm-card-title">Backup storage</div><div className="gm-note">Snapshots survive plugin updates</div></div>
                <Action onClick={()=>navigate("backups")}>Manage backups</Action></div>
              <div className="gm-setting-path">{location?.folder||"Default"}</div>
            </div>
            <div className="gm-card gm-settings-card">
              <div className="gm-setting-line">
                <div><div className="gm-card-title">Classic interface</div><div className="gm-note">Return to the previous GameSweep UI if this test layout causes issues</div></div>
                <Action onClick={()=>Navigation.Navigate("/gamesweep-classic")}>Open classic UI</Action>
              </div>
            </div>
          </div>}

        </div>
        {entry&&!dialog?<><div className="gm-scrim" onClick={()=>setEntry(null)}/>
          <aside className="gm-drawer">
            <div className="gm-drawer-body">
              <div className="gm-drawer-top"><span>Game details</span>
                <Action onClick={()=>setEntry(null)}><FaArrowLeft/> Close</Action></div>
              <h2>{entry.name}</h2>
              <div className="gm-drawer-meta"><Source value={entry.game_type}/><span aria-hidden="true">·</span><Badge entry={entry}/></div>
              <div className="gm-drawer-section"><h3>Storage breakdown</h3>
                <div className="gm-breakdown">
                  <div><strong>{bytes(entry.prefix_bytes)}</strong><small>Compatdata</small></div>
                  <div><strong>{bytes(entry.shader_bytes)}</strong><small>Shader cache</small></div>
                </div>
              </div>
              <div className="gm-drawer-section">
                <h3>Actions</h3>
                <div className="gm-drawer-buttons">
                  <Action kind="primary" onClick={()=>beginCleanup(entry)} disabled={loading}><FaBroom/> Cleanup options</Action>
                  <Action onClick={()=>beginSave(entry)} disabled={loading||!entry.prefix_path}><FaSave/> Backup saves</Action>
                  <Action onClick={()=>openSavePicker(entry)} disabled={loading||!entry.prefix_path}><FaFolderOpen/> Find save folder</Action>
                  {entry.name_source==="unknown"?<Action onClick={()=>lookupName(entry)} disabled={loading}><FaSearch/> Lookup title</Action>:null}
                </div>
                <p className="gm-note">A Proton prefix may contain unique save files. Back up recognized saves before deleting it.</p>
              </div>
              <div className="gm-drawer-section">
                <h3>Advanced details</h3>
                <div className="gm-details">
                  <div>AppID: {entry.id}</div>
                  <div>Classification: {entry.status==="installed"?"Registered in Steam":entry.status}</div>
                  <div>Evidence: {entry.type_source} · Name: {entry.name_source}</div>
                  <div>{entry.reason}</div>
                  <details><summary>Storage paths</summary><code>{entry.library}</code>
                    <code>{entry.prefix_path||"No prefix"}</code><code>{entry.shader_path||"No shader cache"}</code></details>
                </div>
              </div>
            </div>
          </aside>
        </>:null}
        {dialog?<Modal title={
          dialog.kind==="cleanupChoice"?"Clean up game data":
          dialog.kind==="cleanupConfirm"?"Confirm permanent deletion":
          dialog.kind==="backupPreview"?"Back up save files":
          dialog.kind==="notFound"?"Save files not detected":
          dialog.kind==="restoreConfirm"?"Restore save files":
          dialog.kind==="storagePicker"?"Choose backup destination":"Locate game save folder"
        } onCancel={back}>
          <ErrorBanner message={error} onDismiss={()=>setError("")}/>
          {dialog.kind==="cleanupChoice"?<>
            <p>Choose what to remove from <strong>{dialog.entry.name}</strong>. The game itself will not be uninstalled.</p>
            <div className="gm-modal-rows"><span>Compatdata: {bytes(dialog.entry.prefix_bytes)}</span><span>Shader cache: {bytes(dialog.entry.shader_bytes)}</span></div>
            {([
              ["prefix","Proton prefix / compatdata",dialog.entry.prefix_path],
              ["shader","Shader cache",dialog.entry.shader_path],
              ["all","Both prefix and shader cache",dialog.entry.prefix_path&&dialog.entry.shader_path]
            ] as Array<[CleanupKind,string,string]>).map(([kind,label,present])=><div className="gm-modal-option" key={kind}>
              <input type="radio" name="cleanup-kind" checked={choice===kind} disabled={!present} onChange={()=>setChoice(kind)}/>
              <label onClick={()=>{if(present)setChoice(kind);}}>{label}</label>
            </div>)}
            <div className="gm-modal-warning">Deleting compatdata may erase local saves and settings. Close the game first.</div>
            <div className="gm-modal-actions">
              <Action kind="primary" disabled={busy} onClick={()=>prepareDelete(dialog.entry,choice)}>Review selected cleanup</Action>
            </div>
          </>:null}
          {dialog.kind==="cleanupConfirm"?<>
            <p>Double-check the selection. This operation cannot be undone and does not uninstall the game.</p>
            <div className="gm-modal-rows"><strong>{dialog.preview.name}</strong>
              <span>AppID: {dialog.preview.appid} · {dialog.preview.game_type}</span>
              <span>Selected: {dialog.preview.kind==="all"?"Prefix + shader cache":dialog.preview.kind}</span>
              <span>Estimated size: {bytes(dialog.preview.bytes||0)}</span>
              {dialog.preview.targets?.map(t=><small key={t.kind}>{t.path}</small>)}
              {dialog.preview.path?<small>{dialog.preview.path}</small>:null}
            </div>
            <div className="gm-modal-warning">Permanent removal. Save files inside compatdata can be lost. Combined cleanup can be partially completed if disk I/O fails.</div>
            <ConfirmCheck value={ack} onChange={setAck}>I understand that deleted files cannot be recovered.</ConfirmCheck>
            {dialog.preview.status==="installed"?<ConfirmCheck value={installedAck} onChange={setInstalledAck}>This game is still registered in Steam and its local saves may be deleted.</ConfirmCheck>:null}
            <div className="gm-modal-actions">
              {(dialog.preview.kind==="prefix"||dialog.preview.kind==="all")?
                <Action onClick={()=>beginSave(dialog.entry)} disabled={busy}><FaSave/> Back up saves first</Action>:null}
              <Action kind="danger" disabled={busy||!ack||(dialog.preview.status==="installed"&&!installedAck)} onClick={()=>confirmDelete(dialog.preview)}>
                {busy?"Removing…":"Delete selected data permanently"}
              </Action>
            </div>
          </>:null}
          {dialog.kind==="notFound"?<>
            <p>{dialog.message}</p><div className="gm-modal-info">
              GameSweep does not assume that missing matches mean missing save files. No backup was created or cleanup performed.
            </div>
            <div className="gm-modal-actions">
              <Action kind="primary" onClick={()=>openSavePicker(dialog.entry)} disabled={busy}>Find save folder manually</Action>
            </div>
          </>:null}
          {dialog.kind==="backupPreview"?<>
            <p>Only recognized save files will be copied, not the full Proton prefix.</p>
            <div className="gm-modal-rows">
              <strong>{dialog.entry.name}</strong>
              <span>{dialog.preview.count} file(s) · {bytes(dialog.preview.bytes||0)}</span>
              <span>Detected via: {dialog.preview.method}</span>
              <span>Destination: {location?.folder||"Default backup location"}</span>
              {(dialog.preview.sample||[]).map((p,i)=><small key={i}>{p}</small>)}
            </div>
            <div className="gm-modal-info">Close the game first. Files stored outside recognized save directories might not be included.</div>
            <div className="gm-modal-actions">
              <Action onClick={()=>openLocationPicker()} disabled={busy}>Change destination</Action>
              <Action onClick={()=>openSavePicker(dialog.entry)} disabled={busy}>Choose save folder</Action>
              <Action kind="primary" onClick={()=>doBackup(dialog.entry)} disabled={busy}>Create save backup</Action>
            </div>
          </>:null}
          {dialog.kind==="restoreConfirm"?<>
            <p>This will write backed-up save files to their original locations.</p>
            <div className="gm-modal-rows">
              <strong>{dialog.preview.name}</strong><span>{dialog.preview.count} file(s) · {bytes(dialog.preview.bytes||0)}</span>
              <span>{dialog.preview.conflicts||0} files already exist and will be overwritten</span>
            </div>
            <div className="gm-modal-warning">Restore can replace newer progress. The archive is hash-checked before writing, but interrupted restores may be partial.</div>
            <ConfirmCheck value={ack} onChange={setAck}>I understand that existing save files may be overwritten.</ConfirmCheck>
            <div className="gm-modal-actions"><Action kind="primary" onClick={()=>doRestore(dialog.preview)} disabled={busy||!ack}>Restore these saves</Action></div>
          </>:null}
          {dialog.kind==="storagePicker"?<>
            <p>Choose a storage folder. GameSweep creates a save-backups subfolder inside it.</p>
            <div className="gm-modal-rows"><span>{dialog.browser.path||"Storage locations"}</span>
              <small>{dialog.browser.free?bytes(dialog.browser.free)+" available":""}</small></div>
            <div className="gm-folder-list">
              {(dialog.browser.folders||[]).map(folder=><Action key={folder.path} onClick={()=>openLocationPicker(folder.path)} disabled={busy}>
                <FaFolderOpen/> {folder.name}
              </Action>)}
            </div>
            <div className="gm-modal-actions">
              <Action onClick={()=>openLocationPicker(dialog.browser.parent||"")} disabled={busy}><FaArrowUp/> Parent folder</Action>
              <Action kind="primary" onClick={()=>chooseStorage(dialog.browser.path||"")} disabled={busy||!dialog.browser.selectable}>Use selected folder</Action>
            </div>
          </>:null}
          {dialog.kind==="savePicker"?<>
            <p>Select a specific save folder within the game's Proton C: drive. Entire system directories cannot be selected.</p>
            <div className="gm-modal-rows"><span>C:/{dialog.browser.relative||""}</span>
              <small>{dialog.browser.count||0} files · {bytes(dialog.browser.bytes||0)}</small></div>
            <div className="gm-folder-list">
              {(dialog.browser.folders||[]).map(folder=><Action key={folder.relative} onClick={()=>openSavePicker(dialog.entry,folder.relative)} disabled={busy}>
                <FaFolderOpen/> {folder.name}
              </Action>)}
            </div>
            <div className="gm-modal-info">A manually selected directory backs up every regular file within that folder, possibly including configuration files.</div>
            <div className="gm-modal-actions">
              <Action onClick={()=>openSavePicker(dialog.entry,dialog.browser.parent||"")} disabled={busy}><FaArrowUp/> Parent folder</Action>
              <Action kind="primary" disabled={busy||!dialog.browser.selectable||!dialog.browser.relative} onClick={()=>chooseSaveDirectory(dialog.entry,dialog.browser.relative||"")}>Use this save folder</Action>
              <Action onClick={()=>resetSaveDirectory(dialog.entry)} disabled={busy}>Reset automatic detection</Action>
            </div>
          </>:null}
        </Modal>:null}
      </main>
    </div>
  </Focusable>;
}
