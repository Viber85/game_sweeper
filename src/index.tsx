import { Navigation, Router, staticClasses } from "@decky/ui";
import { definePlugin, routerHook } from "@decky/api";
import { useEffect, useState } from "react";
import { FaBroom } from "react-icons/fa";
import { GameSweepFullScreen } from "./fullscreen";
import { ModernGameSweep } from "./modern";

const FULLSCREEN_PATH = "/gamesweep";

// Decky retains the last selected plugin when the Quick Access menu closes.
// Avoid an endless re-open cycle when a user comes back from fullscreen.
let showReturnHintOnce = false;

function openFullScreen(): void {
  Router.CloseSideMenus();
  try {
    Navigation.Navigate(FULLSCREEN_PATH);
  } catch {
    Router.Navigate(FULLSCREEN_PATH);
  }
}

function Launcher() {
  const [returnHint, setReturnHint] = useState(false);

  useEffect(() => {
    if (showReturnHintOnce) {
      showReturnHintOnce = false;
      setReturnHint(true);
      return;
    }

    // Defer until the plugin panel has mounted. On a new selection
    // the fullscreen route opens without any extra "Enter" button.
    const timer = window.setTimeout(() => {
      showReturnHintOnce = true;
      openFullScreen();
    }, 0);
    return () => window.clearTimeout(timer);
  }, []);

  return (
    <div style={{ padding: 12, fontSize: 13, opacity: 0.8 }}>
      {returnHint
        ? "Press B to return to Decky's plugin list. Select GameSweep to open it again."
        : "Opening GameSweep fullscreen…"}
    </div>
  );
}

export default definePlugin(() => {
  routerHook.addRoute(FULLSCREEN_PATH, ModernGameSweep);
  routerHook.addRoute("/gamesweep-classic", GameSweepFullScreen);
  return {
    name: "GameSweep",
    titleView: <div className={staticClasses.Title}>GameSweep</div>,
    icon: <FaBroom />,
    content: <Launcher />,
    onDismount() {
      routerHook.removeRoute(FULLSCREEN_PATH);
      routerHook.removeRoute("/gamesweep-classic");
    }
  };
});
