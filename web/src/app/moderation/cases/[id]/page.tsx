import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { CaseDetailView } from "@/components/moderation/case-detail";

export const metadata: Metadata = { title: "Moderation case", robots: { index: false } };

export default async function ModerationCasePage({ params }: PageProps<"/moderation/cases/[id]">) {
  const { id } = await params;
  if (!/^\d{1,15}$/.test(id)) notFound();
  return <CaseDetailView caseId={Number(id)} />;
}
