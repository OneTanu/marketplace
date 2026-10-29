import { readdir, readFile } from "node:fs/promises";
import path from "node:path";

import { expect } from "@playwright/test";

import { EMAIL_DIR } from "./slot";

// The E2E API runs in backend/ and writes each email it sends to a file there.
const MAIL_DIR = path.resolve(__dirname, "../../backend", EMAIL_DIR);

/** Undo quoted-printable encoding, which can wrap long links across lines. */
function decodeQuotedPrintable(text: string) {
  return text.replace(/=\r?\n/g, "").replace(/=([0-9A-F]{2})/g, (_, hex) => String.fromCharCode(parseInt(hex, 16)));
}

async function messagesTo(address: string) {
  const files = await readdir(MAIL_DIR).catch(() => []);
  const messages = await Promise.all(files.map((file) => readFile(path.join(MAIL_DIR, file), "utf8")));
  // A file can hold several messages, each starting with its headers.
  return messages
    .flatMap((log) => log.split(/^-{70,}$/m))
    .map(decodeQuotedPrintable)
    .filter((message) => new RegExp(`^To: ${address}$`, "mi").test(message));
}

/** Waits for an email to `address` containing a link that matches `pattern`; returns the link's path. */
export async function linkInEmail(address: string, pattern: RegExp): Promise<string> {
  let link: string | undefined;
  await expect
    .poll(async () => {
      for (const message of await messagesTo(address)) link = message.match(pattern)?.[0] ?? link;
      return link;
    }, { message: `email to ${address} with a link matching ${pattern}` })
    .toBeTruthy();
  return new URL(link!).pathname;
}
