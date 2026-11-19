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
const consoleProblems = [];
const unexpectedFailures = [];
page.on('pageerror', error => pageErrors.push(error.message));
page.on('console', message => {
  if (!['error', 'warning'].includes(message.type())) return;
  // Chromium emits a console network error for the intentionally unavailable
  // model endpoint exercised below; the HTTP contract checks its 503 response.
  if (message.location().url.endsWith('/api/analyze') && /503/.test(message.text())) return;
  consoleProblems.push(`${message.type()}: ${message.text()}`);
});
page.on('response', response => {
  if (response.status() >= 400 && !(response.url().endsWith('/api/analyze') && response.status() === 503)) unexpectedFailures.push(`${response.status()} ${response.url()}`);
});

async function state() { return (await page.request.get(origin + '/api/state')).json(); }
async function hatsState() { return (await page.request.get(origin + '/api/hats')).json(); }
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

async function verifyFreshHatsSessionBootstrap() {
  // A shared /#hats URL starts with no cookie. Delay the classic registry's
  // first response so a parallel HATS request cannot silently create a second
  // browser session whose later Set-Cookie abandons the displayed identities.
  const freshContext = await browser.newContext({ viewport: { width: 1536, height: 1024 }, acceptDownloads: true, proxy });
  const freshPage = await freshContext.newPage();
  let releasedBootstrap = false;
  let stateRequests = 0;
  const earlyHatsRequests = [];
  let completeBootstrap;
  const bootstrapCompleted = new Promise(resolve => { completeBootstrap = resolve; });
  freshPage.on('request', request => {
    if (new URL(request.url()).pathname === '/api/hats' && !releasedBootstrap) earlyHatsRequests.push(request.url());
  });
  await freshPage.route('**/api/state', async route => {
    stateRequests += 1;
    const response = await route.fetch();
    await new Promise(resolve => setTimeout(resolve, 300));
    releasedBootstrap = true;
    await route.fulfill({ response });
    completeBootstrap();
  });
  try {
    const firstHatsResponse = freshPage.waitForResponse(response => new URL(response.url()).pathname === '/api/hats' && response.request().method() === 'GET');
    await freshPage.goto(origin + '/#hats');
    await bootstrapCompleted;
    const firstHats = await (await firstHatsResponse).json();
    assert.equal(stateRequests, 1, 'Fresh HATS navigation establishes one browser session.');
    assert.deepEqual(earlyHatsRequests, [], 'HATS must wait for the initial session response before requesting its registry.');
    await freshPage.waitForFunction(() => document.querySelector('[data-testid="hats-agent-count"]')?.textContent === '1');
    const displayedRootId = await freshPage.getByLabel('Selected agent', { exact: true }).inputValue();
    assert.equal(displayedRootId, firstHats.agents[0].id);
    await freshPage.getByRole('button', { name: 'Spawn child', exact: true }).click();
    await freshPage.waitForFunction(() => document.querySelector('[data-testid="hats-agent-count"]')?.textContent === '2');
    const exported = freshPage.waitForEvent('download');
    await freshPage.getByRole('link', { name: 'Export HATS evidence', exact: true }).click();
    const download = await exported;
    const filename = path.join(artifacts, 'hats-fresh-session-evidence.json');
    await download.saveAs(filename);
    const bundle = JSON.parse(await readFile(filename, 'utf8'));
    assert.equal(bundle.state.runId, firstHats.runId, 'Export must retain the registry initially displayed after bootstrap.');
    assert.ok(bundle.state.agents.some(agent => agent.id === displayedRootId));
    assert.ok(bundle.state.agents.some(agent => agent.parentId === displayedRootId));
    assert.equal(bundle.state.agents.length, 2, 'The displayed root remains authoritative for manual spawning.');
    await freshPage.screenshot({ path: path.join(artifacts, 'hats-fresh-session.png'), fullPage: true });
  } finally { await freshContext.close(); }
}

