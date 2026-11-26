export const modernStyle = String.raw`
.gm-shell{--gm-bg:#091321;--gm-rail:#0d1a2b;--gm-card:#122135;--gm-text:#eaf1fa;--gm-muted:#8fa4bb;--gm-line:#263a51;--gm-accent:#51ddca;--gm-danger:#f08a91;position:fixed;inset:48px 0 0 0;z-index:8000;display:flex;min-height:0;background:var(--gm-bg);color:var(--gm-text);font-family:Inter,"Segoe UI",sans-serif;font-size:14px;isolation:isolate}
.gm-shell *{box-sizing:border-box}.gm-shell button,.gm-shell input,.gm-shell select{font-family:inherit}
.gm-shell .DialogButton{background:transparent;border:1px solid transparent;box-shadow:none;color:inherit;min-height:43px;border-radius:9px;text-align:left;padding:8px 12px;font-weight:650;transition:background .12s,border-color .12s}
.gm-shell .DialogButton:hover{background:rgba(98,157,183,.15);color:#f0ffff}
.gm-shell .DialogButton:focus,.gm-shell .DialogButton:focus-visible{outline:2px solid #60e5d6!important;outline-offset:1px!important;background:rgba(57,176,172,.18)!important}
.gm-shell .DialogButton:disabled{opacity:.38!important}
.gm-rail{width:218px;flex:0 0 218px;background:linear-gradient(180deg,#0e1b2d,#0a1728);border-right:1px solid var(--gm-line);display:flex;flex-direction:column;padding:21px 12px 15px;min-height:0;overflow-y:auto}
.gm-brand{display:flex;gap:11px;align-items:center;padding:2px 8px 28px}
.gm-logo{height:41px;width:41px;display:flex;align-items:center;justify-content:center;background:linear-gradient(140deg,#64eadb,#21aead);border-radius:11px;color:#042a31;box-shadow:0 0 0 4px rgba(73,224,208,.06);font-size:20px}
.gm-brand strong{font-size:20px;letter-spacing:-.6px}.gm-brand small{display:block;color:#889db4;letter-spacing:1.05px;font-size:10px;text-transform:uppercase;font-weight:700}
.gm-rail-label{font-size:10px;letter-spacing:1.6px;color:#7289a2;font-weight:800;margin:0 9px 8px;text-transform:uppercase}
.gm-nav{display:grid;gap:4px}.gm-nav-item{position:relative}.gm-nav-item .DialogButton{width:100%;display:flex;align-items:center;gap:11px;color:#a6b8cb;min-height:47px}
.gm-nav-item.active .DialogButton{background:linear-gradient(90deg,rgba(63,195,188,.18),rgba(37,114,126,.06))!important;color:#e4fffd!important;border-color:rgba(64,198,187,.30)!important;box-shadow:inset 3px 0 0 #51ddca}
.gm-nav-item.active svg{color:#51ddca}
.gm-nav-item svg{font-size:17px;flex-shrink:0}.gm-nav-item span{flex:1}.gm-nav-count{background:#26384b;border-radius:6px;padding:3px 6px;color:#d6e0ea;font-size:10px}
.gm-rail-footer{margin-top:auto;border-top:1px solid var(--gm-line);padding:15px 9px 0;color:#869bb1;font-size:11px;line-height:1.7}
.gm-rail-footer i{display:inline-block;width:8px;height:8px;background:#54d9c5;border-radius:50%;margin-right:7px;box-shadow:0 0 0 4px rgba(77,214,199,.13)}
.gm-main{position:relative;flex:1;overflow-y:auto;min-width:0;scrollbar-width:thin;scrollbar-color:#374c60 transparent}
.gm-inner{max-width:1450px;margin:0 auto;padding:28px 32px 70px}
.gm-header{display:flex;align-items:flex-start;justify-content:space-between;gap:16px;margin-bottom:25px}
.gm-eyebrow{text-transform:uppercase;color:#57ddcc;font-weight:800;letter-spacing:1.65px;font-size:10px;margin:0 0 6px}
.gm-header h1{font-size:29px;font-weight:800;letter-spacing:-.8px;line-height:1.1;margin:0}
.gm-lede{font-size:13px;color:#a2b3c7;margin:10px 0 0}
.gm-header-actions{display:flex;align-items:center;gap:10px;flex-wrap:wrap;justify-content:flex-end}
.gm-smallnote{color:#809ab4;font-size:11px}
.gm-primary .DialogButton{background:#50d7c7!important;color:#05252b!important;border-color:#64e5d7!important;min-height:42px;padding:10px 17px}
.gm-primary .DialogButton:hover,.gm-primary .DialogButton:focus{background:#73eee1!important;color:#062b31!important}
.gm-secondary .DialogButton{background:#1a2e43;border-color:#314a60;min-height:39px;padding:9px 13px;font-size:12px}
.gm-danger .DialogButton{background:#aa4755!important;color:#fff!important;border-color:#bd5d67!important;text-align:center;min-height:43px}
.gm-danger .DialogButton:hover{background:#c65c68!important}
.gm-danger .DialogButton:disabled{opacity:.38!important}
.gm-card{background:linear-gradient(140deg,#122237,#101e30);border:1px solid var(--gm-line);border-radius:15px;min-width:0}
.gm-card-title{font-weight:760;font-size:15px;letter-spacing:-.2px}.gm-note{color:#92a9bd;font-size:11px;margin-top:5px}
.gm-overview-top{display:grid;grid-template-columns:minmax(300px,1fr) minmax(365px,1.22fr);gap:16px}
.gm-storage{min-height:324px;padding:21px 24px;display:flex;flex-direction:column;justify-content:space-between}
.gm-storage-head{display:flex;justify-content:space-between;align-items:center;gap:8px}.gm-select{background:#1b3145;border:1px solid #36516a;color:#dceaf5;padding:9px 11px;border-radius:8px;max-width:230px;font-size:12px}
.gm-donut-line{display:flex;align-items:center;gap:25px;margin-top:11px}.gm-donut{--fill:65;position:relative;border-radius:50%;height:170px;width:170px;flex:0 0 170px;background:conic-gradient(from -90deg,#4dd9ca 0%,#458cce calc(var(--fill)*1%),#263c53 calc(var(--fill)*1%),#263c53 100%);display:grid;place-items:center}
.gm-donut:before{content:"";position:absolute;inset:18px;background:#13263b;border-radius:50%}.gm-donut-label{position:relative;text-align:center}.gm-donut-label strong{display:block;font-size:27px;letter-spacing:-.8px}.gm-donut-label small{color:#90a6bb;font-size:11px}
.gm-storage-values{display:grid;gap:20px}.gm-storage-values strong{font-size:23px;font-weight:780}.gm-storage-values small{display:block;color:#90a5ba;font-size:11px}.gm-accent-text{color:#55ddce}
.gm-legend{display:flex;justify-content:space-between;gap:8px;color:#879cb2;font-size:11px}.gm-legend i{display:inline-block;width:8px;height:8px;border-radius:2px;margin-right:5px}
.gm-metrics{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:15px}
.gm-metric{padding:21px;min-height:154px;display:flex;flex-direction:column;justify-content:space-between}
.gm-metric-head{display:flex;align-items:center;justify-content:space-between;gap:8px;color:#9daec1;font-size:12px}
.gm-metric-head svg{font-size:17px;color:#6fa9b8}
.gm-metric strong{font-size:30px;font-weight:790;letter-spacing:-1.1px;line-height:1.1}.gm-metric small{font-size:11px;color:#8299b1}
.gm-review-banner{margin:16px 0 28px;display:flex;align-items:center;gap:15px;padding:14px 17px;background:#0e292e;border:1px solid #1b4849;border-radius:11px;color:#b0dbd8}
.gm-review-banner svg{color:#53d7c8;font-size:19px}.gm-review-banner strong{font-size:12px;color:#dae8ea}.gm-review-banner small{display:block;color:#8ab5b2;font-size:11px;margin-top:4px}.gm-review-banner .gm-secondary{margin-left:auto}
.gm-section-head{display:flex;align-items:center;justify-content:space-between;gap:12px;margin:30px 0 13px}.gm-section-head h2{font-size:17px;font-weight:750;margin:0}.gm-section-head small{font-size:11px;color:#91a6ba}
.gm-game-table{overflow:hidden}.gm-table-head,.gm-game-row{display:grid;grid-template-columns:minmax(230px,1.7fr) 120px 145px 115px 22px;align-items:center;gap:9px;padding:0 18px}
.gm-table-head{height:42px;color:#748ba4;font-size:10px;font-weight:750;letter-spacing:1px;text-transform:uppercase;border-bottom:1px solid var(--gm-line)}
.gm-game-row{width:100%;min-height:72px;background:transparent;border:0;border-bottom:1px solid #203349;color:inherit;text-align:left;cursor:pointer}
.gm-game-row:hover{background:#172d41}.gm-game-row:focus,.gm-game-row:focus-visible{outline:2px solid #5cddce!important;outline-offset:-3px!important;background:#1a3844}
.gm-game-row:last-child{border-bottom:0}.gm-game-cell{display:flex;align-items:center;gap:11px;min-width:0}
.gm-game-art{width:54px;height:48px;flex:0 0 54px;display:grid;place-items:center;border-radius:9px;background:linear-gradient(135deg,var(--art1,#316079),var(--art2,#152b40));font-weight:800;font-size:18px;color:#fff;text-shadow:0 1px 6px #000a}
.gm-game-name{font-weight:720;font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.gm-game-sub{display:flex;align-items:center;gap:7px;font-size:11px;color:#8ba2b8;margin-top:5px;min-width:0}
.gm-source{font-size:10px;border:1px solid #2e5862;border-radius:6px;background:#143440;color:#72d7d0;padding:3px 7px;font-weight:760;white-space:nowrap}.gm-source.non{background:#183b34;border-color:#326758;color:#8adcb7}.gm-source.unknown{background:#263342;border-color:#465368;color:#bdc7d6}
.gm-status{display:inline-flex;align-items:center;padding:4px 8px;background:#173b35;border:1px solid #2e6556;color:#89dfb6;font-size:10px;font-weight:750;border-radius:7px;white-space:nowrap}
.gm-status.review{background:#3a2836;color:#f2b1ad;border-color:#69424a}.gm-status.candidate{background:#3e3125;color:#e5c68f;border-color:#6e563e}
.gm-table-id{font-size:11px;color:#8599ae}.gm-table-size{text-align:right;font-size:13px;font-weight:750}.gm-game-chevron{color:#829ab2;text-align:right}
.gm-filters{display:flex;gap:10px;flex-wrap:wrap;margin:14px 0}
.gm-search{background:#15283c;border:1px solid #344b63;color:#eff9ff;border-radius:9px;padding:11px 12px;min-width:230px;flex:1;font-size:13px}.gm-search:focus{outline:2px solid #63decc}
.gm-filter-select{background:#172a3e;color:#d1e5f0;border:1px solid #344b63;padding:10px 12px;border-radius:9px;font-size:12px}
.gm-empty{border:1px dashed #3b4e62;border-radius:12px;background:#102038;color:#92adc3;font-size:13px;padding:30px 20px;text-align:center}
.gm-banner{padding:12px 15px;border-radius:10px;margin-bottom:16px;border:1px solid #315f56;background:#14342f;color:#a6e5ce;font-size:12px;overflow-wrap:anywhere}
.gm-banner.error{border-color:#7a4b52;background:#38252e;color:#ffbec1}
.gm-backup-row{display:flex;align-items:center;justify-content:space-between;gap:15px;padding:16px 20px;border-bottom:1px solid var(--gm-line)}
.gm-backup-row:last-child{border:0}.gm-backup-row strong{font-size:14px}.gm-backup-row small{display:block;color:#869fb6;font-size:11px;margin-top:5px;overflow-wrap:anywhere}.gm-backup-row .gm-secondary{flex-shrink:0}
.gm-settings-card{padding:21px;display:grid;gap:13px;margin-bottom:16px}.gm-setting-line{display:flex;justify-content:space-between;align-items:center;gap:14px}.gm-setting-path{font-size:12px;color:#a1b6c9;word-break:break-all;max-width:750px}.gm-setting-line .gm-secondary{flex-shrink:0}
.gm-scrim{position:fixed;inset:48px 0 0 0;z-index:30;background:rgba(1,7,15,.68)}
.gm-drawer{position:fixed;inset:48px 0 0 auto;width:min(438px,100%);z-index:31;overflow-y:auto;background:#0e1b2d;border-left:1px solid #36506a;box-shadow:-25px 0 65px #0007}
.gm-drawer-body{padding:21px 23px}.gm-drawer-top{display:flex;align-items:center;justify-content:space-between;gap:10px}
.gm-drawer-hero{height:124px;display:flex;align-items:center;justify-content:center;background:linear-gradient(130deg,#1e5b66,#26374c 58%,#112139);border:1px solid #2b4356;border-radius:12px;margin:16px 0}
.gm-drawer-hero strong{font-size:55px;opacity:.22}.gm-drawer h2{font-size:23px;font-weight:820;letter-spacing:-.5px;margin:0 0 11px;line-height:1.12}
.gm-drawer-section{border-top:1px solid #283b50;padding:17px 0}.gm-drawer-section h3{font-size:11px;color:#92a9c1;letter-spacing:1.2px;text-transform:uppercase;margin:0 0 13px}
.gm-breakdown{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:9px}.gm-breakdown>div{background:#14293e;border:1px solid #2b4056;padding:14px;border-radius:10px}.gm-breakdown strong{display:block;font-size:20px}.gm-breakdown small{color:#95adc0;font-size:11px}
.gm-drawer-buttons{display:grid;grid-template-columns:1fr 1fr;gap:9px;margin:17px 0}.gm-drawer-buttons>div:first-child{grid-column:1/-1}.gm-drawer-buttons .DialogButton{width:100%;text-align:center!important}
.gm-details{font-size:11px;color:#9bb3c9;line-height:1.8;overflow-wrap:anywhere}.gm-details summary{padding:7px 0;cursor:pointer}.gm-details code{white-space:pre-wrap;font-size:11px}
.gm-modal-backdrop{position:fixed;inset:48px 0 0;z-index:60;display:flex;align-items:center;justify-content:center;background:#010911d9;backdrop-filter:blur(7px);padding:16px}
.gm-modal{width:min(555px,96vw);max-height:88vh;overflow-y:auto;padding:23px;border:1px solid #42576b;border-radius:16px;background:linear-gradient(155deg,#15263a,#101e30);box-shadow:0 25px 90px #000a}
.gm-modal h2{font-size:22px;margin:0 0 8px;font-weight:790}.gm-modal p{font-size:12px;line-height:1.55;color:#acbece;margin:7px 0 15px}
.gm-modal .DialogButton{min-height:42px}.gm-modal-option{border:1px solid #3b536a;background:#192d43;border-radius:10px;padding:11px;margin:8px 0;display:flex;align-items:center;gap:10px}
.gm-modal-option input{accent-color:#51ddca;width:19px;height:19px}.gm-modal-option label{flex:1;font-size:13px}
.gm-modal-warning{background:#35282f;border:1px solid #69444d;color:#f1c1b9;padding:12px;border-radius:10px;font-size:12px;line-height:1.55;margin:13px 0}
.gm-modal-info{border:1px solid #2c5560;background:#15323a;color:#a2e7db;padding:12px;border-radius:9px;font-size:12px;margin:11px 0}
.gm-modal-rows{display:grid;gap:6px;background:#0e1c2e;border:1px solid #2b4058;border-radius:10px;padding:13px;margin:13px 0;color:#c2d3e3;font-size:12px;overflow-wrap:anywhere}
.gm-modal-actions{display:flex;flex-direction:column;gap:9px;margin-top:14px}.gm-modal-actions>div>.DialogButton{width:100%;text-align:center}
.gm-folder-list{max-height:31vh;overflow-y:auto;display:grid;gap:5px;padding:6px 0;margin:12px 0;border-top:1px solid #294459;border-bottom:1px solid #294459}
.gm-folder-list .DialogButton{width:100%;text-align:left}
.gm-check{display:flex;align-items:center;gap:10px;font-size:12px;margin:12px 0;color:#cbd9e6}.gm-check input{accent-color:#53d8ca;height:18px;width:18px}
.gm-spinner{opacity:.68}
@media(max-width:1120px){.gm-rail{width:185px;flex-basis:185px}.gm-inner{padding:21px}.gm-donut{height:143px;width:143px;flex-basis:143px}.gm-overview-top{grid-template-columns:minmax(255px,1fr) minmax(315px,1.15fr)}}
@media(max-width:875px){.gm-rail{width:80px;flex-basis:80px}.gm-rail-label,.gm-brand strong,.gm-brand small,.gm-nav-item span,.gm-nav-count,.gm-rail-footer{display:none}.gm-brand{padding-left:6px}.gm-nav-item .DialogButton{justify-content:center}.gm-overview-top{grid-template-columns:1fr}.gm-game-row,.gm-table-head{grid-template-columns:minmax(180px,1fr) 110px 95px 18px}.gm-table-id{display:none}}
@media(max-width:600px){.gm-rail{width:64px;flex-basis:64px}.gm-inner{padding:15px}.gm-header{flex-direction:column}.gm-metrics{gap:9px}.gm-metric{padding:15px;min-height:120px}.gm-metric strong{font-size:24px}.gm-game-row,.gm-table-head{grid-template-columns:minmax(130px,1fr) 90px 18px}.gm-game-row .gm-table-size{font-size:12px}.gm-game-row .gm-status,.gm-table-head .gm-col-status{display:none}.gm-donut-line{gap:13px}.gm-donut{height:128px;width:128px;flex-basis:128px}.gm-storage-values strong{font-size:18px}}

.gm-game-row-wrap{border-bottom:1px solid #203449}.gm-game-row-wrap:last-child{border-bottom:0}
.gm-game-row-wrap>.DialogButton{padding:0!important;display:block!important;width:100%!important;height:auto!important;background:transparent!important;border:0!important;border-radius:0!important;min-height:69px!important;text-align:left!important;color:#ebf2f9!important}
.gm-game-row-wrap>.DialogButton:hover{background:#172d42!important}
.gm-game-row-wrap>.DialogButton:focus{background:#1a3744!important;outline:2px solid #56d9ca!important;outline-offset:-2px!important}
.gm-game-row-content{display:grid;grid-template-columns:minmax(230px,1.7fr) 120px 145px 115px 22px;align-items:center;gap:9px;padding:11px 18px}
.gm-nav .DialogButton{width:100%}
.gm-shell .gm-drawer-buttons .gm-secondary .DialogButton{height:100%}
.gm-shell .gm-modal-actions .gm-secondary>.DialogButton{width:100%;text-align:center!important}
.gm-game-row-content>.gm-status{justify-self:start}
@media(max-width:875px){.gm-game-row-content{grid-template-columns:minmax(180px,1fr) 110px 95px 18px}.gm-game-row-content>.gm-table-id{display:none}}
@media(max-width:600px){.gm-game-row-content{grid-template-columns:minmax(130px,1fr) 90px 18px}.gm-game-row-content>span:nth-child(3){display:none}.gm-game-row-content .gm-table-size{font-size:12px}}
@media(prefers-reduced-motion:reduce){.gm-shell *{transition:none!important;animation:none!important}}
`;
