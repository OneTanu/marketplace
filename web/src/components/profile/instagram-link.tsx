function InstagramIcon() {
  return (
    <svg viewBox="0 0 24 24" className="size-[1.1em] shrink-0" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="2.5" y="2.5" width="19" height="19" rx="5.5" />
      <circle cx="12" cy="12" r="4.25" />
      <circle cx="17.5" cy="6.5" r="0.75" fill="currentColor" stroke="none" />
    </svg>
  );
}

export function InstagramLink({ handle }: { handle: string }) {
  return (
    <a
      className="inline-flex items-center gap-1.5 font-semibold text-ink underline decoration-ink/25 underline-offset-4 transition hover:decoration-ink"
      href={`https://www.instagram.com/${encodeURIComponent(handle)}/`}
      target="_blank"
      rel="noreferrer"
      aria-label={`@${handle} on Instagram`}
    >
      <InstagramIcon />
      @{handle} <span aria-hidden="true">↗</span>
    </a>
  );
}
