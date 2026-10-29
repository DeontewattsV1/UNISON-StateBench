import assert from 'node:assert/strict';
import { mkdir, readFile } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { chromium } from 'playwright';

const origin = process.env.BROWSER_TEST_URL || 'http://127.0.0.1:5173';
const artifacts = process.env.BROWSER_ARTIFACTS || path.join(os.tmpdir(), 'unison-guardian-browser');
await mkdir(artifacts, { recursive: true });
const executablePath = process.env.CHROMIUM_EXECUTABLE || (existsSync('/usr/bin/chromium') ? '/usr/bin/chromium' : undefined);
// Browser navigation and Playwright's Node-side API requests must use the same
// inherited egress proxy when checking a remote deployment. Local previews
// remain direct loopback traffic.
const proxyValue = process.env.HTTPS_PROXY || process.env.https_proxy || process.env.HTTP_PROXY || process.env.http_proxy;
const remote = !['localhost', '127.0.0.1', '[::1]'].includes(new URL(origin).hostname);
const proxyURL = remote && proxyValue ? new URL(proxyValue) : null;
const proxy = proxyURL ? {
  server: `${proxyURL.protocol}//${proxyURL.host}`,
  ...(proxyURL.username ? { username: decodeURIComponent(proxyURL.username), password: decodeURIComponent(proxyURL.password) } : {}),
  ...(process.env.NO_PROXY || process.env.no_proxy ? { bypass: process.env.NO_PROXY || process.env.no_proxy } : {}),
} : undefined;
const browser = await chromium.launch({ executablePath, headless: true, args: ['--no-sandbox'], proxy });
const context = await browser.newContext({ viewport: { width: 1536, height: 1024 }, acceptDownloads: true, proxy });
const page = await context.newPage();
const pageErrors = [];
const unexpectedFailures = [];
page.on('pageerror', error => pageErrors.push(error.message));
page.on('response', response => {
  if (response.status() >= 400 && !(response.url().endsWith('/api/analyze') && response.status() === 503)) unexpectedFailures.push(`${response.status()} ${response.url()}`);
});

async function state() { return (await page.request.get(origin + '/api/state')).json(); }
async function workflow() {
  const baseline = page.getByRole('button', { name: 'Run baseline', exact: true });
  await baseline.click();
  await page.waitForFunction(() => document.querySelector('.step--complete'));
  await page.getByRole('button', { name: 'Revoke authority', exact: true }).click();
  await page.waitForFunction(() => [...document.querySelectorAll('button')].find(button => button.textContent === 'Revoke authority')?.disabled);
  await page.getByRole('button', { name: 'Replay queued action', exact: true }).click();
  await page.locator('.check-list').waitFor();
}
async function choose(value) {
  await page.getByLabel('Scenario', { exact: true }).selectOption(value);
  await page.waitForFunction(value => document.querySelector('#scenario')?.value === value && !document.querySelector('#scenario')?.disabled, value);
}
async function noDocumentOverflow() {
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false, 'Document must not overflow horizontally');
}

