// One-off codemod for slice 1c: moves class strings onto the design tokens.
// node eslint-rules/codemod-tokens.mjs <file...>   (prints how many tokens changed per file)
// Kept in the repo beside the lint rule so the mapping from old classes to roles is on record.
import fs from "node:fs";

const SIZE = {
  "text-xs": "text-fine", "text-[10px]": "text-fine", "text-[11px]": "text-fine", "text-[12px]": "text-fine", "text-[13px]": "text-fine",
  "text-sm": "text-label", "text-[14px]": "text-label",
  "text-base": "text-body", "text-[15px]": "text-body", "text-[16px]": "text-body",
  "text-lg": "text-title", "text-xl": "text-title", "text-[17px]": "text-title", "text-[22px]": "text-title", "text-[1.375rem]": "text-title",
  "text-2xl": "text-display", "text-3xl": "text-display", "text-4xl": "text-display", "text-5xl": "text-display", "text-6xl": "text-display",
  "text-[1.625rem]": "text-display", "text-[2rem]": "text-display", "text-[2.5rem]": "text-display", "text-[2.75rem]": "text-display",
};
const RADIUS = { "": "lg", sm: "lg", md: "lg", "2xl": "xl", "3xl": "xl", "[14px]": "xl", "[1.375rem]": "xl", "[0.625rem]": "lg", "[0.5rem]": "lg", "[0.75rem]": "xl" };
const SHADOW = {
  shadow: "shadow-float", "shadow-sm": "shadow-float", "shadow-md": "shadow-overlay", "shadow-lg": "shadow-overlay", "shadow-xl": "shadow-overlay",
  "shadow-[0_6px_20px_-8px_rgb(23_22_43/25%)]": "shadow-card",
  "shadow-[0_24px_48px_-12px_rgb(23_22_43/18%)]": "shadow-overlay",
  "shadow-[0_16px_40px_-12px_rgb(23_22_43/22%)]": "shadow-overlay",
};
const COLOUR = {
  "[var(--danger)]": "danger", "[var(--danger-soft)]": "danger-soft", "[var(--brand-soft)]": "brand-soft", "[var(--ink-soft)]": "ink-soft",
  "[var(--brand)]": "brand", "[var(--success)]": "success", "[var(--success-soft)]": "success-soft", "[var(--warning)]": "warning",
  "[var(--warning-soft)]": "warning-soft", "[#d42b33]": "danger", "[var(--muted)]": "muted", "[var(--line)]": "line", "[var(--surface)]": "surface",
  "[var(--kraft)]": "kraft", "[var(--signal)]": "signal", "[var(--ink)]": "ink",
};
const RESPONSIVE = /^(?:sm|md|lg|xl|2xl|desktop):$/;

function split(token) {
  let depth = 0, cut = 0;
  for (let i = 0; i < token.length; i++) {
    const c = token[i];
    if (c === "[" || c === "(") depth++;
    else if (c === "]" || c === ")") depth--;
    else if (c === ":" && depth === 0) cut = i + 1;
  }
  return [token.slice(0, cut), token.slice(cut)];
}

function mapClass(cls, wide) {
  const bang = cls.startsWith("!") ? "!" : "";
  const c = bang ? cls.slice(1) : cls;
  let out = SIZE[c];
  if (!out && /^font-(black|bold|medium|light|thin|extralight)$/.test(c)) out = c === "font-black" || (c === "font-bold" && wide) ? "font-extrabold" : c === "font-light" || c === "font-thin" || c === "font-extralight" ? "font-normal" : "font-semibold";
  if (!out) {
    const m = c.match(/^rounded(-(?:t|r|b|l|tl|tr|br|bl|s|e))?(?:-(sm|md|2xl|3xl|\[[^\]]+\]))?$/);
    if (m && (m[2] !== undefined || true) && RADIUS[m[2] ?? ""] && !(m[2] === undefined && false)) out = `rounded${m[1] ?? ""}-${RADIUS[m[2] ?? ""]}`;
  }
  if (!out) out = SHADOW[c];
  if (!out) {
    const m = c.match(/^(bg|text|border(?:-[trblxy])?|ring|outline|decoration|divide|accent|fill|stroke|placeholder)-(\[[^\]]+\])(\/\d+)?$/);
    if (m && COLOUR[m[2]]) out = `${m[1]}-${COLOUR[m[2]]}${m[3] ?? ""}`;
  }
  return out ? bang + out : cls;
}

function rewriteClassList(text, dedupe) {
  const tokens = text.split(/(\s+)/);
  const wide = tokens.some((t) => split(t)[1] === "type-wide");
  let changed = 0;
  const mapped = tokens.map((t) => {
    if (!t.trim()) return t;
    const [prefix, cls] = split(t);
    const next = mapClass(cls, wide);
    if (next !== cls) changed++;
    return prefix + next;
  });
  if (!dedupe) return [mapped.join(""), changed];
  // "text-display sm:text-display" -> "text-display": a responsive copy of a class already set is noise.
  const plain = new Set(mapped.filter((t) => t.trim() && !split(t)[0]).map((t) => t));
  const kept = [];
  for (const t of mapped) {
    const [prefix, cls] = split(t);
    if (t.trim() && prefix && RESPONSIVE.test(prefix) && plain.has(cls)) { changed++; continue; }
    kept.push(t);
  }
  return [kept.join("").replace(/\s{2,}/g, " "), changed];
}

for (const file of process.argv.slice(2)) {
  const src = fs.readFileSync(file, "utf8");
  let total = 0;
  // Plain strings on one line: map and dedupe. Template literals: map only.
  let out = src.replace(/(["'])((?:(?!\1)[^\n\\])*)\1/g, (whole, q, body) => {
    const [next, n] = rewriteClassList(body, true);
    total += n;
    return q + next + q;
  });
  out = out.replace(/`([^`]*)`/g, (whole, body) => {
    const [next, n] = rewriteClassList(body, false);
    total += n;
    return "`" + next + "`";
  });
  if (out !== src) fs.writeFileSync(file, out);
  if (total) console.log(String(total).padStart(4), file);
}
