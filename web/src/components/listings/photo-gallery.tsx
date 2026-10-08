"use client";

import Image from "next/image";
import { useRef, useState } from "react";

import type { components } from "@/lib/api/schema";

type Photo = components["schemas"]["ListingPhoto"];

/** A listing's photos, cover first. One swipeable row (scroll snap) on every screen; wide
 * screens also get a thumbnail strip that scrolls the row to the picked photo. */
export function PhotoGallery({ photos, title }: { photos: Photo[]; title: string }) {
  const ordered = [...photos].sort((a, b) => a.position - b.position);
  const [current, setCurrent] = useState(0);
  const row = useRef<HTMLDivElement>(null);

  function show(index: number) {
    const element = row.current;
    if (!element) return;
    element.scrollTo({ left: index * element.clientWidth, behavior: "smooth" });
  }

  function onScroll() {
    const element = row.current;
    if (!element || !element.clientWidth) return;
    setCurrent(Math.round(element.scrollLeft / element.clientWidth));
  }

  const count = ordered.length;

  return (
    <div className="flex gap-3">
      {count > 1 && (
        <ul aria-label="Photos" className="hidden w-16 shrink-0 flex-col gap-2 lg:flex">
          {ordered.map((photo, index) => (
            <li key={photo.id}>
              <button
                type="button"
                onClick={() => show(index)}
                aria-label={`Show photo ${index + 1} of ${count}`}
                aria-current={current === index || undefined}
                className="relative block aspect-[4/5] w-full overflow-hidden rounded-md bg-surface outline-offset-2 ring-ink aria-[current]:ring-2"
              >
                <Image src={photo.thumbnail_url ?? photo.image_url} alt="" fill unoptimized className="object-cover" />
              </button>
            </li>
          ))}
        </ul>
      )}
      <div className="relative min-w-0 flex-1">
        <div
          ref={row}
          onScroll={onScroll}
          className="flex aspect-[4/5] snap-x snap-mandatory overflow-x-auto rounded-none bg-surface [scrollbar-width:none] sm:rounded-lg"
        >
          {ordered.map((photo, index) => (
            <div key={photo.id} className="relative h-full w-full shrink-0 snap-center">
              {/* unoptimized: Django serves /media directly, so Next's image optimizer isn't
                  in the path. */}
              <Image
                src={photo.image_url}
                alt={`${title}, photo ${index + 1} of ${count}`}
                fill
                unoptimized
                priority={index === 0}
                className="object-contain"
              />
            </div>
          ))}
        </div>
        {count > 1 && (
          // For mouse and keyboard users below lg, where there's no thumbnail strip.
          <>
            <GalleryArrow label="Previous photo" onClick={() => show(current - 1)} disabled={current === 0} side="left" />
            <GalleryArrow label="Next photo" onClick={() => show(current + 1)} disabled={current === count - 1} side="right" />
          </>
        )}
        {count > 1 && (
          <div aria-hidden="true" className="pointer-events-none absolute inset-x-0 bottom-3 flex justify-center gap-1.5">
            {ordered.map((photo, index) => (
              <span
                key={photo.id}
                className={`size-1.5 rounded-full ${current === index ? "bg-white" : "bg-white/50"} shadow`}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function GalleryArrow({
  label,
  onClick,
  disabled,
  side,
}: {
  label: string;
  onClick: () => void;
  disabled: boolean;
  side: "left" | "right";
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-label={label}
      className={`absolute top-1/2 grid size-9 -translate-y-1/2 place-items-center rounded-full bg-background/90 text-ink shadow disabled:hidden lg:hidden ${side === "left" ? "left-2" : "right-2"}`}
    >
      <svg viewBox="0 0 24 24" className="size-4" fill="none" stroke="currentColor" strokeWidth={2.2} aria-hidden="true">
        <path d={side === "left" ? "M15 6l-6 6 6 6" : "M9 6l6 6-6 6"} />
      </svg>
    </button>
  );
}
