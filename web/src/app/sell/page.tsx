import type { Metadata } from "next";

import { RestrictionNotice } from "@/components/trust/restriction-notice";
import { FocusedHeader } from "@/components/ui/focused-header";

import { SellForm } from "./sell-form";

export const metadata: Metadata = { title: "Sell" };

export default function SellPage() {
  return (
    <>
      <FocusedHeader title="Sell an item" backHref="/" backLabel="Back to Home" />
      <section className="mx-auto w-full max-w-2xl px-4 pb-10 pt-4">
        <RestrictionNotice only={["selling"]} />
        <SellForm />
      </section>
    </>
  );
}
