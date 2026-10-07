import type { Metadata } from "next";

import { SchoolMarketplaceView } from "@/components/school-marketplace";

export const metadata: Metadata = { title: "School marketplace" };

export default async function SchoolMarketplacePage({ params }: PageProps<"/schools/[slug]">) {
  const { slug } = await params;
  return <SchoolMarketplaceView slug={slug} />;
}
