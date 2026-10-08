import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { ListingDetail } from "./listing-detail";

export const metadata: Metadata = { title: "Listing" };

export default async function ListingPage({ params }: PageProps<"/listings/[id]">) {
  const { id } = await params;
  if (!/^\d{1,15}$/.test(id)) notFound(); // listing IDs are positive integers
  return <ListingDetail listingId={Number(id)} />;
}
