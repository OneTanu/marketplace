import { schoolPalette } from "@/lib/school-colors";

// The first color takes most of the stripe; the rest share what's left.
function stripeWidth(index: number, count: number) {
  if (count === 1) return "100%";
  const lead = count === 2 ? 80 : 72;
  return `${index === 0 ? lead : (100 - lead) / (count - 1)}%`;
}

function joinedLabel(dateJoined: string) {
  return new Date(dateJoined).toLocaleDateString("en-US", { month: "short", year: "numeric", timeZone: "America/New_York" });
}

export type StudentIdCardProps = {
  firstName: string;
  lastInitial: string;
  username: string;
  schoolName?: string;
  schoolColors?: readonly string[];
  dateJoined: string;
  soldCount: number;
  /** The name is the page's h1 on a profile; the design lab nests the card under an h2. */
  nameAs?: "h1" | "h3";
};

// The profile header, shaped like a campus ID (a little shorter than the real 85.6 × 54 mm card)
// without copying any school's real card: no logos, seals, ID numbers, or barcodes.
export function StudentIdCard({ firstName, lastInitial, username, schoolName, schoolColors, dateJoined, soldCount, nameAs: Name = "h1" }: StudentIdCardProps) {
  const { stripe } = schoolPalette(schoolColors);
  const name = firstName ? `${firstName}${lastInitial ? ` ${lastInitial}.` : ""}` : `@${username}`;
  const initial = (firstName[0] || username[0] || "T").toUpperCase();

  return (
    <div className="relative grid w-full max-w-[26rem] grid-cols-[30%_1fr] items-center gap-4 overflow-hidden rounded-[14px] border border-line bg-background px-4 pt-8 pb-4 sm:aspect-[85.6/48]">
      {/* School stripe: the one place the school's colors fill space. */}
      <div className="absolute inset-x-0 top-0 flex h-4" aria-hidden="true">
        {stripe.map((color, index) => <span key={index} style={{ background: color, width: stripeWidth(index, stripe.length) }} />)}
      </div>
      <div className="type-wide grid aspect-[4/5] place-items-center rounded-md bg-surface text-4xl font-black text-ink" aria-hidden="true">{initial}</div>
      <div className="min-w-0">
        <Name className="type-wide truncate text-[22px] font-black leading-none text-ink">{name}</Name>
        {schoolName && <p className="mt-1 text-[13px] text-muted">{schoolName}</p>}
        <p className="mt-0.5 truncate text-[13px] font-bold text-ink">@{username}</p>
        <ul className="mt-3 grid gap-1 text-[13px] text-ink">
          <li>Joined <b className="font-extrabold">{joinedLabel(dateJoined)}</b></li>
          <li><b className="font-extrabold">{soldCount}</b> sold</li>
        </ul>
      </div>
    </div>
  );
}
