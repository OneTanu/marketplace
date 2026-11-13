/**
 * Every icon in the app comes from here: Lucide (2px outlines on a 24px grid), plus the two
 * drawings Lucide doesn't have. Import from this file, never from lucide-react directly, so the
 * set stays one family. Lucide has no filled icons: a current tab is ink with strokeWidth 2.4,
 * and a saved heart is the outline filled in.
 */
import type { SVGProps } from "react";

export {
  ArrowDownUp as SortIcon,
  ArrowUp as SendIcon,
  Ban as BlockedIcon,
  Bell as BellIcon,
  Bookmark as BookmarkIcon,
  Check as CheckIcon,
  Gavel as ModerationIcon,
  ChevronDown as ChevronDownIcon,
  ChevronLeft as ChevronLeftIcon,
  ChevronRight as ChevronRightIcon,
  Handshake as DealsIcon,
  Heart as HeartIcon,
  House as HomeIcon,
  LogOut as LogOutIcon,
  MapPin as MapPinIcon,
  MessageCircle as InboxIcon,
  Plus as PlusIcon,
  Search as SearchIcon,
  Share as ShareIcon,
  ShieldCheck as ShieldCheckIcon,
  SlidersHorizontal as FiltersIcon,
  Store as StoreIcon,
  User as ProfileIcon,
  X as CloseIcon,
} from "lucide-react";

/** Lucide dropped brand logos, so the Instagram glyph is drawn here in Lucide's style. */
export function InstagramIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" width={24} height={24} fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}>
      <rect x="2.5" y="2.5" width="19" height="19" rx="5.5" />
      <circle cx="12" cy="12" r="4.25" />
      <circle cx="17.5" cy="6.5" r="0.75" fill="currentColor" stroke="none" />
    </svg>
  );
}

/** The blank hang tag on the 404 page. */
export function BlankTagDrawing(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 144 88" fill="none" aria-hidden="true" {...props}>
      <path d="M28 4h108a4 4 0 0 1 4 4v72a4 4 0 0 1-4 4H28L4 58V30z" stroke="var(--ink)" strokeWidth="2.5" strokeLinejoin="round" />
      <circle cx="24" cy="44" r="5" stroke="var(--ink)" strokeWidth="2.5" />
    </svg>
  );
}
