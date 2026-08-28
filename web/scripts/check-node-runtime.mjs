import { readFileSync } from 'node:fs';
import { pathToFileURL } from 'node:url';

const { engines } = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));

export function checkNodeRuntime(version) {
  const supported = engines.node.split(' || ').map((range) => range.replace('.x', ''));
  if (!supported.includes(version.split('.')[0])) {
    throw new Error(
      `Unsupported Node ${version}. Web gates support ${engines.node}; prefer Node 24. ` +
      'Run nvm install && nvm use at the repository root, or set WEB_NODE_BIN=/path/to/node24/bin for make.'
    );
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  try {
    checkNodeRuntime(process.versions.node);
  } catch (error) {
    console.error(error.message);
    process.exitCode = 1;
  }
}
