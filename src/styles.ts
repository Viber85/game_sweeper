export const style = `
.gs-screen,.gs-screen *{box-sizing:border-box}
.gs-screen{width:100%;height:100%;min-height:0;display:flex;overflow:hidden;color:#f2f7ff;font-family:Arial,sans-serif;background:radial-gradient(ellipse 65% 45% at 97% -12%,rgba(12,145,161,.22),transparent 75%),linear-gradient(135deg,#0b1422 0%,#101d2c 60%,#0a1622 100%)}
.gs-sidebar{width:204px;flex:0 0 204px;display:flex;flex-direction:column;padding:28px 12px 18px;border-right:1px solid rgba(174,207,242,.08);background:linear-gradient(180deg,rgba(14,27,49,.86),rgba(14,24,45,.52))}
.gs-brand{display:flex;align-items:center;gap:11px;padding:3px 10px 32px;font-weight:750;font-size:21px;letter-spacing:-.6px;white-space:nowrap}
.gs-brand-icon{color:#4de7db;flex-shrink:0}
.gs-subbrand{color:#88a4bb;font-size:10px;letter-spacing:1.4px;font-weight:700;text-transform:uppercase;padding:0 13px;margin-bottom:8px}
.gs-nav{display:flex;flex-direction:column;gap:6px}
.gs-nav-wrap{border-radius:10px;overflow:hidden}
.gs-nav-wrap.gs-active{background:linear-gradient(95deg,rgba(24,125,213,.35),rgba(29,110,202,.09));box-shadow:inset 2px 0 0 #40c8f8}
.gs-screen .gs-nav .DialogButton{background:transparent!important;box-shadow:none!important;border:0!important;text-align:left!important;padding:12px!important;min-height:42px!important;font-weight:600!important;color:#a7b6ca!important;width:100%!important}
.gs-screen .gs-nav .gs-active .DialogButton{color:#fff!important}
.gs-screen .DialogButton:focus{outline:2px solid #59d5ff!important;outline-offset:-2px!important}
.gs-nav-label{display:flex;align-items:center;gap:12px;font-size:13px}
.gs-sidebar-bottom{margin-top:auto;padding:10px;font-size:11px;color:#92a7ba;border-top:1px solid rgba(255,255,255,.08)}
.gs-main{min-width:0;flex:1;height:100%;overflow-y:auto;overscroll-behavior:contain;padding:25px 28px 27px}
.gs-heading{display:flex;justify-content:space-between;align-items:center;gap:15px;margin-bottom:17px}
.gs-title{font-size:27px;font-weight:750;letter-spacing:-.9px;line-height:1.13;margin:0}
.gs-subtitle{font-size:12px;color:#91acc3;margin-top:6px}
.gs-right-tag{border:1px solid rgba(107,164,197,.24);color:#91b5cc;border-radius:25px;padding:8px 12px;font-size:11px;white-space:nowrap}
.gs-overview{display:grid;grid-template-columns:minmax(245px,.88fr) minmax(420px,1.32fr);gap:19px;align-items:stretch;margin-bottom:19px}
.gs-card{border:1px solid rgba(153,204,255,.13);border-radius:15px;background:linear-gradient(115deg,rgba(28,48,69,.84),rgba(18,36,54,.82));box-shadow:0 12px 35px rgba(0,0,0,.08)}
.gs-meter-card{padding:14px;display:flex;flex-direction:column;justify-content:center;align-items:center;min-height:275px}
.gs-meter{width:min(24vw,235px);height:min(24vw,235px);min-width:192px;min-height:192px;border-radius:50%;display:grid;place-items:center;position:relative;box-shadow:0 0 0 1px rgba(54,139,202,.08)}
.gs-meter:after{content:"";position:absolute;inset:16px;border-radius:50%;background:radial-gradient(circle at 55% 30%,#14273a,#0d1a2a);box-shadow:inset 0 0 35px rgba(0,0,0,.35)}
.gs-meter-text{position:relative;z-index:1;text-align:center;display:flex;flex-direction:column;align-items:center}
.gs-meter-icon{color:#b7cee5;font-size:24px;margin-bottom:9px}
.gs-meter-big{font-size:31px;font-weight:800;line-height:1;letter-spacing:-.8px}
.gs-meter-label{font-size:12px;color:#a9bbcc;margin-top:6px}
.gs-meter-rule{width:135px;height:1px;background:rgba(255,255,255,.14);margin:13px 0 10px}
.gs-meter-small{display:flex;gap:12px;font-size:11px;color:#adbed0}
.gs-meter-small strong{color:#59e8d2}
.gs-meter-foot{margin-top:12px;font-size:11px;color:#90a8c0;text-align:center}
.gs-metrics{display:grid;grid-template-columns:1fr 1fr;grid-template-rows:1fr 1fr 1fr;gap:10px}
.gs-metric{padding:16px;min-height:76px;display:flex;gap:12px;align-items:center}
.gs-metric-icon{flex-shrink:0;font-size:22px;color:#86b0fb}
.gs-metric-title{font-size:12px;color:#a2b5c9}
.gs-metric-value{font-size:22px;line-height:1.2;font-weight:750;letter-spacing:-.45px;margin-top:5px}
.gs-metric-note{font-size:10px;color:#89a0b6;margin-top:3px}
.gs-metric-accent .gs-metric-value{color:#52e2cf}
.gs-wide{grid-column:1/-1}
.gs-section{padding:14px 16px 17px}
.gs-section-heading{display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap;padding:0 3px 11px;border-bottom:1px solid rgba(255,255,255,.11)}
.gs-section-title{font-size:17px;font-weight:750;letter-spacing:-.25px}
.gs-section-detail{color:#93aac0;font-size:12px}
.gs-filters{display:flex;gap:5px;flex-wrap:wrap;padding:12px 0 8px}
.gs-filter{min-width:84px}
.gs-screen .gs-filter .DialogButton{background:rgba(18,33,50,.86)!important;color:#b2c4d5!important;font-size:11px!important;border-radius:7px!important;padding:6px 13px!important}
.gs-screen .gs-filter.gs-selected .DialogButton{color:#59e5dc!important;background:rgba(22,112,130,.28)!important}
.gs-list-heading,.gs-list-row{display:grid;grid-template-columns:minmax(0,2fr) 114px 122px 100px;align-items:center;gap:12px}
.gs-list-heading{color:#7e99ad;font-size:11px;padding:8px 12px 9px}
.gs-list-row-wrap{border-top:1px solid rgba(255,255,255,.085)}
.gs-screen .gs-list-row-wrap .DialogButton{background:transparent!important;box-shadow:none!important;border:0!important;text-align:left!important;width:100%!important;padding:0!important;min-height:0!important}
.gs-screen .gs-list-row-wrap .DialogButton:focus{outline:2px solid #5dcffe!important;outline-offset:-2px!important}
.gs-screen .gs-list-row-wrap .DialogButton:hover{background:rgba(45,105,155,.15)!important}
.gs-list-row{width:100%;padding:8px 12px;text-align:left;background:transparent;border:0;cursor:pointer;font:inherit;color:#f1f7ff;min-height:53px;border-radius:7px}
.gs-list-row:hover,.gs-list-row:focus{background:rgba(55,121,175,.18);outline:2px solid #57d4ff;outline-offset:-2px}
.gs-game-name{display:flex;align-items:center;gap:10px;min-width:0}
.gs-game-initial{flex-shrink:0;width:41px;height:37px;display:flex;align-items:center;justify-content:center;border-radius:6px;font-size:13px;font-weight:750;color:#c7eff3;background:linear-gradient(125deg,#145a75,#22405c)}
.gs-game-title{font-size:12px;font-weight:650;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.gs-game-hint{font-size:10px;color:#8aa3b8;margin-top:4px}
.gs-col-text{font-size:11px;color:#aec0d1;overflow:hidden;text-overflow:ellipsis}
.gs-col-size{text-align:right;font-size:12px;font-weight:750}
.gs-status{display:inline-block;border-radius:15px;font-size:10px;font-weight:650;padding:4px 7px;white-space:nowrap}
.gs-status.installed{color:#66dcac;background:rgba(35,165,108,.14);border:1px solid rgba(48,201,137,.35)}
.gs-status.candidate{color:#67c7ff;background:rgba(47,131,212,.14);border:1px solid rgba(83,159,241,.3)}
.gs-status.review{color:#f1c17f;background:rgba(209,149,52,.13);border:1px solid rgba(215,152,65,.34)}
.gs-details{padding:11px 15px 14px;margin:2px 12px 10px;border-radius:9px;background:rgba(2,10,20,.36);font-size:11px;color:#aec2d6;overflow-wrap:anywhere;line-height:1.7}
.gs-screen .DialogButton{border-radius:8px!important}
.gs-action{display:flex;gap:10px;margin-top:13px;flex-wrap:wrap}
.gs-action .DialogButton{background:rgba(38,65,91,.72)!important;min-width:130px!important}
.gs-action-primary .DialogButton{background:linear-gradient(120deg,#1bcab5,#30bbc7)!important;color:#041b25!important;font-weight:750!important}
.gs-note{font-size:12px;color:#c2aac0;padding:10px 14px;border:1px solid rgba(243,198,107,.3);border-radius:10px;background:rgba(103,78,26,.13);margin-bottom:14px}
.gs-empty{padding:20px;text-align:center;color:#90aabe;font-size:13px}
.gs-library-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(270px,1fr));gap:12px}
.gs-library{padding:18px}
.gs-library-name{font-size:12px;color:#afc0d0;overflow-wrap:anywhere}
.gs-library-free{font-size:26px;font-weight:750;margin:12px 0 8px}
.gs-progress{height:7px;border-radius:10px;background:rgba(255,255,255,.12);overflow:hidden;margin:14px 0}
.gs-progress-fill{height:100%;background:linear-gradient(90deg,#4977ee,#4fe4d7)}
.gs-muted{color:#90a9bc;font-size:12px;line-height:1.6}
.gs-settings{max-width:780px;padding:24px}
.gs-settings-row{padding:12px 0;display:flex;justify-content:space-between;gap:18px;align-items:center;border-top:1px solid rgba(255,255,255,.1)}
.gs-alert{color:#f6cb83;font-size:11px;margin:10px 0;white-space:pre-wrap;overflow-wrap:anywhere}
.gs-loading{padding:30px;text-align:center;color:#abc4d7}
@media(max-width:1120px){.gs-sidebar{width:170px;flex-basis:170px}.gs-brand{font-size:18px}.gs-main{padding:19px}.gs-overview{grid-template-columns:minmax(215px,.9fr) minmax(0,1.2fr)}.gs-metric{padding:11px}.gs-metric-value{font-size:18px}.gs-meter{width:190px;height:190px}.gs-meter-card{min-height:258px}}
@media(max-width:850px){.gs-sidebar{width:142px;flex-basis:142px;padding:18px 7px}.gs-nav-label{gap:6px;font-size:11px}.gs-brand{font-size:15px;padding:3px 5px 20px}.gs-main{padding:16px}.gs-overview{grid-template-columns:1fr}.gs-meter-card{min-height:240px}.gs-metrics{grid-template-rows:auto}.gs-list-heading,.gs-list-row{grid-template-columns:minmax(0,2fr) 82px 100px 69px;gap:5px}.gs-col-text{font-size:10px}}

.gs-delete-row{margin-top:12px;gap:8px}
.gs-screen .gs-delete-row .DialogButton{background:rgba(150,55,58,.24)!important;border:1px solid rgba(236,105,106,.38)!important;color:#ffc7bd!important;padding:8px 13px!important}
.gs-cleanup-success{font-size:12px;margin:10px 0 15px;padding:12px 15px;border:1px solid rgba(87,209,169,.36);border-radius:10px;color:#8ef2bf;background:rgba(33,105,87,.16)}
.gs-modal-layer{position:fixed;inset:0;z-index:9999;background:rgba(3,8,17,.83);backdrop-filter:blur(9px);display:flex;justify-content:center;align-items:center;padding:25px}
.gs-modal{background:linear-gradient(140deg,#1b2d3d,#0d1c2e);border:1px solid rgba(240,144,130,.26);box-shadow:0 28px 90px rgba(0,0,0,.52);border-radius:18px;width:min(625px,100%);max-height:94vh;overflow-y:auto;padding:25px 30px;color:#eef6ff}
.gs-modal-symbol{font-size:22px;color:#ffc06d;margin-bottom:8px}
.gs-modal h2{font-size:23px;line-height:1.2;letter-spacing:-.5px;margin:0 0 6px}
.gs-modal-subtitle{font-size:13px;color:#fbbaa9;margin:0 0 17px}
.gs-modal-details{display:flex;flex-direction:column;gap:6px;padding:15px;border:1px solid rgba(206,225,255,.12);border-radius:10px;background:rgba(9,16,28,.72);color:#acc2d5;font-size:12px}
.gs-modal-details strong{font-size:17px;color:#f3f8ff}
.gs-modal-warning{margin:14px 0;color:#f6c49d;font-size:13px;line-height:1.55}
.gs-modal-action{display:flex;flex-direction:column;gap:8px}
.gs-modal-action>.DialogButton,.gs-modal-action>div>.DialogButton{width:100%!important;text-align:center!important;padding:11px!important}
.gs-modal-action>.DialogButton{background:rgba(64,85,108,.4)!important;color:#f5f9ff!important}
.gs-delete-button .DialogButton{background:linear-gradient(120deg,#b44b54,#cf6863)!important;color:white!important;font-weight:700!important}
.gs-delete-button .DialogButton:disabled{opacity:.38!important}
@media (max-height:660px){.gs-modal{padding:15px 20px}.gs-modal-details{padding:10px}.gs-modal-warning{font-size:11px;margin:9px 0}}

.gs-game-hint{display:flex;align-items:center;gap:7px;flex-wrap:wrap}
.gs-type{font-size:10px;font-weight:750;border:1px solid transparent;border-radius:6px;padding:2px 6px;white-space:nowrap}
.gs-type-steam{color:#83ccff;background:rgba(42,126,200,.17);border-color:rgba(95,163,235,.35)}
.gs-type-non_steam{color:#83e6c7;background:rgba(29,167,119,.13);border-color:rgba(72,205,161,.36)}
.gs-type-unknown{color:#c3bdca;background:rgba(139,135,158,.12);border-color:rgba(162,163,175,.24)}
.gs-source-filters{width:100%;display:flex;flex-wrap:wrap;gap:6px;margin-top:5px;padding-top:10px;border-top:1px solid rgba(255,255,255,.08)}
.gs-installed-warning{font-size:13px;line-height:1.55;color:#ffe0ad;background:rgba(127,64,22,.26);border:1px solid rgba(246,164,76,.5);padding:12px 15px;border-radius:10px;margin-bottom:14px}

.gs-delete-all{width:100%;flex-basis:100%;margin-top:4px;padding-top:9px;border-top:1px solid rgba(248,118,109,.22)}
.gs-screen .gs-delete-all .DialogButton{width:100%!important;text-align:center!important;background:rgba(151,53,57,.28)!important;border:1px solid rgba(242,130,117,.53)!important;color:#ffd7cf!important;font-weight:700!important}
.gs-screen .gs-delete-all .DialogButton:focus{outline:2px solid #ffc3aa!important}
.gs-main{scroll-padding-bottom:70px}
.gs-list-row-wrap{scroll-margin-bottom:70px}
.gs-modal-layer{overscroll-behavior:contain}
.gs-modal{scroll-padding-bottom:28px}

.gs-screen .gs-save-row .DialogButton{background:linear-gradient(120deg,rgba(27,160,133,.27),rgba(45,119,161,.19))!important;color:#8af5d2!important;border:1px solid rgba(72,190,169,.35)!important;font-weight:700!important}
.gs-backup-list{display:flex;flex-direction:column;gap:8px;margin-top:15px}
.gs-backup-item{display:flex;align-items:center;justify-content:space-between;gap:15px;padding:14px;border:1px solid rgba(177,213,244,.12);border-radius:11px;background:rgba(5,19,34,.33)}
.gs-backup-info{min-width:0;flex:1;display:flex;flex-direction:column;gap:4px;overflow-wrap:anywhere}
.gs-backup-item .DialogButton{min-width:155px!important;background:rgba(27,112,116,.28)!important;color:#99edde!important}
.gs-modal .gs-action-primary>.DialogButton{width:100%!important;background:linear-gradient(120deg,#1bcab5,#30bbc7)!important;color:#041b25!important;font-weight:750!important}
.gs-backup-item .gs-game-title{font-size:14px}
@media(max-width:840px){.gs-backup-item{align-items:stretch;flex-direction:column}.gs-backup-item .DialogButton{width:100%!important}}
`;