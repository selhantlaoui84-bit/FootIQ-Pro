import { readFile } from 'node:fs/promises';
import assert from 'node:assert/strict';

const refreshProxy = new URL('../pages/api/admin/refresh-data.ts', import.meta.url);
const diagnosticsProxy = new URL('../pages/api/admin/diagnostics.ts', import.meta.url);
const adminProxyHelper = new URL('../lib/server/admin-proxy.ts', import.meta.url);
const refreshJobStatusProxy = new URL('../pages/api/admin/refresh-job-status.ts', import.meta.url);
const featureStoreJobStatusProxy = new URL('../pages/api/admin/feature-store-job-status.ts', import.meta.url);
const buildFeatureStoreProxy = new URL('../pages/api/admin/build-feature-store.ts', import.meta.url);
const hourlyCron = new URL('../pages/api/cron/hourly-refresh.ts', import.meta.url);
const matchFinishedCron = new URL('../pages/api/cron/match-finished-check.ts', import.meta.url);
const adminPage = new URL('../pages/admin.tsx', import.meta.url);
const apiClient = new URL('../lib/api.ts', import.meta.url);
const backendMain = new URL('../../api/main.py', import.meta.url);
const runtimeStore = new URL('../../api/data/runtime_store.py', import.meta.url);

async function run() {
  const refreshSource = await readFile(refreshProxy, 'utf8');
  assert.match(refreshSource, /process\.env\.ADMIN_API_KEY/);
  assert.match(refreshSource, /status\(500\)\.json\(\{ detail: 'ADMIN_API_KEY missing on Vercel server environment' \}\)/);
  assert.equal(refreshSource.includes(['NEXT', 'PUBLIC', 'ADMIN', 'API', 'KEY'].join('_')), false);

  const diagnosticsSource = await readFile(diagnosticsProxy, 'utf8');
  assert.match(diagnosticsSource, /hasAdminApiKey/);
  assert.match(diagnosticsSource, /hasCronSecret/);
  assert.match(diagnosticsSource, /Boolean\(adminApiKey\)/);
  assert.doesNotMatch(diagnosticsSource, /ADMIN_API_KEY\s*:/);
  assert.doesNotMatch(diagnosticsSource, /adminApiKey\s*:/);
  assert.doesNotMatch(diagnosticsSource, /adminApiKey\s*,/);

  const adminProxySource = await readFile(adminProxyHelper, 'utf8');
  assert.match(adminProxySource, /process\.env\.NEXT_PUBLIC_API_URL/);
  assert.match(adminProxySource, /process\.env\.ADMIN_API_KEY/);
  assert.match(adminProxySource, /NEXT_PUBLIC_API_URL missing on Vercel environment/);
  assert.match(adminProxySource, /ADMIN_API_KEY missing on Vercel server environment/);
  assert.match(adminProxySource, /headers\['X-Admin-Key'\] = adminKey/);
  assert.doesNotMatch(adminProxySource, /NEXT_PUBLIC_ADMIN_API_KEY/);

  const refreshJobStatusSource = await readFile(refreshJobStatusProxy, 'utf8');
  assert.match(refreshJobStatusSource, /\/admin\/refresh-job-status/);
  assert.match(refreshJobStatusSource, /requireAdminKey: true/);
  assert.match(refreshJobStatusSource, /timeoutMs: 10000/);

  const featureStoreJobStatusSource = await readFile(featureStoreJobStatusProxy, 'utf8');
  assert.match(featureStoreJobStatusSource, /\/admin\/feature-store-job-status/);
  assert.match(featureStoreJobStatusSource, /requireAdminKey: true/);
  assert.match(featureStoreJobStatusSource, /timeoutMs: 10000/);

  const buildFeatureStoreSource = await readFile(buildFeatureStoreProxy, 'utf8');
  assert.match(buildFeatureStoreSource, /\/admin\/build-feature-store/);
  assert.match(buildFeatureStoreSource, /requireAdminKey: true/);
  assert.match(buildFeatureStoreSource, /timeoutMs: 60000/);
  assert.match(buildFeatureStoreSource, /Backend Feature Store build timed out/);

  const adminPageSource = await readFile(adminPage, 'utf8');
  assert.match(adminPageSource, /setError\(response\.detail \?\? response\.error \?\? 'Actualisation impossible\.'\)/);
  assert.match(adminPageSource, /\{error && <section className="banner error">\{error\}<\/section>\}/);
  assert.match(adminPageSource, /stableRefreshInfo\?\.storage === 'postgresql' && \(stableRefreshInfo\?\.matches_imported \?\? 0\) > 0/);
  assert.match(adminPageSource, /Données actualisées<\/span><strong>\{dataImported \? 'oui' : 'non'\}/);
  assert.match(adminPageSource, /stableRefreshInfo\?\.storage === 'postgresql'/);
  assert.match(adminPageSource, /Ancien job refresh probablement bloqu/);
  assert.match(adminPageSource, /reason_if_zero_snapshots/);
  assert.match(adminPageSource, /Prédictions générées/);
  assert.match(adminPageSource, /Prédictions sauvegardées/);
  assert.match(adminPageSource, /Les prédictions sont générées mais non sauvegardées en base\./);
  assert.match(adminPageSource, /predictions_source/);
  assert.match(adminPageSource, /getFeatureSummary/);
  assert.match(adminPageSource, /featureSummary\?\.snapshots_count/);
  assert.match(adminPageSource, /featureSummary\?\.with_target_count/);
  assert.match(adminPageSource, /featureSummary\?\.storage === 'postgresql'/);
  assert.match(adminPageSource, /effectiveFeatureStoreReady \? 'oui' : 'non'/);
  assert.match(adminPageSource, /disabled=\{isTraining \|\| !isAdmin \|\| !effectiveFeatureStoreReady\}/);
  assert.match(adminPageSource, /displayedNextStep/);
  assert.match(adminPageSource, /train_candidate_model/);

  const backendSource = await readFile(backendMain, 'utf8');
  assert.match(backendSource, /data_imported = refresh_matches_imported > 0 or repository_matches_count > 0/);
  assert.match(backendSource, /next_step = "build_feature_store"/);
  assert.match(backendSource, /"data_imported": data_imported/);
  assert.match(backendSource, /Backend refresh misconfigured: missing/);
  assert.match(backendSource, /@app\.post\("\/admin\/cron\/hourly-refresh"\)/);
  assert.match(backendSource, /@app\.post\("\/admin\/cron\/match-finished-check"\)/);

  const runtimeSource = await readFile(runtimeStore, 'utf8');
  assert.match(runtimeSource, /JOB_STALE_SECONDS = 15 \* 60/);
  assert.match(runtimeSource, /failed_timeout/);

  for (const cronSource of [await readFile(hourlyCron, 'utf8'), await readFile(matchFinishedCron, 'utf8')]) {
    assert.match(cronSource, /CRON_SECRET missing on Vercel server environment/);
    assert.match(cronSource, /Invalid cron authorization/);
    assert.match(cronSource, /process\.env\.ADMIN_API_KEY/);
    assert.equal(cronSource.includes(['NEXT', 'PUBLIC', 'ADMIN', 'API', 'KEY'].join('_')), false);
  }
}

run()
  .then(() => {
    console.log('admin regression checks passed');
  })
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
