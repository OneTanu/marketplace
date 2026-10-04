import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";

import { SiteFooter } from "@/components/site-footer";
import { SiteNav } from "@/components/site-nav";

import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: { default: "Tanu — Your campus marketplace", template: "%s · Tanu" },
  description: "Buy and sell with verified students at your school.",
  appleWebApp: { capable: true, title: "Tanu", statusBarStyle: "default" },
};

export const viewport: Viewport = {
  themeColor: "#f7f5ef",
  viewportFit: "cover",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      data-scroll-behavior="smooth"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
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