try {
  await page.goto(origin);
  await page.waitForFunction(() => document.querySelector('#scenario')?.disabled === false);
  assert.match(await page.title(), /UNISON Guardian/);
  assert.equal(await page.locator('vite-error-overlay').count(), 0);
  await page.getByRole('heading', { name: 'Authority, made verifiable.' }).waitFor();
  await noDocumentOverflow();
  await page.screenshot({ path: path.join(artifacts, 'initial-desktop.png'), fullPage: true });

  await workflow();
  await page.getByText('Revocation verified', { exact: true }).waitFor();
  const queued = await state();
  assert.equal(queued.results.verdict, 'PASS');
  assert.equal(queued.stats.protectedActions, 1, 'Stale queued work must not increment the protected-action counter');
  assert.equal(queued.queue[0].status, 'blocked');
  await page.screenshot({ path: path.join(artifacts, 'revocation-pass.png'), fullPage: true });

  const downloadPromise = page.waitForEvent('download');
  await page.getByRole('link', { name: 'Export evidence' }).click();
  const download = await downloadPromise;
  const downloadPath = path.join(artifacts, 'evidence.json');
  await download.saveAs(downloadPath);
  const bundle = JSON.parse(await readFile(downloadPath, 'utf8'));
  assert.equal(bundle.state.runId, queued.runId);
  assert.equal(bundle.state.results.verdict, 'PASS');
  assert.equal(bundle.origin.trusted, false);

  // A separate browser session uses an explicitly mocked model response. No
  // inference request or paid provider call is made by this UI contract test.
  const mockedContext = await browser.newContext({ viewport: { width: 1536, height: 1024 }, proxy });
  const mockedPage = await mockedContext.newPage();
  await mockedPage.route('**/api/health', route => route.fulfill({ json: { meta: { configured: true, model: 'muse-wonder-1.0' } } }));
  await mockedPage.route('**/api/analyze', async route => {
    const current = await (await mockedPage.request.get(origin + '/api/state')).json();
    await route.fulfill({ json: {
      status: 'completed', model: 'muse-wonder-1.0', authority: 'none', evidence: 'CONJECTURE',
      analyzedRunId: current.runId, analyzedRevision: current.revision, requestId: 'mocked-response-for-test',
      proposal: { explanation: 'MOCKED TEST PROPOSAL — never actual Meta.', suggestedGrantIds: ['grant-primary'], uncertainty: 'Mocked transport only.' },
    } });
  });
  await mockedPage.goto(origin);
  await mockedPage.waitForFunction(() => document.querySelector('#scenario')?.disabled === false);
  const beforeProposal = await (await mockedPage.request.get(origin + '/api/state')).json();
  await mockedPage.getByRole('button', { name: /Ask Muse/ }).click();
  await mockedPage.getByRole('button', { name: 'Analyze this sandbox' }).click();
  await mockedPage.getByText('mocked-response-for-test', { exact: true }).waitFor();
  assert.deepEqual(await (await mockedPage.request.get(origin + '/api/state')).json(), beforeProposal, 'A model proposal must not change authority');
  await mockedPage.getByRole('button', { name: 'Run baseline', exact: true }).click();
  await mockedPage.locator('.proposal').waitFor({ state: 'detached' });
  await mockedContext.close();

  await choose('alternate');
  await workflow();
  await page.getByText('Authority still reachable', { exact: true }).waitFor();
  const alternate = await state();
  assert.equal(alternate.results.verdict, 'FAIL');
  assert.ok(alternate.results.residualPaths.some(route => route.includes('service')));
  await page.screenshot({ path: path.join(artifacts, 'alternate-path-fail.png'), fullPage: true });

  await choose('unknown');
  await workflow();
  const unknown = await state();
  assert.equal(unknown.results.verdict, 'UNKNOWN');
  assert.equal(unknown.results.checks.find(check => check.id === 'inventory').status, 'UNKNOWN');

  await page.getByRole('button', { name: 'Evidence ledger', exact: true }).click();
  await page.getByLabel('Search ledger events').fill('queued');
  assert.ok(await page.locator('.event-button').count() > 0);
  await page.locator('.event-button').first().click();
  await page.getByText(/Local event receipt/).waitFor();
  await page.getByRole('button', { name: 'Agent identity', exact: true }).click();
  await page.getByText('Legal owner', { exact: true }).waitFor();
  assert.match(await page.locator('.identity-list').innerText(), /UNKNOWN/);
  await page.getByRole('button', { name: 'How it works', exact: true }).click();
  await page.getByRole('heading', { name: 'From permission to proof.' }).waitFor();
  await page.getByRole('button', { name: 'Authority graph', exact: true }).click();
  await page.getByRole('button', { name: /Ask Muse/ }).click();
  const health = await (await page.request.get(origin + '/api/health')).json();
  if (!health.meta.configured) {
    await page.getByRole('button', { name: 'Analyze this sandbox' }).click();
    await page.getByRole('alert').filter({ hasText: 'META_API_KEY' }).waitFor();
    assert.equal((await state()).results.verdict, 'UNKNOWN');
  }

  await page.setViewportSize({ width: 390, height: 844 });
  await noDocumentOverflow();
  await page.getByRole('button', { name: 'Open navigation' }).click();
  await page.getByRole('button', { name: 'Agent identity', exact: true }).click();
  await page.getByRole('heading', { name: 'Identity without assumptions.' }).waitFor();
  await noDocumentOverflow();
  await page.screenshot({ path: path.join(artifacts, 'mobile-identity.png'), fullPage: true });
  await page.getByRole('button', { name: 'Open navigation' }).click();
  await page.getByRole('button', { name: 'Authority graph', exact: true }).click();
  await page.getByRole('button', { name: 'Reset sandbox', exact: true }).click();
  await page.waitForFunction(() => !document.querySelector('#scenario')?.disabled && [...document.querySelectorAll('button')].find(button => button.textContent === 'Run baseline')?.disabled === false);
  assert.ok(await page.locator('#scenario').evaluate(select => select.getBoundingClientRect().width > 180), 'Mobile scenario selector must remain readable');
  await page.screenshot({ path: path.join(artifacts, 'mobile-graph.png'), fullPage: true });
  await noDocumentOverflow();
  assert.deepEqual(pageErrors, [], 'No browser runtime errors');
  assert.deepEqual(unexpectedFailures, [], 'No unexpected failed resources');
  console.log(JSON.stringify({ result: 'PASS', origin, viewports: ['1536x1024', '390x844'], checks: ['page identity', 'nonblank', 'no framework overlay', 'no page errors', 'queued denial and PASS', 'alternate witness and FAIL', 'incomplete coverage UNKNOWN', 'evidence download', 'ledger receipt', 'identity separation', 'model proposal isolation and invalidation (mocked)', 'mobile navigation', 'no document overflow'], liveMeta: health.meta.configured ? 'Not exercised by automated test to avoid unrequested billing' : 'Not configured; unavailable state verified', artifacts }, null, 2));
} finally { await browser.close(); }