async function verifyHatsBootstrapRetry() {
  const retryContext = await browser.newContext({ viewport: { width: 390, height: 844 }, proxy });
  const retryPage = await retryContext.newPage();
  let stateRequests = 0;
  let hatsRequests = 0;
  retryPage.on('request', request => { if (new URL(request.url()).pathname === '/api/hats') hatsRequests += 1; });
  await retryPage.route('**/api/state', async route => {
    stateRequests += 1;
    if (stateRequests === 1) return route.fulfill({ status: 503, json: { error: { code: 'TEST_BOOTSTRAP_UNAVAILABLE', message: 'Bootstrap unavailable for regression' } } });
    return route.fulfill({ response: await route.fetch() });
  });
  try {
    await retryPage.goto(origin + '/#hats');
    await retryPage.getByRole('alert').filter({ hasText: 'Bootstrap unavailable for regression' }).waitFor();
    assert.equal(hatsRequests, 0, 'Failed bootstrap cannot mount a competing HATS session client.');
    const exportControl = retryPage.locator('a[download="unison-guardian-hats-evidence.json"]');
    assert.equal(await exportControl.getAttribute('href'), null);
    assert.equal(await exportControl.getAttribute('aria-disabled'), 'true');
    assert.equal(await retryPage.getByRole('button', { name: 'Spawn child', exact: true }).count(), 0);
    await retryPage.getByRole('button', { name: 'Open navigation' }).click();
    await retryPage.getByRole('button', { name: 'Authority graph', exact: true }).click();
    await retryPage.getByRole('button', { name: /Ask Muse/ }).click();
    assert.equal(await retryPage.getByRole('button', { name: 'Analyze this sandbox' }).isDisabled(), true,
      'Local model analysis must also wait for the shared browser session.');
    await retryPage.getByRole('button', { name: 'Open navigation' }).click();
    await retryPage.getByRole('button', { name: 'HATS lab', exact: true }).click();
    await retryPage.screenshot({ path: path.join(artifacts, 'hats-bootstrap-retry-mobile.png'), fullPage: true });
    await retryPage.getByRole('button', { name: 'Retry', exact: true }).click();
    await retryPage.waitForFunction(() => document.querySelector('[data-testid="hats-agent-count"]')?.textContent === '1');
    assert.equal(stateRequests, 2);
    assert.equal(hatsRequests, 1);
    assert.equal(await exportControl.getAttribute('href'), '/api/hats/evidence');
  } finally { await retryContext.close(); }
}

