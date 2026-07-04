// CLI verification harness: runs a challenge's Solution (or Stub with --stub)
// in its pinned env, no HTTP/CSRF involved. Used by the backfill workflow to
// prove every authored solution runs green before commit.
//   npm run -s run-challenge -- <topic>/<slug> [--stub]
import { getChallenge, getEnvRegistry } from "../lib/challenges";
import { runChallenge } from "../lib/runner";

const args = process.argv.slice(2);
const id = args.find((a) => !a.startsWith("--"));
const useStub = args.includes("--stub");

if (!id) {
  console.error("usage: npm run -s run-challenge -- <topic>/<slug> [--stub]");
  process.exit(2);
}

const detail = await getChallenge(id);
if (!detail) {
  console.error(`challenge not found: ${id}`);
  process.exit(2);
}

const envs = await getEnvRegistry();
const env = envs[detail.meta.env];
if (!env) {
  console.error(`env not in registry: ${detail.meta.env}`);
  process.exit(2);
}

if (env.type === "browser") {
  console.log(JSON.stringify({ browser: true, note: "renders client-side; verify visually" }));
  process.exit(0);
}

const blocks = useStub ? detail.stub : detail.solution;
const result = await runChallenge(detail, env, blocks.map((b) => b.code).join("\n"));
console.log(JSON.stringify(result, null, 2));
process.exit(result.exitCode === 0 && !result.timedOut ? 0 : 1);
