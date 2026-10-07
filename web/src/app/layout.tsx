import type { Metadata, Viewport } from "next";
import { Archivo } from "next/font/google";

import { SiteFooter } from "@/components/site-footer";
import { SiteNav } from "@/components/site-nav";

import "./globals.css";

const archivo = Archivo({
  variable: "--font-archivo",
  subsets: ["latin"],
  axes: ["wdth"],
});

export const metadata: Metadata = {
  title: { default: "Tanu — Your campus marketplace", template: "%s · Tanu" },
  description: "Buy and sell with verified students at your school.",
  appleWebApp: { capable: true, title: "Tanu", statusBarStyle: "default" },
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
        {/* Bottom padding keeps content clear of the phone tab bar. */}
        <main className="flex-1 pb-20 desktop:pb-0">{children}</main>
        <div className="pb-20 desktop:pb-0">
          <SiteFooter />
        </div>
      </body>
    </html>
  );
}
