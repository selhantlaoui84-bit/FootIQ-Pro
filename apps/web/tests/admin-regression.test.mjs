import { readFile } from 'node:fs/promises';
import assert from 'node:assert/strict';

const refreshProxy = new URL('../pages/api/admin/refresh-data.ts', import.meta.url);
const diagnosticsProxy = new URL('../pages/api/admin/diagnostics.ts', import.meta.url);
const adminProxyHelper = new URL('../lib/server/admin-proxy.ts', import.meta.url);
const refreshJobStatusProxy = new URL('../pages/api/admin/refresh-job-status.ts', import.meta.url);
const featureStoreJobStatusProxy = new URL('../pages/api/admin/feature-store-job-status.ts', import.meta.url);
const buildFeatureStoreProxy = new URL('../pages/api/admin/build-feature-store.ts', import.meta.url);
const refreshDataSyncProxy = new URL('../pages/api/admin/refresh-data-sync.ts', import.meta.url);
const trainCandidateProxy = new URL('../pages/api/admin/train-candidate-model.ts', import.meta.url);
const shadowProxy = new URL('../pages/api/admin/generate-shadow-predictions.ts', import.meta.url);
const hourlyCron = new URL('../pages/api/cron/hourly-refresh.ts', import.meta.url);
const matchFinishedCron = new URL('../pages/api/cron/match-finished-check.ts', import.meta.url);
const adminPage = new URL('../pages/admin.tsx', import.meta.url);
const apiClient = new URL('../lib/api.ts', import.meta.url);
const backendMain = new URL('../../api/main.py', import.meta.url);
const runtimeStore = new URL('../../api/data/runtime_store.py', import.meta.url);

const brokenEncoding = new RegExp('\\u00c3|\\u00c2|\\u00e2\\u20ac|\\ufffd');

