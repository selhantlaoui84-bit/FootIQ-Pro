import assert from 'node:assert/strict';

const baseUrl = (process.env.FOOTIQ_SMOKE_BASE_URL || 'https://foot-iq-pro-ten.vercel.app').replace(/\/$/, '');
const brokenEncodingPattern = new RegExp('\\u00c3|\\u00c2|\\u00e2\\u20ac|\\ufffd');
const routes = [
  '/',
  '/dashboard',
  '/matches',
  '/predictions',
  '/teams',
  '/performance',
  '/login',
  '/register',
  '/profile',
  '/admin',
  '/cgu',
  '/confidentialite',
  '/mentions-legales',
];

async function fetchWithTimeout(url, timeoutMs = 15000) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  try {
    return await fetch(url, { signal: controller.signal, redirect: 'follow' });
  } finally {
    clearTimeout(timeout);
  }
}

async function checkPage(route) {
  const response = await fetchWithTimeout(`${baseUrl}${route}`);
  assert.equal(response.ok, true, `${route} returned HTTP ${response.status}`);
  const html = await response.text();
  assert.equal(brokenEncodingPattern.test(html), false, `${route} contains broken UTF-8 text`);
  assert.equal(/Unhandled Runtime Error|Application error|ChunkLoadError/i.test(html), false, `${route} contains a runtime error marker`);
}

async function checkAdminFeatureSummary() {
  const response = await fetchWithTimeout(`${baseUrl}/api/admin/feature-summary`, 20000);
  assert.equal(response.ok, true, `/api/admin/feature-summary returned HTTP ${response.status}`);
  const data = await response.json();
  assert.equal(data.storage, 'postgresql', 'feature summary storage should be postgresql');
  assert.equal(Number(data.snapshots_count) > 0, true, 'feature summary snapshots_count should be > 0');
  assert.equal(Number(data.with_target_count) > 0, true, 'feature summary with_target_count should be > 0');
}

async function run() {
  for (const route of routes) {
    await checkPage(route);
  }

  if (process.env.FOOTIQ_SMOKE_ADMIN === '1') {
    await checkAdminFeatureSummary();
  }

  console.log(`smoke checks passed for ${baseUrl}`);
}

run().catch((error) => {
  console.error(error);
  process.exit(1);
});

