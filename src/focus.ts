/**
 * GameSweep's Game Mode directional focus bridge.
 *
 * Steam Input sends both D-pad and left-stick navigation as vgp_ondirection
 * events. We use Steam's native focus nodes (BTakeFocus) rather than invoking
 * DOM click, so A, B, focus sounds and gamepad-scrolling stay Steam-native.
 * The hook is scoped to our fullscreen DOM and is removed on unmount.
 */
import { GamepadButton, getGamepadNavigationTrees } from "@decky/ui";
import { useEffect } from "react";
import type { RefObject } from "react";

type Direction = "up" | "down" | "left" | "right";
type FocusNode = {
  Element?: HTMLElement;
  GetChildren(): [FocusNode[], number];
  BTakeFocus(source: number, direction: number): boolean;
};
type FocusTree = { Root?: FocusNode };
type Rect = { x: number; y: number };

const DIR: Record<Direction, number> = {
  up: GamepadButton.DIR_UP,
  down: GamepadButton.DIR_DOWN,
  left: GamepadButton.DIR_LEFT,
  right: GamepadButton.DIR_RIGHT,
};

function nativeFocus(element: HTMLElement, direction: number): boolean {
  const trees = (getGamepadNavigationTrees() as FocusTree[] | undefined) || [];
  for (const tree of trees) {
    const nodes = tree.Root ? [tree.Root] : [];
    while (nodes.length) {
      const node = nodes.pop()!;
      if (node.Element === element) {
        return node.BTakeFocus(0, direction);
      }
      try {
        nodes.push(...node.GetChildren()[0]);
      } catch {
        // Steam may reconfigure a nav tree as a route is closing.
      }
    }
  }
  return false;
}


/** Focus an initial action through Steam's native focus node when available. */
export function focusGameSweepFirstButton(root: HTMLElement, selector: string): void {
  const button = root.querySelector<HTMLElement>(selector);
  if (!button) return;
  if (!nativeFocus(button, GamepadButton.DIR_DOWN)) {
    // DOM fallback for older Decky/Steam clients.
    button.focus();
  }
}

function controls(container: Element | null): HTMLElement[] {
  if (!container) return [];
  return Array.from(container.querySelectorAll<HTMLElement>(".DialogButton, button"))
    .filter((element) => !element.hasAttribute("disabled") &&
      element.getAttribute("aria-disabled") !== "true" &&
      element.getClientRects().length > 0 &&
      element.getBoundingClientRect().width > 0);
}

function center(element: HTMLElement): Rect {
  const r = element.getBoundingClientRect();
  return { x: r.left + r.width / 2, y: r.top + r.height / 2 };
}

function nextSpatial(current: HTMLElement, pool: HTMLElement[],
                     direction: Direction): HTMLElement | undefined {
  const a = center(current);
  let best: HTMLElement | undefined;
  let bestScore = Infinity;
  for (const candidate of pool) {
    if (candidate === current) continue;
    const b = center(candidate);
    const dx = b.x - a.x;
    const dy = b.y - a.y;
    const primary = direction === "left" ? -dx :
      direction === "right" ? dx :
      direction === "up" ? -dy : dy;
    if (primary < 5) continue;
    const secondary = direction === "up" || direction === "down" ?
      Math.abs(dx) : Math.abs(dy);
    // Prioritise the intended axis, then favor staying in the same column.
    const score = primary + secondary * 1.7;
    if (score < bestScore) {
      best = candidate;
      bestScore = score;
    }
  }
  return best;
}

export function useGameSweepGamepadFocus(
  rootRef: RefObject<HTMLDivElement | null>,
  modalOpen: boolean,
): void {
  useEffect(() => {
    function onDirection(event: Event) {
      const root = rootRef.current;
      if (!root) return;
      const code = (event as CustomEvent<{ button?: number }>).detail?.button;
      const direction = (Object.keys(DIR) as Direction[]).find((d) => DIR[d] === code);
      if (!direction || !(event.target instanceof Element)) return;
      if (!root.contains(event.target)) return;

      const modal = root.querySelector(".gs-modal");
      const restricted = modalOpen && modal;
      const zone = restricted || root;
      const all = controls(zone);
      if (!all.length) return;

      const focused = event.target.closest<HTMLElement>(".DialogButton, button");
      const current = focused && all.includes(focused) ? focused : undefined;
      let candidate: HTMLElement | undefined;

      if (!current) {
        candidate = all[0];
      } else if (restricted) {
        // All confirmation actions are in one vertical column. Let both
        // horizontal and vertical directions reach every confirmation option.
        const index = all.indexOf(current);
        const delta = direction === "up" || direction === "left" ? -1 : 1;
        candidate = all[Math.min(all.length - 1, Math.max(0, index + delta))];
      } else {
        const sidebar = root.querySelector(".gs-nav");
        const main = root.querySelector(".gs-main");
        const sideButtons = controls(sidebar);
        const contentButtons = controls(main);
        if (sideButtons.includes(current)) {
          const index = sideButtons.indexOf(current);
          if (direction === "up" || direction === "down") {
            const next = index + (direction === "up" ? -1 : 1);
            candidate = sideButtons[next];
          } else if (direction === "right") {
            candidate = contentButtons[0];
          }
        } else if (contentButtons.includes(current)) {
          // Left from the leftmost content edge returns to the matching
          // sidebar item; other directions stay within the content area.
          candidate = nextSpatial(current, contentButtons, direction);
          if (!candidate && direction === "left") {
            const selected = root.querySelector(".gs-nav .gs-active .DialogButton");
            candidate = selected instanceof HTMLElement ? selected : sideButtons[0];
          }
        }
      }

      if (candidate && candidate !== current && nativeFocus(candidate, code!)) {
        event.preventDefault();
        event.stopPropagation();
        // Steam normally scrolls newly focused elements automatically; this
        // additionally ensures long lists stay reachable on custom routes.
        candidate.scrollIntoView({ block: "nearest", inline: "nearest" });
      }
      // On older Steam clients where the native nav tree differs, leave the
      // event to Steam's built-in directional navigation instead of trapping it.
    }

    document.addEventListener("vgp_ondirection", onDirection, true);
    return () => document.removeEventListener("vgp_ondirection", onDirection, true);
  }, [rootRef, modalOpen]);
}
