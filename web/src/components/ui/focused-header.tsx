import Link from "next/link";
import { ChevronLeftIcon } from "@/components/ui/icons";

export function BackLink({ href, label }: { href: string; label: string }) {
  return (
    <Link href={href} aria-label={label} className="grid size-11 shrink-0 place-items-center rounded-lg text-ink transition hover:bg-surface">
      <ChevronLeftIcon className="size-6" aria-hidden="true" />
    </Link>
  );
}

/**
 * The top of a focused screen (Sell, Edit listing, Meetup preferences): a back button and the
 * page title, nothing else. On phones it is the only header, so it sticks to the top; on
 * desktop it sits under the site header.
 */
export function FocusedHeader({ title, backHref, backLabel, width = "max-w-2xl" }: {
  title: string;
  backHref: string;
  backLabel: string;
  /** Matches the page's own max width, so the title lines up with the content. */
  width?: string;
}) {
  return (
    <header className="sticky top-0 z-20 border-b border-line bg-background/95 backdrop-blur-xl desktop:static desktop:border-0 desktop:bg-transparent desktop:pt-6 desktop:backdrop-blur-none">
      <div className={`mx-auto flex min-h-14 w-full items-center gap-1 px-2 sm:px-4 ${width}`}>
        <BackLink href={backHref} label={backLabel} />
        <h1 className="type-wide min-w-0 flex-1 truncate text-title font-extrabold">{title}</h1>
      </div>
    </header>
  );
}
