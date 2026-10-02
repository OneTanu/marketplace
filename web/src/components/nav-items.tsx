import type { ReactNode } from "react";

export type NavItem = { href: string; label: string; icon: ReactNode };

function Icon({ d }: { d: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
      className="size-6"
      aria-hidden="true"
    >
      <path d={d} />
    </svg>
  );
}

export const NAV_ITEMS: NavItem[] = [
  { href: "/", label: "Home", icon: <Icon d="M3 10.5 12 3l9 7.5V21h-6v-6H9v6H3z" /> },
  { href: "/search", label: "Search", icon: <Icon d="m21 21-4.3-4.3M10.5 18a7.5 7.5 0 1 1 0-15 7.5 7.5 0 0 1 0 15z" /> },
  { href: "/sell", label: "Sell", icon: <Icon d="M12 5v14M5 12h14" /> },
  { href: "/inbox", label: "Inbox", icon: <Icon d="M4 5h16v11H8l-4 4z" /> },
  { href: "/profile", label: "Profile", icon: <Icon d="M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM4 21a8 8 0 0 1 16 0" /> },
];
