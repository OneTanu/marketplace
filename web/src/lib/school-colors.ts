// School colors appear only as a stripe or a badge, never as a theme or logo.

/** How a school's colors are used: the lead fills the badge, the accent edges it, and the
 * stripe shows every color in order. Schools without colors fall back to Tanu's ink and kraft. */
export type SchoolPalette = { lead: string; accent: string; text: string; stripe: string[] };

const INK = "#17162B";
const KRAFT = "#D7B98E";

function luminance(hex: string) {
  const channels = [1, 3, 5].map((start) => {
    const value = parseInt(hex.slice(start, start + 2), 16) / 255;
    return value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2];
}

export function contrast(a: string, b: string) {
  const [light, dark] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (light + 0.05) / (dark + 0.05);
}

export function schoolPalette(colors: readonly string[] | undefined): SchoolPalette {
  const stripe = colors?.length ? [...colors] : [INK, KRAFT];
  const [lead, accent = lead] = stripe;
  // Text on the lead: the accent if it's readable (WCAG AA, 4.5:1), else black or white.
  const text = contrast(lead, accent) >= 4.5
    ? accent
    : contrast(lead, "#FFFFFF") >= contrast(lead, "#000000") ? "#FFFFFF" : "#000000";
  return { lead, accent, text, stripe };
}
