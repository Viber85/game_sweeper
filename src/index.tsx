import { Navigation, Router, staticClasses } from "@decky/ui";
import { definePlugin, routerHook } from "@decky/api";
import { useEffect } from "react";
import { FaBroom } from "react-icons/fa";
import { GameSweepFullScreen } from "./fullscreen";

const FULLSCREEN_PATH = "/gamesweep";

function openFullScreen(): void {
  Router.CloseSideMenus();
  try {
    Navigation.Navigate(FULLSCREEN_PATH);
  } catch {
    Router.Navigate(FULLSCREEN_PATH);
  }
}

/** Mounted when the GameSweep QAM entry is opened.
 * Open its own route immediately; no intermediate launcher button.
 */
function Launcher() {
  useEffect(() => {
    // Defer navigation one tick so Steam finishes rendering the QAM entry.
    const timer = window.setTimeout(openFullScreen, 0);
    return () => window.clearTimeout(timer);
  }, []);

  return (
    <div style={{ padding: 12, fontSize: 13, opacity: 0.8 }}>
      Opening GameSweep fullscreen…
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
