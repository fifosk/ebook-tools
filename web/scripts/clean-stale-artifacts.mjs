#!/usr/bin/env node
import { readdir, rm } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const projectRoot = path.resolve(fileURLToPath(new URL('..', import.meta.url)));
const sourceDir = path.join(projectRoot, 'src');
const removedPaths = [];

async function sweep(directory) {
  const entries = await readdir(directory, { withFileTypes: true });
  await Promise.all(
    entries.map(async (entry) => {
      const entryPath = path.join(directory, entry.name);
      if (entry.isDirectory()) {
        await sweep(entryPath);
        return;
      }
      if (entry.isFile() && (entry.name.endsWith('.js') || entry.name.endsWith('.js.map'))) {
        await rm(entryPath, { force: true });
        removedPaths.push(entryPath);
      }
    }),
  );
}

async function main() {
  try {
    await sweep(sourceDir);
    if (removedPaths.length > 0) {
      const relativeDir = path.relative(projectRoot, sourceDir) || '.';
      console.log(
        `[clean] Removed ${removedPaths.length} stale JS artifacts from ${relativeDir}.`,
      );
    }
  } catch (error) {
    if (error && error.code === 'ENOENT') {
      return;
    }
    console.error('[clean] Failed to remove stale JS artifacts.', error);
    process.exitCode = 1;
  }
}

await main();
