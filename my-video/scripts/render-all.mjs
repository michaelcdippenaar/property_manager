#!/usr/bin/env node
/**
 * Batch-render property listing videos.
 *
 * Usage:
 *   node scripts/render-all.mjs                              # uses data/properties.sample.json → vertical
 *   node scripts/render-all.mjs data/my-properties.json      # custom data file
 *   node scripts/render-all.mjs data/my-properties.json landscape   # 16:9
 *
 * Output: out/listing-<slug>.mp4
 */
import { spawnSync } from "node:child_process";
import { readFileSync, mkdirSync, writeFileSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const projectRoot = resolve(__dirname, "..");

const dataPath = resolve(
  projectRoot,
  process.argv[2] ?? "data/properties.sample.json",
);
const mode = process.argv[3] ?? "vertical";
const compositionId =
  mode === "landscape" ? "PropertyListingLandscape" : "PropertyListing";

const properties = JSON.parse(readFileSync(dataPath, "utf8"));
if (!Array.isArray(properties)) {
  throw new Error(`${dataPath} must contain a JSON array of properties`);
}

const outDir = resolve(projectRoot, "out");
mkdirSync(outDir, { recursive: true });
const tmpDir = resolve(projectRoot, ".tmp-props");
mkdirSync(tmpDir, { recursive: true });

console.log(
  `Rendering ${properties.length} ${mode} video(s) from ${dataPath}…\n`,
);

let ok = 0;
let fail = 0;

for (const [i, prop] of properties.entries()) {
  const slug = (prop.address ?? `listing-${i}`)
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
  const propsFile = resolve(tmpDir, `${slug}.json`);
  const outFile = resolve(outDir, `listing-${slug}${mode === "landscape" ? "-16x9" : ""}.mp4`);

  writeFileSync(propsFile, JSON.stringify(prop));

  console.log(`[${i + 1}/${properties.length}] ${slug} → ${outFile}`);
  const res = spawnSync(
    "npx",
    [
      "remotion",
      "render",
      "src/index.ts",
      compositionId,
      outFile,
      `--props=${propsFile}`,
      "--log=error",
    ],
    { cwd: projectRoot, stdio: "inherit" },
  );
  if (res.status === 0) {
    ok++;
  } else {
    fail++;
    console.error(`  ✗ failed (exit ${res.status})`);
  }
}

console.log(`\nDone. ${ok} succeeded, ${fail} failed. Output: ${outDir}`);
process.exit(fail > 0 ? 1 : 0);
