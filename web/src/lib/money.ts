// Money is integer cents everywhere (see AGENTS.md). This only splits and joins strings, so
// a price never passes through floating-point math.

// Whole dollars (commas only as thousands separators), then up to two decimal digits.
const DOLLARS = /^(\d{1,3}(?:,\d{3})+|\d*)(?:\.(\d{0,2}))?$/;

/**
 * Parses what a seller types in a price field ("25", "24.99", "$1,200.5", ".99") into integer
 * cents. Returns null for anything that isn't a non-negative amount with at most two decimals,
 * including a comma used as the decimal mark ("24,99"), so it can't be misread as $2,499.
 */
export function dollarsToCents(input: string): number | null {
  const match = DOLLARS.exec(input.trim().replace(/^\$\s*/, ""));
  if (!match) return null;
  const whole = match[1].replaceAll(",", "");
  const fraction = match[2] ?? "";
  if (whole === "" && fraction === "") return null;
  // Too many digits to be a real price; also keeps the result a safe integer.
  if (whole.length > 9) return null;
  return Number.parseInt(`${whole}${fraction.padEnd(2, "0")}`, 10);
}

/**
 * Formats integer cents for display: 2500 → "$25", 2499 → "$24.99", 120050 → "$1,200.50".
 * The API only sends whole, non-negative cents, so anything else is a bug and throws.
 */
export function centsToDollars(cents: number): string {
  if (!Number.isSafeInteger(cents) || cents < 0) {
    throw new RangeError(`Expected a non-negative whole number of cents, got ${cents}.`);
  }
  const digits = String(cents).padStart(3, "0");
  const whole = digits.slice(0, -2).replace(/\B(?=(\d{3})+$)/g, ",");
  const fraction = digits.slice(-2);
  return fraction === "00" ? `$${whole}` : `$${whole}.${fraction}`;
}
