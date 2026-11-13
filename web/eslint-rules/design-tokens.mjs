/**
 * Keeps the UI on the design system in DESIGN.md (tokens in src/app/globals.css).
 *
 * Flags, in any string or template literal (class lists live in JSX and in constants):
 * - text sizes other than the five roles: text-display, text-title, text-body, text-label, text-fine
 * - font weights other than font-normal, font-semibold, font-extrabold
 * - corners other than rounded-lg, rounded-xl, rounded-full, rounded-none (any side)
 * - shadows other than shadow-float, shadow-card, shadow-overlay, shadow-none
 * - one-off colours like bg-[#fff] or text-[var(--danger)]: use the theme colour (text-danger)
 * - kraft anywhere but the price tag
 * - Tailwind's palette colours (text-red-600) and dark: variants: use the theme colours; there is no dark mode
 * - <svg> drawn inline: use an icon from components/ui/icons.tsx
 */

const SIDES = "(?:-(?:t|r|b|l|tl|tr|br|bl|s|e|ss|se|es|ee))?";
const BANNED = [
  [/^text-(?:xs|sm|base|lg|[0-9]?xl)$/, "Use a type role: text-display, text-title, text-body, text-label or text-fine."],
  [/^text-\[(?:\d|\.|calc|clamp)/, "Use a type role: text-display, text-title, text-body, text-label or text-fine."],
  [/^font-(?:thin|extralight|light|medium|bold|black|\[)/, "Use one of the three weights: font-normal, font-semibold or font-extrabold."],
  [new RegExp(`^rounded${SIDES}$`), "Name the corner: rounded-lg (controls), rounded-xl (cards, photos) or rounded-full."],
  [new RegExp(`^rounded${SIDES}-(?:xs|sm|md|2xl|3xl|4xl|\\[.*\\])$`), "Use rounded-lg (controls), rounded-xl (cards, photos) or rounded-full."],
  [/^shadow(?:-(?:2xs|xs|sm|md|lg|xl|2xl|inner|\[.*\]))?$/, "Use shadow-float, shadow-card or shadow-overlay."],
  [/^(?:bg|text|border(?:-[trblxy])?|ring|outline|decoration|fill|stroke|from|via|to|divide|accent|placeholder)-(?:slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose)-\d{2,3}(?:\/\d+)?$/, "Use a theme colour (text-danger, text-success, border-line…), not Tailwind's palette."],
  [/^(?:bg|text|border(?:-[trblxy])?|ring|outline|decoration|fill|stroke|from|to)-kraft(?:\/\d+)?$/, "Kraft is the price tag and nothing else (components/ui/price-tag.tsx)."],
  [/^(?:bg|text|border(?:-[trblxy])?|ring|outline|decoration|fill|stroke|divide|accent|caret|from|via|to|placeholder)-\[(?:#|rgb|hsl|var\(--)/, "Use the theme colour instead (for example text-danger or bg-brand-soft)."],
];

// "sm:hover:!text-lg" -> "text-lg"; "aria-[current=page]:text-ink" -> "text-ink".
function bareClass(token) {
  let rest = token;
  for (;;) {
    let depth = 0;
    let cut = -1;
    for (let i = 0; i < rest.length; i++) {
      const c = rest[i];
      if (c === "[" || c === "(") depth++;
      else if (c === "]" || c === ")") depth--;
      else if (c === ":" && depth === 0) { cut = i; break; }
    }
    if (cut < 0) break;
    rest = rest.slice(cut + 1);
  }
  return rest.replace(/^!/, "").replace(/!$/, "");
}

function check(context, node, text) {
  for (const token of text.split(/\s+/)) {
    if (!token) continue;
    if (/(?:^|:)dark:/.test(token)) {
      context.report({ node, message: `"${token}" is a dark-mode class; Tanu has no dark mode.` });
      continue;
    }
    const cls = bareClass(token);
    for (const [pattern, message] of BANNED) {
      if (pattern.test(cls)) {
        context.report({ node, message: `"${token}" is off the design system. ${message}` });
        break;
      }
    }
  }
}

const designTokens = {
  meta: { type: "problem", docs: { description: "Only design-system sizes, weights, corners, shadows, colours and icons." }, schema: [] },
  create(context) {
    return {
      Literal(node) {
        if (typeof node.value === "string") check(context, node, node.value);
      },
      TemplateElement(node) {
        check(context, node, node.value.cooked ?? node.value.raw);
      },
      JSXOpeningElement(node) {
        if (node.name.type === "JSXIdentifier" && node.name.name === "svg") {
          context.report({ node, message: "Draw icons with components/ui/icons.tsx (Lucide), not inline <svg>." });
        }
      },
    };
  },
};

const plugin = { rules: { "design-tokens": designTokens } };
export default plugin;
