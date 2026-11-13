// Prints design-token lint findings per file, most first: pnpm exec eslint src -f json | node eslint-rules/report.mjs
let input = "";
process.stdin.on("data", (chunk) => (input += chunk)).on("end", () => {
  const files = JSON.parse(input)
    .map((f) => [f.filePath.split(/[\\/]src[\\/]/).pop(), f.messages.filter((m) => m.ruleId === "tanu/design-tokens").length])
    .filter(([, n]) => n)
    .sort((a, b) => b[1] - a[1]);
  let total = 0;
  for (const [file, n] of files) { total += n; console.log(String(n).padStart(4), file); }
  console.log(`${total} findings in ${files.length} files`);
});
