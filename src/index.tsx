import { ButtonItem, Navigation, Router, staticClasses } from "@decky/ui";
import { definePlugin, routerHook } from "@decky/api";
import { FaBroom, FaExpandArrowsAlt } from "react-icons/fa";
import { GameSweepFullScreen } from "./fullscreen";

const FULLSCREEN_PATH = "/gamesweep";

function openFullScreen(): void {
  // Open a real Game Mode route, not a CSS overlay inside the QAM panel.
  Router.CloseSideMenus();
  try {
    Navigation.Navigate(FULLSCREEN_PATH);
  } catch {
    Router.Navigate(FULLSCREEN_PATH);
  }
}

function Launcher() {
  return (
    <div style={{ padding: 12, minWidth: 0 }}>
      <div style={{ marginBottom: 12, fontSize: 12, opacity: 0.75 }}>
        GameSweep has its own fullscreen interface in SteamOS Game Mode.
      </div>
      <ButtonItem layout="below" onClick={openFullScreen}>
        <FaExpandArrowsAlt style={{ marginRight: 8 }} />
        Open GameSweep fullscreen
      </ButtonItem>
      <div style={{ fontSize: 11, opacity: 0.7, marginTop: 12 }}>
        Preview scanner only. No delete operations.
      </div>
    </div>
  );
}

export default definePlugin(() => {
  routerHook.addRoute(FULLSCREEN_PATH, GameSweepFullScreen);
  return {
    name: "GameSweep",
    titleView: <div className={staticClasses.Title}>GameSweep</div>,
    icon: <FaBroom />,
    content: <Launcher />,
    onDismount() {
      routerHook.removeRoute(FULLSCREEN_PATH);
    }
  };
});
