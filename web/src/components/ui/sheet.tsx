"use client";

import { useEffect, useId, useRef, type ReactNode } from "react";

import { CloseIcon } from "./icons";

/**
 * A bottom sheet on phones and a centred dialog on desktop, built on the browser's own <dialog>
 * (focus trap, Escape, top layer). It slides up in 280ms and leaves in 200ms; with reduced
 * motion it only fades. Tapping the dimmed area closes it. First used for real in slice 2.
 */
export function Sheet({ open, onClose, title, children }: { open: boolean; onClose: () => void; title: string; children: ReactNode }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  // Where the pointer went down: selecting text inside and letting go over the dimmed area isn't a tap on it.
  const downOnBackdrop = useRef(false);

  useEffect(() => {
    const el = dialog.current;
    if (!el) return;
    if (open && !el.open) el.showModal();
    if (!open && el.open) el.close();
  }, [open]);

  return (
    <dialog
      ref={dialog}
      aria-labelledby={titleId}
      onClose={onClose}
      onPointerDown={(event) => { downOnBackdrop.current = event.target === dialog.current; }}
      onClick={(event) => { if (event.target === dialog.current && downOnBackdrop.current) onClose(); }}
      className="sheet"
    >
      <div className="sheet-body">
        <div aria-hidden="true" className="mx-auto mb-3 h-1 w-9 rounded-full bg-line desktop:hidden" />
        <div className="flex items-center justify-between gap-3">
          <h2 id={titleId} className="type-wide text-title font-extrabold">{title}</h2>
          <button type="button" onClick={onClose} aria-label="Close" className="-mr-2 grid size-11 shrink-0 place-items-center rounded-full text-muted transition hover:bg-surface hover:text-ink">
            <CloseIcon className="size-5" aria-hidden="true" />
          </button>
        </div>
        <div className="mt-3">{children}</div>
      </div>
    </dialog>
  );
}
