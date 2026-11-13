"use client";

import Link from "next/link";
import { createContext, useContext, useEffect, useId, useRef, useState, type KeyboardEvent, type ReactNode } from "react";

const CloseMenu = createContext<() => void>(() => {});

const ITEM = "flex min-h-11 w-full items-center px-4 text-left text-sm font-semibold text-ink transition hover:bg-surface focus-visible:bg-surface focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-ink";

function items(menu: HTMLElement | null) {
  return menu ? [...menu.querySelectorAll<HTMLElement>("[role=menuitem]")] : [];
}

/**
 * A button that opens a short list of actions or links ("More", the account menu).
 * Closes on Escape, a click outside, Tab, or choosing an item. Arrow keys, Home and End move
 * between items. Focus returns to the button when it closes from the keyboard.
 */
export function Menu({ label, trigger, triggerClassName = "", align = "end", children }: {
  /** The button's accessible name, e.g. "Account menu" or "More". */
  label: string;
  trigger: ReactNode;
  triggerClassName?: string;
  align?: "start" | "end";
  children: ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const wrapper = useRef<HTMLDivElement>(null);
  const button = useRef<HTMLButtonElement>(null);
  const menu = useRef<HTMLDivElement>(null);
  // Which item to focus once the menu has rendered: the first or last (from the keyboard), or none (a click).
  const focusOnOpen = useRef<"first" | "last" | null>(null);
  const id = useId();

  useEffect(() => {
    if (!open) return;
    const list = items(menu.current);
    if (focusOnOpen.current === "first") list[0]?.focus();
    if (focusOnOpen.current === "last") list.at(-1)?.focus();
    focusOnOpen.current = null;
    function outside(event: PointerEvent) {
      if (!wrapper.current?.contains(event.target as Node)) setOpen(false);
    }
    document.addEventListener("pointerdown", outside);
    return () => document.removeEventListener("pointerdown", outside);
  }, [open]);

  function show(focus: "first" | "last" | null) {
    if (open) {
      const list = items(menu.current);
      (focus === "last" ? list.at(-1) : list[0])?.focus();
      return;
    }
    focusOnOpen.current = focus;
    setOpen(true);
  }

  function close(returnFocus: boolean) {
    setOpen(false);
    if (returnFocus) button.current?.focus();
  }

  function onButtonKey(event: KeyboardEvent) {
    if (event.key === "ArrowDown") { event.preventDefault(); show("first"); }
    if (event.key === "ArrowUp") { event.preventDefault(); show("last"); }
    if (event.key === "Escape" && open) { event.preventDefault(); close(true); }
  }

  function onMenuKey(event: KeyboardEvent) {
    const list = items(menu.current);
    const index = list.indexOf(document.activeElement as HTMLElement);
    const move = (to: number) => { event.preventDefault(); list[(to + list.length) % list.length]?.focus(); };
    if (event.key === "ArrowDown") move(index + 1);
    else if (event.key === "ArrowUp") move(index - 1);
    else if (event.key === "Home") move(0);
    else if (event.key === "End") move(list.length - 1);
    else if (event.key === "Escape") { event.preventDefault(); close(true); }
    else if (event.key === "Tab") setOpen(false);
  }

  return (
    <div ref={wrapper} className="relative">
      <button
        ref={button}
        type="button"
        aria-label={label}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={open ? id : undefined}
        // detail is 0 when Enter or Space pressed the button; then focus goes into the menu.
        onClick={(event) => (open ? close(false) : show(event.detail === 0 ? "first" : null))}
        onKeyDown={onButtonKey}
        className={triggerClassName}
      >
        {trigger}
      </button>
      {open && (
        <div
          ref={menu}
          id={id}
          role="menu"
          aria-label={label}
          onKeyDown={onMenuKey}
          className={`absolute top-full z-40 mt-2 min-w-52 overflow-hidden rounded-xl border border-line bg-background py-1.5 shadow-[0_16px_40px_-12px_rgb(23_22_43/22%)] ${align === "end" ? "right-0" : "left-0"}`}
        >
          <CloseMenu.Provider value={() => close(false)}>{children}</CloseMenu.Provider>
        </div>
      )}
    </div>
  );
}

export function MenuLink({ href, children }: { href: string; children: ReactNode }) {
  const close = useContext(CloseMenu);
  // Menu items answer Space as well as Enter; a link only answers Enter on its own.
  return <Link href={href} role="menuitem" tabIndex={-1} onClick={close} onKeyDown={(event) => { if (event.key === " ") { event.preventDefault(); event.currentTarget.click(); } }} className={ITEM}>{children}</Link>;
}

export function MenuButton({ onSelect, children }: { onSelect: () => void; children: ReactNode }) {
  const close = useContext(CloseMenu);
  return <button type="button" role="menuitem" tabIndex={-1} onClick={() => { close(); onSelect(); }} className={ITEM}>{children}</button>;
}

export function MenuDivider() {
  return <div role="separator" className="my-1.5 border-t border-line" />;
}
