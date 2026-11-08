import { readFile } from "node:fs/promises";
import { join } from "node:path";

import { ImageResponse } from "next/og";

// The preview card shown when a tanu.one link is shared (GroupMe, iMessage, Instagram, X).
// Generated once at build time; every page uses it unless it sets its own.
export const alt = "Tanu: your campus is a closet. Buy and sell with verified students at your school.";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

const INK = "#17162b";
const MUTED = "#6b6a7b";
const KRAFT = "#d7b98e";

export default async function OpengraphImage() {
  const [wide, medium, logo] = await Promise.all([
    readFile(join(process.cwd(), "src/assets/fonts/ArchivoExpanded-Black.ttf")),
    readFile(join(process.cwd(), "src/assets/fonts/Archivo-Medium.ttf")),
    readFile(join(process.cwd(), "public/icon-512.png"), "base64"),
  ]);

  return new ImageResponse(
    <div style={{ width: "100%", height: "100%", display: "flex", flexDirection: "column", justifyContent: "space-between", background: "#ffffff", padding: "64px 72px", fontFamily: "Archivo" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 22 }}>
        <img src={`data:image/png;base64,${logo}`} width={72} height={72} style={{ borderRadius: 16 }} alt="" />
        <span style={{ fontFamily: "Archivo Expanded", fontSize: 46, color: INK, letterSpacing: -1 }}>tanu</span>
      </div>
      <div style={{ display: "flex", flexDirection: "column", fontFamily: "Archivo Expanded", fontSize: 92, lineHeight: 0.98, color: INK, letterSpacing: -2 }}>
        <span>Your campus</span>
        <span>is a closet.</span>
      </div>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <span style={{ fontSize: 32, color: MUTED }}>Buy and sell with verified students at your school.</span>
        <span style={{ display: "flex", background: KRAFT, color: INK, fontFamily: "Archivo Expanded", fontSize: 30, padding: "12px 22px", borderRadius: 8, transform: "rotate(-3deg)" }}>tanu.one</span>
      </div>
    </div>,
    {
      ...size,
      fonts: [
        { name: "Archivo Expanded", data: wide, weight: 900, style: "normal" },
        { name: "Archivo", data: medium, weight: 500, style: "normal" },
      ],
    },
  );
}
