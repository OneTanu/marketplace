import { Avatar } from "@/components/ui/avatar";
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
  /** Adds a followers count (the account hub shows it; the public profile has its own). */
  followerCount?: number;
  /** The name is the page's h1 on a profile; the design lab nests the card under an h2. */
  nameAs?: "h1" | "h3";
};

/**
 * The profile header, in the shape of a campus ID (85.6 × 54 mm, like a bank card) at every
 * width, without copying any school's real card: no logos, seals, ID numbers or barcodes.
 * The school's colours fill the stripe across the top and nowhere else.
 */
export function StudentIdCard({ firstName, lastInitial, username, schoolName, schoolColors, dateJoined, soldCount, followerCount, nameAs: Name = "h1" }: StudentIdCardProps) {
  const { stripe } = schoolPalette(schoolColors);
  const name = firstName ? `${firstName}${lastInitial ? ` ${lastInitial}.` : ""}` : `@${username}`;

  return (
    <div className="grid aspect-[85.6/54] w-full max-w-[26rem] grid-rows-[auto_1fr] overflow-hidden rounded-xl border border-line bg-background shadow-card">
      <div className="flex h-3.5" aria-hidden="true">
        {stripe.map((color, index) => <span key={index} style={{ background: color, width: stripeWidth(index, stripe.length) }} />)}
      </div>
      <div className="flex min-h-0 items-center gap-4 px-4.5 desktop:gap-5 desktop:px-5">
        <Avatar user={{ first_name: firstName, username }} size="lg" />
        <div className="min-w-0">
          <Name className="type-wide line-clamp-2 text-title font-extrabold text-ink [overflow-wrap:anywhere]">{name}</Name>
          {/* Without a first name the heading is already the username, so it isn't repeated. */}
          {firstName && <p className="truncate text-fine text-muted">@{username}</p>}
          {schoolName && <p className="truncate text-fine text-muted">{schoolName}</p>}
          <p className="mt-2 flex flex-wrap gap-x-3.5 text-fine text-ink">
            <span><b className="font-semibold tabular-nums">{soldCount}</b> sold</span>
            {followerCount !== undefined && <span><b className="font-semibold tabular-nums">{followerCount}</b> {followerCount === 1 ? "follower" : "followers"}</span>}
          </p>
          <p className="mt-0.5 text-fine text-muted">Joined {joinedLabel(dateJoined)}</p>
        </div>
      </div>
    </div>
  );
}
