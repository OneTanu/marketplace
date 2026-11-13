import { cookies } from "next/headers";

import { GuestHome } from "@/components/home/guest-home";
import { SignedInHome } from "@/components/home/signed-in-home";

/** Home. With a session cookie it's the student's school feed; without one, the guest page.
 * The cookie only says a session might exist (it can be expired), so the feed confirms it and
 * falls back to the guest page. Reading the cookie makes Home render per request. */
export default async function HomePage() {
  const maybeSignedIn = (await cookies()).has("sessionid");
  return maybeSignedIn ? <SignedInHome guest={<GuestHome />} /> : <GuestHome />;
}