async function run() {
  const refreshSource = await readFile(refreshProxy, 'utf8');
  assert.match(refreshSource, /process\.env\.ADMIN_API_KEY/);
  assert.match(refreshSource, /ADMIN_API_KEY missing on Vercel server environment/);
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
  assert.doesNotMatch(adminProxySource, /footiq-pro-production\.up\.railway\.app/);
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

  for (const mutationSource of [
    await readFile(refreshDataSyncProxy, 'utf8'),
    await readFile(trainCandidateProxy, 'utf8'),
    await readFile(shadowProxy, 'utf8'),
    buildFeatureStoreSource,
  ]) {
    assert.match(mutationSource, /method: 'POST'/);
    assert.match(mutationSource, /requireAdminKey: true/);
    assert.doesNotMatch(mutationSource, /footiq-pro-production\.up\.railway\.app/);
    assert.doesNotMatch(mutationSource, /NEXT_PUBLIC_ADMIN_API_KEY/);
  }

  const readProxyFiles = [
    '../pages/api/admin/refresh-status.ts',
    '../pages/api/admin/workflow-status.ts',
    '../pages/api/admin/alerts.ts',
    '../pages/api/admin/feature-summary.ts',
    '../pages/api/admin/feature-quality-report.ts',
    '../pages/api/admin/model-governance.ts',
    '../pages/api/admin/dashboard-summary.ts',
  ];

  for (const proxyPath of readProxyFiles) {
    const proxySource = await readFile(new URL(proxyPath, import.meta.url), 'utf8');
    assert.match(proxySource, /method: 'GET'/);
    assert.match(proxySource, /requireAdminKey: true/);
    assert.match(proxySource, /timeoutMs: 15000/);
    assert.doesNotMatch(proxySource, /footiq-pro-production\.up\.railway\.app/);
    assert.doesNotMatch(proxySource, /NEXT_PUBLIC_ADMIN_API_KEY/);
  }

  const adminPageSource = await readFile(adminPage, 'utf8');
  assert.doesNotMatch(adminPageSource, brokenEncoding);
  assert.match(adminPageSource, /setError\(response\.detail \?\? response\.error \?\? 'Actualisation impossible\.'\)/);
  assert.match(adminPageSource, /\{error && <section className="banner error">\{error\}<\/section>\}/);
  assert.match(adminPageSource, /resolvedRefreshStorage === 'postgresql'/);
  assert.match(adminPageSource, /refreshMatchesImported > 0/);
  assert.match(adminPageSource, /Données actualisées<\/span><strong>\{dataImported \? 'oui' : 'non'\}/);
  assert.match(adminPageSource, /stableRefreshInfo\?\.storage === 'postgresql'/);
  assert.match(adminPageSource, /Ancien job refresh probablement bloqué/);
  assert.match(adminPageSource, /reason_if_zero_snapshots/);
  assert.match(adminPageSource, /Prédictions générées/);
  assert.match(adminPageSource, /Prédictions sauvegardées/);
  assert.match(adminPageSource, /Les prédictions sont générées mais non sauvegardées en base\./);
  assert.match(adminPageSource, /predictions_source/);
  assert.match(adminPageSource, /getFeatureSummary/);
  assert.match(adminPageSource, /featureSummary\?\.snapshots_count/);
  assert.match(adminPageSource, /featureSummary\?\.with_target_count/);
  assert.match(adminPageSource, /featureSummary\?\.storage === 'postgresql'/);
  assert.match(adminPageSource, /featureSummaryError/);
  assert.match(adminPageSource, /adminLoadErrors/);
  assert.match(adminPageSource, /Erreurs de chargement API admin/);
  assert.match(adminPageSource, /Impossible de charger \/features\/summary/);
  assert.match(adminPageSource, /displayedFeatureReady/);
  assert.match(adminPageSource, /disabled=\{isTraining \|\| !isAdmin \|\| !effectiveFeatureStoreReady\}/);
  assert.match(adminPageSource, /effectiveNextStep/);
  assert.match(adminPageSource, /train_candidate_model/);
  assert.match(adminPageSource, /workflowStatus\?\.candidate_model\?\.trained \? 'generate_shadow_predictions' : 'train_candidate_model'/);
  assert.match(adminPageSource, /setRefreshJobId\(null\)/);
  assert.match(adminPageSource, /if \(isProbablyStale\(job\)\)/);
  assert.match(adminPageSource, /setRefreshJobId\(response\.job_id\)/);
  assert.match(adminPageSource, /setRefreshJob\(runningJob\(response\.job_id\)\)/);
  assert.doesNotMatch(adminPageSource, /setRefreshJobId\(response\.job_id\);\s*await Promise\.all\(\[reloadAdminState\(\), handleDiagnostics\(\)\]\)/);
  assert.match(adminPageSource, /effectiveFeatureStorage/);
  assert.match(adminPageSource, /effectivePipelineStorage/);
  assert.match(adminPageSource, /displayedPipelineStorage/);
  assert.match(adminPageSource, /displayedFeatureStorage/);
  assert.match(adminPageSource, /Stockage Feature Store <strong>\{displayedFeatureStorage\}/);
  assert.match(adminPageSource, /Snapshots disponibles <strong>\{displayedFeatureSnapshots\}/);
  assert.match(adminPageSource, /Lignes entraînables <strong>\{displayedTrainingRows\}/);
  assert.match(adminPageSource, /Nouveaux snapshots créés/);
  assert.match(adminPageSource, /Nouveaux snapshots sauvegardés/);
  assert.match(adminPageSource, /Aucun nouveau snapshot créé : le Feature Store contient déjà des snapshots disponibles\./);
  assert.doesNotMatch(adminPageSource, /<span>Snapshots créés <strong>\{featureBuildInfo\.feature_snapshots_built/);

  const apiClientSource = await readFile(apiClient, 'utf8');
  assert.match(apiClientSource, /async function fetchBackendJson/);
  assert.match(apiClientSource, /async function fetchProxyJson/);
  assert.match(apiClientSource, /const url = path\.startsWith\('http'\) \? path : `\$\{API_URL\}\$\{path\}`/);
  assert.match(apiClientSource, /const response = await fetch\(path, \{/);
  assert.match(apiClientSource, /fetchProxyJson<RefreshResponse>\('\/api\/admin\/refresh-status', undefined, 15000\)/);
  assert.match(apiClientSource, /fetchProxyJson<AdminWorkflowStatus>\('\/api\/admin\/workflow-status', undefined, 15000\)/);
  assert.match(apiClientSource, /fetchProxyJson<AdminAlertsReport>\('\/api\/admin\/alerts', undefined, 15000\)/);
  assert.match(apiClientSource, /fetchProxyJson<FeatureSummary>\('\/api\/admin\/feature-summary', undefined, 15000\)/);
  assert.match(apiClientSource, /fetchProxyJson<DatasetQualityReport>\(`\/api\/admin\/feature-quality-report\?limit=\$\{safeLimit\}`, undefined, 15000\)/);
  assert.match(apiClientSource, /fetchProxyJson<ModelGovernanceReport>\('\/api\/admin\/model-governance', undefined, 15000\)/);
  assert.match(apiClientSource, /fetchProxyJson<DashboardSummary>\('\/api\/admin\/dashboard-summary', undefined, 15000\)/);
  assert.match(apiClientSource, /Impossible de charger \/features\/summary depuis le backend\./);
  assert.doesNotMatch(apiClientSource, /safeFetchJson/);
  assert.doesNotMatch(apiClientSource, /fetchBackendJson<FeatureSummary>\('\/features\/summary'/);
  assert.doesNotMatch(apiClientSource, /fetchBackendJson<RefreshResponse>\('\/admin\/refresh-status'/);
  assert.doesNotMatch(apiClientSource, /fetchBackendJson<AdminWorkflowStatus>\('\/admin\/workflow-status'/);
  assert.doesNotMatch(apiClientSource, /fetchBackendJson<AdminAlertsReport>\('\/admin\/alerts'/);
  assert.doesNotMatch(apiClientSource, /fetchBackendJson<[^>]+>\('\/api\/admin/);
  assert.doesNotMatch(apiClientSource, /footiq-pro-production\.up\.railway\.app\/admin/);
  assert.doesNotMatch(apiClientSource, /return data \?\? mockFeatureSummary/);
  assert.doesNotMatch(apiClientSource, /return data \?\? mockAdminWorkflowStatus/);
  assert.doesNotMatch(apiClientSource, /return data \?\? mockAdminAlertsReport/);
  assert.doesNotMatch(apiClientSource, /return data \?\? mockModelGovernance/);
  assert.doesNotMatch(apiClientSource, /NEXT_PUBLIC_ADMIN_API_KEY/);

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

