// A stand-in for flashcard-mcp's app server (NDJSON over stdio), for the deck
// client's tests. Methods: echo (returns params), fail (error reply), delay
// ({ms, value}: replies after ms), hang (never replies), exit (quits), pid,
// split (reply sent in two chunks), big ({bytes}: one very long reply line).
// FAKE_DECK_CRASH_ONCE=<file>: the first start (no file yet) creates it and
// dies before ready; later starts boot normally.
import { createInterface } from "node:readline";
import { existsSync, writeFileSync } from "node:fs";

const marker = process.env.FAKE_DECK_CRASH_ONCE;
if (marker && !existsSync(marker)) {
  writeFileSync(marker, "crashed");
  process.stderr.write("boot failure\n");
  process.exit(1);
}

const delayStart = Number(process.env.FAKE_DECK_STARTUP_MS ?? 0);
setTimeout(() => {
  process.stdout.write(JSON.stringify({ ready: true }) + "\n");
  process.stderr.write("noise on stderr that must be drained\n");

  const reply = (obj) => process.stdout.write(JSON.stringify(obj) + "\n");
  createInterface({ input: process.stdin })
    .on("line", (line) => {
      const { id, method, params } = JSON.parse(line);
      if (method === "echo") reply({ id, result: params });
      else if (method === "pid") reply({ id, result: process.pid });
      else if (method === "fail") reply({ id, error: { message: "boom" } });
      else if (method === "delay") setTimeout(() => reply({ id, result: params.value }), params.ms);
      else if (method === "split") {
        const text = JSON.stringify({ id, result: "joined" }) + "\n";
        process.stdout.write(text.slice(0, 7));
        setTimeout(() => process.stdout.write(text.slice(7)), 30);
      } else if (method === "big") reply({ id, result: "x".repeat(params.bytes) });
      else if (method === "exit") process.exit(3);
      // "hang" and anything else: no reply.
    })
    .on("close", () => process.exit(0));
}, delayStart);
