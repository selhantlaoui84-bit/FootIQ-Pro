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
const shadowJobStatusProxy = new URL('../pages/api/admin/shadow-prediction-job-status.ts', import.meta.url);
const shadowBacktestingProxy = new URL('../pages/api/admin/shadow-backtesting.ts', import.meta.url);
const promoteProxy = new URL('../pages/api/admin/promote-candidate-model.ts', import.meta.url);
const rollbackProxy = new URL('../pages/api/admin/rollback-production-model.ts', import.meta.url);
const promotionAuditProxy = new URL('../pages/api/admin/model-promotion-audit.ts', import.meta.url);
const hourlyCron = new URL('../pages/api/cron/hourly-refresh.ts', import.meta.url);
const matchFinishedCron = new URL('../pages/api/cron/match-finished-check.ts', import.meta.url);
const adminPage = new URL('../pages/admin.tsx', import.meta.url);
const loginPage = new URL('../pages/login.tsx', import.meta.url);
const protectedRoute = new URL('../components/ProtectedRoute.tsx', import.meta.url);
const authProvider = new URL('../lib/auth.tsx', import.meta.url);
const middleware = new URL('../middleware.ts', import.meta.url);
const apiClient = new URL('../lib/api.ts', import.meta.url);
const dashboardPage = new URL('../pages/dashboard.tsx', import.meta.url);
const matchesPage = new URL('../pages/matches.tsx', import.meta.url);
const performancePage = new URL('../pages/performance.tsx', import.meta.url);
const uiComponents = new URL('../components/ui.tsx', import.meta.url);
const teamAssets = new URL('../lib/team-assets.ts', import.meta.url);
const layoutSourceFile = new URL('../src-layout.tsx', import.meta.url);
const globalStyles = new URL('../styles/globals.css', import.meta.url);
const backendMain = new URL('../../api/main.py', import.meta.url);
const runtimeStore = new URL('../../api/data/runtime_store.py', import.meta.url);

