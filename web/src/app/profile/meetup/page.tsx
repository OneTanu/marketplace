import type { Metadata } from "next";

import { MeetupPreferences } from "@/components/profile/meetup-preferences";

export const metadata: Metadata = { title: "Meetup preferences" };

export default function MeetupPreferencesPage() {
  return <MeetupPreferences />;
}
