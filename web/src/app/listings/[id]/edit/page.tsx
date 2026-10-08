import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { EditListing } from "./edit-listing";

export const metadata: Metadata = { title: "Edit listing" };

export default async function EditListingPage({ params }: PageProps<"/listings/[id]/edit">) {
  const { id } = await params;
  if (!/^\d{1,15}$/.test(id)) notFound(); // listing IDs are positive integers
  return (
    <section className="mx-auto w-full max-w-2xl px-4 py-6">
      <EditListing listingId={Number(id)} />
    </section>
  );
}