const brokenEncoding = new RegExp('\\u00c3|\\u00c2|\\u00e2\\u20ac|\\ufffd');
const publicAdminKeyName = ['NEXT', 'PUBLIC', 'ADMIN', 'API', 'KEY'].join('_');
const publicAdminKeyPattern = new RegExp(publicAdminKeyName);

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
  assert.match(adminProxySource, /JSON\.stringify\(req\.body\)/);
  assert.match(adminProxySource, /export const proxyAdminRequest = proxyBackendRequest/);
  assert.doesNotMatch(adminProxySource, /footiq-pro-production\.up\.railway\.app/);
  assert.doesNotMatch(adminProxySource, publicAdminKeyPattern);

  const refreshJobStatusSource = await readFile(refreshJobStatusProxy, 'utf8');
  assert.match(refreshJobStatusSource, /\/admin\/refresh-job-status/);
  assert.match(refreshJobStatusSource, /requireAdminKey: true/);
  assert.match(refreshJobStatusSource, /timeoutMs: 10000/);

  const featureStoreJobStatusSource = await readFile(featureStoreJobStatusProxy, 'utf8');
  assert.match(featureStoreJobStatusSource, /\/admin\/feature-store-job-status/);
  assert.match(featureStoreJobStatusSource, /requireAdminKey: true/);
  assert.match(featureStoreJobStatusSource, /timeoutMs: 10000/);

  const shadowJobStatusSource = await readFile(shadowJobStatusProxy, 'utf8');
  assert.match(shadowJobStatusSource, /\/admin\/shadow-prediction-job-status/);
  assert.match(shadowJobStatusSource, /requireAdminKey: true/);
  assert.match(shadowJobStatusSource, /timeoutMs: 10000/);

  const shadowBacktestingSource = await readFile(shadowBacktestingProxy, 'utf8');
  assert.match(shadowBacktestingSource, /\/shadow\/backtesting/);
  assert.match(shadowBacktestingSource, /method: 'GET'/);
  assert.match(shadowBacktestingSource, /requireAdminKey: true/);
  assert.match(shadowBacktestingSource, /timeoutMs: 60000/);

  const promoteProxySource = await readFile(promoteProxy, 'utf8');
  assert.match(promoteProxySource, /\/models\/promote-candidate/);
  assert.match(promoteProxySource, /method: 'POST'/);
  assert.match(promoteProxySource, /requireAdminKey: true/);

  const rollbackProxySource = await readFile(rollbackProxy, 'utf8');
  assert.match(rollbackProxySource, /\/models\/rollback-production/);
  assert.match(rollbackProxySource, /method: 'POST'/);
  assert.match(rollbackProxySource, /requireAdminKey: true/);

  const promotionAuditProxySource = await readFile(promotionAuditProxy, 'utf8');
  assert.match(promotionAuditProxySource, /\/models\/promotion-audit/);
  assert.match(promotionAuditProxySource, /method: 'GET'/);
  assert.match(promotionAuditProxySource, /requireAdminKey: true/);

  const buildFeatureStoreSource = await readFile(buildFeatureStoreProxy, 'utf8');
  assert.match(buildFeatureStoreSource, /\/admin\/build-feature-store/);
  assert.match(buildFeatureStoreSource, /requireAdminKey: true/);
  assert.match(buildFeatureStoreSource, /timeoutMs: 60000/);
  assert.match(buildFeatureStoreSource, /Backend Feature Store build timed out/);

  const trainCandidateSource = await readFile(trainCandidateProxy, 'utf8');
  assert.match(trainCandidateSource, /proxyAdminRequest/);
  assert.match(trainCandidateSource, /\/admin\/train-candidate-model/);
  assert.match(trainCandidateSource, /model_type/);
  assert.match(trainCandidateSource, /modelType/);
  assert.match(trainCandidateSource, /limit/);
  assert.match(trainCandidateSource, /method: 'POST'/);
  assert.match(trainCandidateSource, /timeoutMs: 60000/);
  assert.match(trainCandidateSource, /requireAdminKey: true/);
  assert.doesNotMatch(trainCandidateSource, publicAdminKeyPattern);

  for (const mutationSource of [
    await readFile(refreshDataSyncProxy, 'utf8'),
    await readFile(trainCandidateProxy, 'utf8'),
    await readFile(shadowProxy, 'utf8'),
    buildFeatureStoreSource,
  ]) {
    assert.match(mutationSource, /method: 'POST'/);
    assert.match(mutationSource, /requireAdminKey: true/);
    assert.doesNotMatch(mutationSource, /footiq-pro-production\.up\.railway\.app/);
    assert.doesNotMatch(mutationSource, publicAdminKeyPattern);
  }

  const readProxyFiles = {
    '../pages/api/admin/refresh-status.ts': 15000,
    '../pages/api/admin/alerts.ts': 45000,
    '../pages/api/admin/feature-summary.ts': 15000,
    '../pages/api/admin/feature-quality-report.ts': 15000,
    '../pages/api/admin/learning-feedback.ts': 15000,
    '../pages/api/admin/learning-monitoring.ts': 45000,
    '../pages/api/admin/calibration.ts': 15000,
    '../pages/api/admin/model-versions.ts': 15000,
    '../pages/api/admin/dashboard-summary.ts': 45000,
  };

  for (const [proxyPath, timeoutMs] of Object.entries(readProxyFiles)) {
    const proxySource = await readFile(new URL(proxyPath, import.meta.url), 'utf8');
    assert.match(proxySource, /method: 'GET'/);
    assert.match(proxySource, /requireAdminKey: true/);
    assert.match(proxySource, new RegExp(`timeoutMs: ${timeoutMs}`));
    assert.doesNotMatch(proxySource, /footiq-pro-production\.up\.railway\.app/);
    assert.doesNotMatch(proxySource, publicAdminKeyPattern);
  }

  const modelGovernanceProxySource = await readFile(new URL('../pages/api/admin/model-governance.ts', import.meta.url), 'utf8');
  assert.match(modelGovernanceProxySource, /method: 'GET'/);
  assert.match(modelGovernanceProxySource, /requireAdminKey: true/);
  assert.match(modelGovernanceProxySource, /timeoutMs: 45000/);
  assert.doesNotMatch(modelGovernanceProxySource, /footiq-pro-production\.up\.railway\.app/);
  assert.doesNotMatch(modelGovernanceProxySource, publicAdminKeyPattern);

  const workflowProxySource = await readFile(new URL('../pages/api/admin/workflow-status.ts', import.meta.url), 'utf8');
  assert.match(workflowProxySource, /\/admin\/workflow-status/);
  assert.match(workflowProxySource, /method: 'GET'/);
  assert.match(workflowProxySource, /requireAdminKey: true/);
  assert.match(workflowProxySource, /timeoutMs: 45000/);
  assert.doesNotMatch(workflowProxySource, /footiq-pro-production\.up\.railway\.app/);
  assert.doesNotMatch(workflowProxySource, publicAdminKeyPattern);

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
  assert.match(adminPageSource, /getLearningFeedback/);
  assert.match(adminPageSource, /getLearningMonitoring/);
  assert.match(adminPageSource, /getMlShadowBacktesting/);
  assert.match(adminPageSource, /getCalibrationReport/);
  assert.match(adminPageSource, /getModelVersionsRegistry/);
  assert.match(adminPageSource, /Auto-learning/);
  assert.match(adminPageSource, /Monitoring learning/);
  assert.match(adminPageSource, /Storage versions/);
  assert.match(adminPageSource, /modelVersions\?\.storage/);
  assert.match(adminPageSource, /learningMonitoring\?\.alerts/);
  assert.match(adminPageSource, /Performance par marché/);
  assert.match(adminPageSource, /Erreurs fréquentes/);
  assert.match(adminPageSource, /Recommandations IA/);
  assert.match(adminPageSource, /Impossible de charger \/features\/summary/);
  assert.match(adminPageSource, /displayedFeatureReady/);
  assert.match(adminPageSource, /disabled=\{isTraining \|\| !isAdmin \|\| !effectiveFeatureStoreReady\}/);
  assert.match(adminPageSource, /Version modèle/);
  assert.match(adminPageSource, /Lignes chargées/);
  assert.match(adminPageSource, /Lignes utilisées/);
  assert.match(adminPageSource, /Features utilisées/);
  assert.match(adminPageSource, /Brier score/);
  assert.match(adminPageSource, /Distribution target/);
  assert.match(adminPageSource, /Erreur entraînement/);
  assert.match(adminPageSource, /getShadowPredictionJobStatus/);
  assert.match(adminPageSource, /shadowJobId/);
  assert.match(adminPageSource, /Job shadow/);
  assert.match(adminPageSource, /Backtesting shadow/);
  assert.match(adminPageSource, /Promotion modèle/);
  assert.match(adminPageSource, /Raisons de blocage/);
  assert.match(adminPageSource, /disabled=\{!isAdmin \|\| !promotionAllowed \|\| isPromotingModel\}/);
  assert.match(adminPageSource, /evaluable_predictions/);
  assert.match(adminPageSource, /pending_predictions/);
  assert.match(adminPageSource, /Les prédictions shadow sont générées, mais aucun match n'est encore évaluable/);
  assert.match(adminPageSource, /effectiveNextStep/);
  assert.match(adminPageSource, /train_candidate_model/);
  assert.match(adminPageSource, /registeredCandidateRows >= 30/);
  assert.match(adminPageSource, /candidateModelTrained \? 'generate_shadow_predictions' : 'train_candidate_model'/);
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

  const loginPageSource = await readFile(loginPage, 'utf8');
  assert.doesNotMatch(loginPageSource, brokenEncoding);
  assert.match(loginPageSource, /function safeNextPath/);
  assert.match(loginPageSource, /if \(isSubmitting \|\| isRedirecting\) return/);
  assert.match(loginPageSource, /disabled=\{!authConfigured \|\| isSubmitting \|\| isRedirecting\}/);
  assert.match(loginPageSource, /Connexion\.\.\./);
  assert.match(loginPageSource, /router\.isReady \|\| loading \|\| !isAuthenticated/);
  assert.match(loginPageSource, /void router\.replace\(nextPath\)/);
  assert.doesNotMatch(loginPageSource, /signInWithPassword/);

  const protectedRouteSource = await readFile(protectedRoute, 'utf8');
  assert.doesNotMatch(protectedRouteSource, brokenEncoding);
  assert.match(protectedRouteSource, /if \(loading \|\| !router\.isReady \|\| !requireAuth \|\| isAuthenticated\) return/);
  assert.match(protectedRouteSource, /Accès admin requis/);
  assert.doesNotMatch(protectedRouteSource, /requireAdmin && !isAdmin[\s\S]*\/login/);

  const authSource = await readFile(authProvider, 'utf8');
  assert.match(authSource, /split\(','\)/);
  assert.match(authSource, /email\.trim\(\)\.toLowerCase\(\)/);
  assert.match(authSource, /adminEmails\.includes\(user\.email\.trim\(\)\.toLowerCase\(\)\)/);
  assert.match(authSource, /isLoading/);
  assert.match(authSource, /onAuthStateChange/);
  assert.doesNotMatch(authSource, publicAdminKeyPattern);

  const middlewareSource = await readFile(middleware, 'utf8');
  assert.doesNotMatch(middlewareSource, /NextResponse\.redirect/);

  const apiClientSource = await readFile(apiClient, 'utf8');
  assert.match(apiClientSource, /async function fetchBackendJson/);
  assert.match(apiClientSource, /async function fetchProxyJson/);
  assert.match(apiClientSource, /const url = path\.startsWith\('http'\) \? path : `\$\{API_URL\}\$\{path\}`/);
  assert.match(apiClientSource, /const response = await fetch\(path, \{/);
  assert.match(apiClientSource, /fetchProxyJson<RefreshResponse>\('\/api\/admin\/refresh-status', undefined, 15000\)/);
  assert.match(apiClientSource, /fetchProxyJson<AdminWorkflowStatus>\('\/api\/admin\/workflow-status', undefined, 45000\)/);
  assert.match(apiClientSource, /fetchProxyJson<AdminAlertsReport>\('\/api\/admin\/alerts', undefined, 45000\)/);
  assert.match(apiClientSource, /fetchProxyJson<FeatureSummary>\('\/api\/admin\/feature-summary', undefined, 15000\)/);
  assert.match(apiClientSource, /fetchProxyJson<DatasetQualityReport>\(`\/api\/admin\/feature-quality-report\?limit=\$\{safeLimit\}`, undefined, 15000\)/);
  assert.match(apiClientSource, /fetchProxyJson<ModelGovernanceReport>\('\/api\/admin\/model-governance', undefined, 45000\)/);
  assert.match(apiClientSource, /fetchProxyJson<LearningFeedbackReport>\('\/api\/admin\/learning-feedback', undefined, 15000\)/);
  assert.match(apiClientSource, /fetchProxyJson<LearningMonitoringReport>\('\/api\/admin\/learning-monitoring', undefined, 45000\)/);
  assert.match(apiClientSource, /fetchProxyJson<CalibrationReport>\('\/api\/admin\/calibration', undefined, 15000\)/);
  assert.match(apiClientSource, /fetchProxyJson<ModelVersionsResponse>\('\/api\/admin\/model-versions', undefined, 15000\)/);
  assert.match(apiClientSource, /\/api\/admin\/promote-candidate-model/);
  assert.match(apiClientSource, /\/api\/admin\/rollback-production-model/);
  assert.match(apiClientSource, /\/api\/admin\/model-promotion-audit/);
  assert.match(apiClientSource, /fetchProxyJson<DashboardSummary>\('\/api\/admin\/dashboard-summary', undefined, 45000\)/);
  assert.match(apiClientSource, /\/api\/admin\/shadow-backtesting\?limit=/);
  assert.match(apiClientSource, /fetchProxyJson<RefreshJobStatus>\(`\/api\/admin\/shadow-prediction-job-status/);
  assert.match(apiClientSource, /Impossible de charger \/features\/summary depuis le backend\./);
  assert.doesNotMatch(apiClientSource, /safeFetchJson/);
  assert.doesNotMatch(apiClientSource, /fetchBackendJson<FeatureSummary>\('\/features\/summary'/);
  assert.doesNotMatch(apiClientSource, /fetchBackendJson<RefreshResponse>\('\/admin\/refresh-status'/);
  assert.doesNotMatch(apiClientSource, /fetchBackendJson<AdminWorkflowStatus>\('\/admin\/workflow-status'/);
  assert.doesNotMatch(apiClientSource, /fetchBackendJson<AdminAlertsReport>\('\/admin\/alerts'/);
  assert.doesNotMatch(apiClientSource, /fetchBackendJson<[^>]+>\('\/api\/admin/);
  assert.doesNotMatch(apiClientSource, /footiq-pro-production\.up\.railway\.app\/admin/);
  assert.match(apiClientSource, /\/api\/admin\/train-candidate-model\?model_type=/);
  assert.doesNotMatch(apiClientSource, /return data \?\? mockFeatureSummary/);
  assert.doesNotMatch(apiClientSource, /return data \?\? mockAdminWorkflowStatus/);
  assert.doesNotMatch(apiClientSource, /return data \?\? mockAdminAlertsReport/);
  assert.doesNotMatch(apiClientSource, /return data \?\? mockModelGovernance/);
  assert.doesNotMatch(apiClientSource, /return data \?\? mockLearningFeedbackReport/);
  assert.doesNotMatch(apiClientSource, /return data \?\? mockCalibrationReport/);
  assert.doesNotMatch(apiClientSource, publicAdminKeyPattern);

  const matchesPageSource = await readFile(matchesPage, 'utf8');
  assert.doesNotMatch(matchesPageSource, brokenEncoding);
  assert.match(matchesPageSource, /GetServerSideProps/);
  assert.doesNotMatch(matchesPageSource, /getStaticProps/);
  assert.match(matchesPageSource, /referenceTimestamp/);
  assert.match(matchesPageSource, /isUpcoming\(match, referenceTimestamp\)/);
  assert.match(matchesPageSource, /isPastKickoff\(match, referenceTimestamp\)/);
  assert.doesNotMatch(matchesPageSource, /status === 'FINISHED'[\s\S]{0,120}: !finished/);

  const dashboardPageSource = await readFile(dashboardPage, 'utf8');
  assert.doesNotMatch(dashboardPageSource, brokenEncoding);
  assert.match(dashboardPageSource, /GetServerSideProps/);
  assert.match(dashboardPageSource, /referenceTime/);
  assert.match(dashboardPageSource, /isUpcoming\(match, referenceTimestamp\)/);
  assert.match(dashboardPageSource, /isPastKickoff\(match, referenceTimestamp\)/);
  assert.match(dashboardPageSource, /TeamCrest name=\{prediction\.home_team\} logoUrl=/);
  assert.match(dashboardPageSource, /isUpcomingPrediction\(prediction, referenceTimestamp\)/);
  assert.doesNotMatch(dashboardPageSource, /isUpcomingPrediction\(prediction, referenceDayStart\)/);
  assert.doesNotMatch(dashboardPageSource, /\.filter\(\(match\) => String\(match\.status \?\? ''\)\.toUpperCase\(\) !== 'FINISHED'\)/);

  const performancePageSource = await readFile(performancePage, 'utf8');
  assert.doesNotMatch(performancePageSource, brokenEncoding);
  assert.match(performancePageSource, /buildEffectiveDatasetQuality/);
  assert.match(performancePageSource, /buildEffectiveGovernanceGates/);
  assert.match(performancePageSource, /rows_with_target/);
  assert.match(performancePageSource, /safe_to_train/);
  assert.match(performancePageSource, /learning-feedback/);
  assert.match(performancePageSource, /Feedback moteur et calibration/);
  assert.match(performancePageSource, /Performance par marché/);
  assert.match(performancePageSource, /Fiabilité par niveau de confiance/);
  assert.match(performancePageSource, /getLearningMonitoring/);
  assert.match(performancePageSource, /Promise\.resolve\(fallback\.featureSummary\)/);
  assert.match(performancePageSource, /En attente de résultats/);
  assert.match(performancePageSource, /Données insuffisantes/);
  assert.match(performancePageSource, /shadowHasMetrics/);
  assert.doesNotMatch(performancePageSource, /Précision shadow<\/span>\s*<strong>\{shadowBacktesting\.shadow_accuracy\}%/);

  const uiSource = await readFile(uiComponents, 'utf8');
  assert.doesNotMatch(uiSource, brokenEncoding);
  assert.match(uiSource, /export function TeamLogo/);
  assert.match(uiSource, /onError=\{\(\) => setFailed\(true\)\}/);
  assert.match(uiSource, /export function TeamIdentity/);
  assert.match(uiSource, /export function TeamCrest/);
  assert.match(uiSource, /resolveTeamLogoUrl/);

  const teamAssetsSource = await readFile(teamAssets, 'utf8');
  assert.doesNotMatch(teamAssetsSource, brokenEncoding);
  assert.match(teamAssetsSource, /crests\.football-data\.org/);
  assert.match(teamAssetsSource, /resolveTeamLogoUrl/);
  assert.match(teamAssetsSource, /getTeamInitials/);

  const layoutSource = await readFile(layoutSourceFile, 'utf8');
  assert.doesNotMatch(layoutSource, brokenEncoding);
  assert.match(layoutSource, /href="\/dashboard"[\s\S]*Tableau de bord[\s\S]*<\/Link>/);
  assert.match(layoutSource, /\{ href: '\/matches', label: 'Matchs'/);

  const stylesSource = await readFile(globalStyles, 'utf8');
  assert.match(stylesSource, /\.topbar \{[\s\S]*z-index: 1000/);
  assert.match(stylesSource, /nav a \{[\s\S]*display: inline-flex/);
  assert.match(stylesSource, /\.navButton \{[\s\S]*z-index: 1/);

  const backendSource = await readFile(backendMain, 'utf8');
  assert.match(backendSource, /data_imported = refresh_matches_imported > 0 or repository_matches_count > 0/);
  assert.match(backendSource, /next_step = "build_feature_store"/);
  assert.match(backendSource, /"data_imported": data_imported/);
  assert.match(backendSource, /Backend refresh misconfigured: missing/);
  assert.match(backendSource, /@app\.post\("\/admin\/train-candidate-model"\)/);
  assert.match(backendSource, /def train_candidate_model_admin/);
  assert.match(backendSource, /train_candidate_model\(rows, model_type=safe_model_type\)/);
  assert.match(backendSource, /@app\.post\("\/admin\/generate-shadow-predictions"\)/);
  assert.match(backendSource, /def generate_shadow_predictions_admin/);
  assert.match(backendSource, /generate_shadow_prediction\(match, production_prediction\)/);
  assert.match(backendSource, /save_ml_shadow_predictions\(items\)/);
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

