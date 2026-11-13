import type { Metadata } from "next";
import Link from "next/link";
import { BlankTagDrawing } from "@/components/ui/icons";

export const metadata: Metadata = { title: "Page not found" };

/** Shown for any URL that matches no page, and wherever a page calls notFound(). It renders
 * inside the root layout, so the header and bottom bar stay. */
export default function NotFound() {
  return (
    <section className="mx-auto grid min-h-[65vh] max-w-xl place-items-center px-4 py-16 text-center">
      <div>
        {/* A blank hang tag: the item that used to be here is gone. */}
        <div aria-hidden="true" className="relative mx-auto w-36 -rotate-6">
          <BlankTagDrawing className="w-full" />
          <span className="type-wide absolute inset-y-0 left-10 right-2 grid place-items-center text-display font-extrabold text-ink">404</span>
        </div>
        <h1 className="type-wide mt-8 text-display font-extrabold">This page isn’t here</h1>
        <p className="mt-3 leading-7 text-muted">The link may be old, or the listing it pointed to was taken down.</p>
        <Link href="/" className="btn btn-primary mt-7">Back to Home</Link>
      </div>
    </section>
  );
}
