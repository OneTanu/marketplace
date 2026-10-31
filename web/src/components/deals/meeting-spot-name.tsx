import type { components } from "@/lib/api/schema";

type MeetingSpot = Pick<components["schemas"]["MeetingSpot"], "name" | "is_indoor">;

/** A meetup spot's name with an Indoors/Outdoors tag, so both students know which side of
 * the doors to wait on. */
export function MeetingSpotName({ spot }: { spot: MeetingSpot }) {
  return <>
    {spot.name}
    <span className="ml-1.5 inline-block rounded-full bg-surface px-2 py-0.5 align-middle text-[11px] font-semibold leading-none text-muted">{spot.is_indoor ? "Indoors" : "Outdoors"}</span>
  </>;
}
