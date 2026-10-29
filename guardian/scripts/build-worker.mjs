import { readFile, readdir, writeFile, mkdir } from 'node:fs/promises';
import path from 'node:path';
import { build } from 'esbuild';

const types = { '.html': 'text/html; charset=utf-8', '.css': 'text/css; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.svg': 'image/svg+xml', '.txt': 'text/plain; charset=utf-8' };
const assets = {};
async function visit(dir) {
  for (const entry of await readdir(dir, { withFileTypes: true })) {
    const filename = path.join(dir, entry.name);
    if (entry.isDirectory()) await visit(filename);
    else {
      const type = types[path.extname(entry.name)];
      if (!type) throw new Error(`Unsupported public asset type: ${entry.name}`);
      const key = '/' + path.relative('dist', filename).split(path.sep).join('/');
      assets[key] = { type, text: await readFile(filename, 'utf8') };
    }
  }
}
await visit('dist');
await writeFile('worker/generated-assets.mjs', `export default ${JSON.stringify(assets)};\n`);
await mkdir('.release', { recursive: true });
await build({ entryPoints: ['worker/index.mjs'], outfile: '.release/worker.mjs', bundle: true, format: 'esm', platform: 'neutral', target: 'es2022', minify: true, external: ['node:*', 'cloudflare:*'] });
console.log('Built Cloudflare Worker with explicit dist assets only. No environment files or research inputs are bundled.');