try {
  await verifyFreshHatsSessionBootstrap();
  await verifyHatsBootstrapRetry();
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

  // HATS is a separate synthetic registry. Its guided denials and manual
  // controls must change real server state without touching the original run.
  await page.getByRole('button', { name: 'HATS lab', exact: true }).click();
  assert.equal(new URL(page.url()).hash, '#hats');
  await page.getByRole('button', { name: 'Run HATS demo', exact: true }).waitFor();
  await page.waitForFunction(() => document.querySelector('[data-testid="hats-agent-count"]')?.textContent === '1');
  await page.getByRole('button', { name: 'Run HATS demo', exact: true }).click();
  await page.getByRole('heading', { name: 'Guided demonstration', exact: true }).waitFor();
  assert.equal(await page.getByTestId('hats-action-count').innerText(), '1');
  const guidedHats = await hatsState();
  assert.equal(guidedHats.demo.verdict, 'PASS');
  assert.ok(guidedHats.demo.steps.every(step => step.passed));
  assert.equal(guidedHats.syntheticActions, 1);
  assert.equal(guidedHats.lastDecision.allowed, false);
  assert.equal(guidedHats.analytics.authority, 'none');
  assert.equal(guidedHats.ledgerVerification.valid, true);
  assert.equal((await state()).results.verdict, 'UNKNOWN', 'HATS actions must preserve the original revocation scenario.');
  await noDocumentOverflow();
  await page.screenshot({ path: path.join(artifacts, 'hats-demo-desktop.png'), fullPage: true });

  const hatsDownloadPromise = page.waitForEvent('download');
  await page.getByRole('link', { name: 'Export HATS evidence', exact: true }).click();
  const hatsDownload = await hatsDownloadPromise;
  const hatsDownloadPath = path.join(artifacts, 'hats-evidence.json');
  await hatsDownload.saveAs(hatsDownloadPath);
  const hatsBundle = JSON.parse(await readFile(hatsDownloadPath, 'utf8'));
  assert.equal(hatsBundle.state.runId, guidedHats.runId);
  assert.equal(hatsBundle.state.demo.verdict, 'PASS');
  assert.equal(hatsBundle.origin.trusted, false);
  assert.equal(hatsBundle.origin.signaturesVerified, false);

  await page.getByRole('button', { name: 'Reset HATS lab', exact: true }).click();
  await page.waitForFunction(() => document.querySelector('[data-testid="hats-agent-count"]')?.textContent === '1' && document.querySelector('[data-testid="hats-action-count"]')?.textContent === '0');
  const manualRoot = (await hatsState()).agents[0];
  await page.getByRole('button', { name: 'Spawn child', exact: true }).click();
  await page.waitForFunction(() => document.querySelector('[data-testid="hats-agent-count"]')?.textContent === '2');
  const manualChild = (await hatsState()).agents.find(agent => agent.parentId === manualRoot.id);
  assert.equal(await page.getByLabel('Selected agent', { exact: true }).inputValue(), manualChild.id, 'Newly spawned child becomes the selected agent.');
  await page.getByRole('button', { name: 'Invoke synthetic action', exact: true }).click();
  await page.waitForFunction(() => document.querySelector('[data-testid="hats-action-count"]')?.textContent === '1');
  await page.getByLabel('Selected agent', { exact: true }).selectOption(manualRoot.id);
  await page.getByRole('button', { name: 'Revoke selected agent', exact: true }).click();
  await page.locator('.hats-current-decision').getByText('AUTHORITY_REVOKED', { exact: true }).waitFor();
  await page.getByLabel('Selected agent', { exact: true }).selectOption(manualChild.id);
  await page.getByRole('button', { name: 'Invoke synthetic action', exact: true }).click();
  await page.locator('.hats-current-decision').getByText('ANCESTOR_REVOKED', { exact: true }).waitFor();
  const manualHats = await hatsState();
  assert.equal(manualHats.lastDecision.allowed, false);
  assert.equal(manualHats.syntheticActions, 1);
  await page.getByRole('button', { name: 'Verify HATS', exact: true }).click();
  await page.locator('.hats-verification').waitFor();
  assert.equal((await hatsState()).verification.verdict, 'PASS');
  await page.getByRole('button', { name: 'Authority graph', exact: true }).click();

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
  await page.getByRole('button', { name: 'Open navigation' }).click();
  await page.getByRole('button', { name: 'HATS lab', exact: true }).click();
  await page.waitForFunction(() => document.querySelector('[data-testid="hats-agent-count"]')?.textContent === '2');
  assert.equal(await page.getByTestId('hats-action-count').innerText(), '1');
  await noDocumentOverflow();
  await page.getByRole('button', { name: 'Reset HATS lab', exact: true }).click();
  await page.waitForFunction(() => document.querySelector('[data-testid="hats-agent-count"]')?.textContent === '1');
  await page.getByRole('button', { name: 'Run HATS demo', exact: true }).click();
  await page.getByRole('heading', { name: 'Guided demonstration', exact: true }).waitFor();
  assert.equal(await page.getByTestId('hats-action-count').innerText(), '1');
  assert.equal((await hatsState()).demo.verdict, 'PASS');
  await page.reload();
  await page.getByRole('heading', { name: 'Guided demonstration', exact: true }).waitFor();
  assert.equal(new URL(page.url()).hash, '#hats', 'The shared HATS URL must reopen the lab.');
  assert.equal(await page.getByTestId('hats-action-count').innerText(), '1');
  await noDocumentOverflow();
  await page.screenshot({ path: path.join(artifacts, 'hats-demo-mobile.png'), fullPage: true });
  assert.equal(await page.locator('vite-error-overlay').count(), 0);
  assert.deepEqual(pageErrors, [], 'No browser runtime errors');
  assert.deepEqual(consoleProblems, [], 'No unexplained console warnings or errors');
  assert.deepEqual(unexpectedFailures, [], 'No unexpected failed resources');
  console.log(JSON.stringify({ result: 'PASS', origin, viewports: ['1536x1024', '390x844'], checks: ['page identity', 'nonblank', 'no framework overlay', 'no page errors', 'no unexplained console messages', 'queued denial and PASS', 'alternate witness and FAIL', 'incomplete coverage UNKNOWN', 'evidence download', 'ledger receipt', 'identity separation', 'model proposal isolation and invalidation (mocked)', 'fresh HATS session bootstrap ordering and run continuity', 'HATS bootstrap failure and retry', 'HATS guided boundary assertions', 'HATS manual spawn and ancestor revocation', 'HATS evidence download', 'separate HATS and revocation registries', 'mobile navigation and HATS demo', 'shared HATS URL reload', 'no document overflow'], liveMeta: health.meta.configured ? 'Not exercised by automated test to avoid unrequested billing' : 'Not configured; unavailable state verified', artifacts }, null, 2));
} finally { await browser.close(); }
