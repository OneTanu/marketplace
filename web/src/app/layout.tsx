import type { Metadata, Viewport } from "next";
import { Archivo } from "next/font/google";

import { SiteFooter } from "@/components/site-footer";
import { SiteNav } from "@/components/site-nav";
import { SITE_URL } from "@/lib/site";

import "./globals.css";

const archivo = Archivo({
  variable: "--font-archivo",
  subsets: ["latin"],
  axes: ["wdth"],
});

const DESCRIPTION = "Buy and sell with verified students at your school.";

export const metadata: Metadata = {
  // Makes the preview image (app/opengraph-image.tsx) an absolute URL, which link previews need.
  metadataBase: new URL(SITE_URL),
  title: { default: "Tanu — Your campus marketplace", template: "%s · Tanu" },
  description: DESCRIPTION,
  appleWebApp: { capable: true, title: "Tanu", statusBarStyle: "default" },
  openGraph: { siteName: "Tanu", type: "website", locale: "en_US", title: "Tanu — Your campus marketplace", description: DESCRIPTION },
  twitter: { card: "summary_large_image", title: "Tanu — Your campus marketplace", description: DESCRIPTION },
};

export const viewport: Viewport = {
  themeColor: "#ffffff",
  viewportFit: "cover",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      data-scroll-behavior="smooth"
      className={`${archivo.variable} h-full antialiased`}
    >
      <body className="flex min-h-full flex-col">
        <SiteNav />
        {/* No bottom padding here: SiteFooter, last on the page, carries the space for the phone
            bottom bar (the footer itself, or a spacer), and focused screens have neither. */}
        <main className="flex-1">{children}</main>
        <SiteFooter />
      </body>
    </html>
  );
}
