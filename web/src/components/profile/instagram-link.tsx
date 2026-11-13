import { InstagramIcon } from "@/components/ui/icons";

export function InstagramLink({ handle }: { handle: string }) {
  return (
    <a
      className="inline-flex items-center gap-1.5 font-semibold text-ink underline decoration-ink/25 underline-offset-4 transition hover:decoration-ink"
      href={`https://www.instagram.com/${encodeURIComponent(handle)}/`}
      target="_blank"
      rel="noreferrer"
      aria-label={`@${handle} on Instagram`}
    >
      <InstagramIcon className="size-[1.1em] shrink-0" />
      @{handle} <span aria-hidden="true">↗</span>
    </a>
  );
}
