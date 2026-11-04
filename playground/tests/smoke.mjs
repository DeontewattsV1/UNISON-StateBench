// Smoke test: serve the built site and load it in headless Chrome.
import http from "node:http"; import fs from "node:fs"; import path from "node:path";
import { execFile } from "node:child_process"; import { promisify } from "node:util";
const root = path.resolve(process.argv[2] || "dist");
const types = { ".html": "text/html", ".js": "text/javascript", ".json": "application/json" };
const srv = http.createServer((req, res) => {
  const p = path.join(root, decodeURIComponent(req.url.split("?")[0]).replace(/\/$/, "/index.html"));
  if (!p.startsWith(root) || !fs.existsSync(p)) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { "content-type": types[path.extname(p)] || "application/octet-stream" }); fs.createReadStream(p).pipe(res);
}).listen(0, async () => {
  const url = `http://127.0.0.1:${srv.address().port}/`;
  const chrome = process.env.CHROME_BIN || "google-chrome";
  let dom = "";
  try {
    ({ stdout: dom } = await promisify(execFile)(chrome, ["--headless=new", "--no-sandbox", "--disable-gpu", "--virtual-time-budget=10000", "--dump-dom", url], { encoding: "utf8", timeout: 60000, maxBuffer: 1 << 24 }));
  } finally { srv.close(); }
  const checks = [/id="chain-status" class="pass">VALID/, /"promoted": true/, /Concept \(illustrative\)/, /Implemented/, /<svg/];
  const failed = checks.filter((r) => !r.test(dom));
  if (failed.length) { console.error("smoke failed:", failed.map(String)); process.exit(1); }
  console.log("smoke ok:", url);
});
