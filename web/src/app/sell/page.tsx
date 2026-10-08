import type { Metadata } from "next";

import { SellForm } from "./sell-form";

export const metadata: Metadata = { title: "Sell" };

export default function SellPage() {
  return (
    <section className="mx-auto w-full max-w-2xl px-4 py-6">
      <h1 className="text-2xl font-semibold tracking-tight">Sell an item</h1>
      <SellForm />
    </section>
  );
}
