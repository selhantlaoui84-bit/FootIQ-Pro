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
const pipelineStatusProxy = new URL('../pages/api/admin/pipeline-status.ts', import.meta.url);
const pipelineJobsProxy = new URL('../pages/api/admin/pipeline-jobs.ts', import.meta.url);
const runPipelineStepProxy = new URL('../pages/api/admin/run-pipeline-step.ts', import.meta.url);
const runHourlyPipelineProxy = new URL('../pages/api/admin/run-hourly-pipeline.ts', import.meta.url);
const runDailyPipelineProxy = new URL('../pages/api/admin/run-daily-pipeline.ts', import.meta.url);
const recomputeCalibrationProxy = new URL('../pages/api/admin/recompute-calibration.ts', import.meta.url);
const activateCalibrationProxy = new URL('../pages/api/admin/activate-calibration.ts', import.meta.url);
const assistantPredictionsProxy = new URL('../pages/api/assistant/predictions.ts', import.meta.url);
const assistantMatchProxy = new URL('../pages/api/assistant/match/[id].ts', import.meta.url);
const assistantDailyBriefProxy = new URL('../pages/api/assistant/daily-brief.ts', import.meta.url);
const oddsMatchProxy = new URL('../pages/api/odds/match/[id].ts', import.meta.url);
const oddsPredictionProxy = new URL('../pages/api/odds/prediction.ts', import.meta.url);
const valueBetsProxy = new URL('../pages/api/value-bets/index.ts', import.meta.url);
const matchValueBetsProxy = new URL('../pages/api/value-bets/match/[id].ts', import.meta.url);
const billingStatusProxy = new URL('../pages/api/billing/status.ts', import.meta.url);
const billingSubscriptionProxy = new URL('../pages/api/billing/subscription.ts', import.meta.url);
const billingCheckoutProxy = new URL('../pages/api/billing/create-checkout-session.ts', import.meta.url);
const billingPortalProxy = new URL('../pages/api/billing/create-portal-session.ts', import.meta.url);
const stripeWebhookProxy = new URL('../pages/api/webhooks/stripe.ts', import.meta.url);
const productionHealthProxy = new URL('../pages/api/system/production-health.ts', import.meta.url);
const superAdminPage = new URL('../pages/super-admin.tsx', import.meta.url);
const superAdminOverviewProxy = new URL('../pages/api/super-admin/overview.ts', import.meta.url);
const superAdminUsersProxy = new URL('../pages/api/super-admin/users/index.ts', import.meta.url);
const superAdminPaymentsProxy = new URL('../pages/api/super-admin/payments.ts', import.meta.url);
const superAdminPlansProxy = new URL('../pages/api/super-admin/plans/index.ts', import.meta.url);
const authMeProxy = new URL('../pages/api/auth/me.ts', import.meta.url);
const onboarding = new URL('../components/OnboardingModal.tsx', import.meta.url);
const hourlyCron = new URL('../pages/api/cron/hourly-refresh.ts', import.meta.url);
const matchFinishedCron = new URL('../pages/api/cron/match-finished-check.ts', import.meta.url);
const dailyLearningCron = new URL('../pages/api/cron/daily-learning.ts', import.meta.url);
const adminPage = new URL('../pages/admin.tsx', import.meta.url);
const loginPage = new URL('../pages/login.tsx', import.meta.url);
const protectedRoute = new URL('../components/ProtectedRoute.tsx', import.meta.url);
const authProvider = new URL('../lib/auth.tsx', import.meta.url);
const middleware = new URL('../middleware.ts', import.meta.url);
const apiClient = new URL('../lib/api.ts', import.meta.url);
const dashboardPage = new URL('../pages/dashboard.tsx', import.meta.url);
const matchesPage = new URL('../pages/matches.tsx', import.meta.url);
const matchDetailPage = new URL('../pages/matches/[id].tsx', import.meta.url);
const predictionsPage = new URL('../pages/predictions.tsx', import.meta.url);
const pricingPage = new URL('../pages/pricing.tsx', import.meta.url);
const profilePage = new URL('../pages/profile.tsx', import.meta.url);
const performancePage = new URL('../pages/performance.tsx', import.meta.url);
const upgradePrompt = new URL('../components/UpgradePrompt.tsx', import.meta.url);
const premiumGate = new URL('../components/PremiumGate.tsx', import.meta.url);
const entitlementGate = new URL('../components/EntitlementGate.tsx', import.meta.url);
const upgradeCard = new URL('../components/UpgradeCard.tsx', import.meta.url);
const entitlementHelpers = new URL('../lib/entitlements.ts', import.meta.url);
const featureAccess = new URL('../lib/feature-access.ts', import.meta.url);
const uiComponents = new URL('../components/ui.tsx', import.meta.url);
const teamAssets = new URL('../lib/team-assets.ts', import.meta.url);
const teamLogos = new URL('../lib/team-logos.ts', import.meta.url);
const teamLogoComponent = new URL('../components/TeamLogo.tsx', import.meta.url);
const teamIdentityComponent = new URL('../components/TeamIdentity.tsx', import.meta.url);
const layoutSourceFile = new URL('../src-layout.tsx', import.meta.url);
const globalStyles = new URL('../styles/globals.css', import.meta.url);
const backendMain = new URL('../../api/main.py', import.meta.url);
const valueBetEngine = new URL('../../api/services/value_bet_engine.py', import.meta.url);
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

  const pipelineProxyChecks = [
    [await readFile(pipelineStatusProxy, 'utf8'), /\/pipeline\/status/, /method: 'GET'/],
    [await readFile(pipelineJobsProxy, 'utf8'), /\/pipeline\/jobs/, /method: 'GET'/],
    [await readFile(runPipelineStepProxy, 'utf8'), /\/pipeline\/run-step/, /method: 'POST'/],
    [await readFile(runHourlyPipelineProxy, 'utf8'), /\/pipeline\/run-hourly/, /method: 'POST'/],
    [await readFile(runDailyPipelineProxy, 'utf8'), /\/pipeline\/run-daily/, /method: 'POST'/],
  ];

  for (const [source, pathPattern, methodPattern] of pipelineProxyChecks) {
    assert.match(source, /proxyAdminRequest/);
    assert.match(source, pathPattern);
    assert.match(source, methodPattern);
    assert.match(source, /requireAdminKey: true/);
    assert.doesNotMatch(source, publicAdminKeyPattern);
    assert.doesNotMatch(source, /footiq-pro-production\.up\.railway\.app/);
  }

  const buildFeatureStoreSource = await readFile(buildFeatureStoreProxy, 'utf8');
  assert.match(buildFeatureStoreSource, /\/admin\/build-feature-store/);
  assert.match(buildFeatureStoreSource, /requireAdminKey: true/);
  assert.match(buildFeatureStoreSource, /timeoutMs: 60000/);
  assert.match(buildFeatureStoreSource, /Backend Feature Store build timed out/);

  const publicProxyChecks = [
    [await readFile(assistantPredictionsProxy, 'utf8'), /\/assistant\/predictions/],
    [await readFile(assistantMatchProxy, 'utf8'), /\/assistant\/match\/\$\{encodeURIComponent\(id\)\}/],
    [await readFile(assistantDailyBriefProxy, 'utf8'), /\/assistant\/daily-brief/],
    [await readFile(oddsMatchProxy, 'utf8'), /\/odds\/match\/\$\{encodeURIComponent\(id\)\}/],
    [await readFile(oddsPredictionProxy, 'utf8'), /\/odds\/prediction/],
    [await readFile(valueBetsProxy, 'utf8'), /\/value-bets/],
    [await readFile(matchValueBetsProxy, 'utf8'), /\/value-bets\/match\/\$\{encodeURIComponent\(id\)\}/],
    [await readFile(billingStatusProxy, 'utf8'), /\/billing\/status/],
    [await readFile(billingSubscriptionProxy, 'utf8'), /\/billing\/subscription/],
  ];

  for (const [source, pathPattern] of publicProxyChecks) {
    assert.match(source, /process\.env\.NEXT_PUBLIC_API_URL/);
    assert.match(source, pathPattern);
    assert.doesNotMatch(source, /process\.env\.ADMIN_API_KEY/);
    assert.doesNotMatch(source, /footiq-pro-production\.up\.railway\.app\/admin/);
    assert.doesNotMatch(source, publicAdminKeyPattern);
  }

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
    await readFile(recomputeCalibrationProxy, 'utf8'),
    await readFile(activateCalibrationProxy, 'utf8'),
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
  assert.match(adminPageSource, /Calibration intelligente/);
  assert.match(adminPageSource, /handleRecomputeCalibration/);
  assert.match(adminPageSource, /handleActivateCalibration/);
  assert.match(adminPageSource, /Recalculer la calibration/);
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
  assert.match(adminPageSource, /Automatisation pipeline/);
  assert.match(adminPageSource, /Lancer pipeline horaire/);
  assert.match(adminPageSource, /Lancer pipeline quotidien/);
  assert.match(adminPageSource, /Réinitialiser les jobs bloqués/);
  assert.match(adminPageSource, /getPipelineStatus/);
  assert.match(adminPageSource, /getPipelineJobs/);
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
  assert.match(protectedRouteSource, /requireSuperAdmin/);
  assert.doesNotMatch(protectedRouteSource, /requireAdmin && !isAdmin[\s\S]*\/login/);

  const authSource = await readFile(authProvider, 'utf8');
  assert.match(authSource, /split\(','\)/);
  assert.match(authSource, /email\.trim\(\)\.toLowerCase\(\)/);
  assert.match(authSource, /getPlatformMe/);
  assert.match(authSource, /role === 'admin' \|\| role === 'super_admin'/);
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
  assert.match(apiClientSource, /\/api\/admin\/recompute-calibration/);
  assert.match(apiClientSource, /\/api\/admin\/activate-calibration/);
  assert.match(apiClientSource, /recomputeCalibration/);
  assert.match(apiClientSource, /activateCalibration/);
  assert.match(apiClientSource, /fetchProxyJson<ModelVersionsResponse>\('\/api\/admin\/model-versions', undefined, 15000\)/);
  assert.match(apiClientSource, /\/api\/admin\/promote-candidate-model/);
  assert.match(apiClientSource, /\/api\/admin\/rollback-production-model/);
  assert.match(apiClientSource, /\/api\/admin\/model-promotion-audit/);
  assert.match(apiClientSource, /fetchProxyJson<DashboardSummary>\('\/api\/admin\/dashboard-summary', undefined, 45000\)/);
  assert.match(apiClientSource, /\/api\/admin\/shadow-backtesting\?limit=/);
  assert.match(apiClientSource, /\/api\/admin\/pipeline-status/);
  assert.match(apiClientSource, /\/api\/admin\/pipeline-jobs/);
  assert.match(apiClientSource, /\/api\/admin\/run-pipeline-step/);
  assert.match(apiClientSource, /\/api\/admin\/run-hourly-pipeline/);
  assert.match(apiClientSource, /\/api\/admin\/run-daily-pipeline/);
  assert.match(apiClientSource, /getAssistantPredictions/);
  assert.match(apiClientSource, /getAssistantMatch/);
  assert.match(apiClientSource, /getAssistantDailyBrief/);
  assert.match(apiClientSource, /getMatchOdds/);
  assert.match(apiClientSource, /getPredictionOdds/);
  assert.match(apiClientSource, /getValueBets/);
  assert.match(apiClientSource, /getMatchValueBets/);
  assert.match(apiClientSource, /getBillingStatus/);
  assert.match(apiClientSource, /getMySubscription/);
  assert.match(apiClientSource, /createCheckoutSession/);
  assert.match(apiClientSource, /createPortalSession/);
  assert.match(apiClientSource, /getProductionHealth/);
  assert.match(apiClientSource, /\/api\/assistant\/predictions/);
  assert.match(apiClientSource, /\/api\/assistant\/match\/\$\{encodeURIComponent\(matchId\)\}/);
  assert.match(apiClientSource, /\/api\/assistant\/daily-brief/);
  assert.match(apiClientSource, /\/api\/odds\/match\/\$\{encodeURIComponent\(matchId\)\}/);
  assert.match(apiClientSource, /\/api\/odds\/prediction/);
  assert.match(apiClientSource, /\/api\/value-bets/);
  assert.match(apiClientSource, /\/api\/value-bets\/match\/\$\{encodeURIComponent\(matchId\)\}/);
  assert.match(apiClientSource, /\/api\/billing\/status/);
  assert.match(apiClientSource, /\/api\/billing\/subscription/);
  assert.match(apiClientSource, /\/api\/billing\/create-checkout-session/);
  assert.match(apiClientSource, /\/api\/billing\/create-portal-session/);
  assert.match(apiClientSource, /\/api\/system\/production-health/);
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
  assert.match(matchesPageSource, /TeamIdentity/);
  assert.match(matchesPageSource, /resolveMatchTeamLogo\(match, 'home'\)/);
  assert.match(matchesPageSource, /resolveMatchTeamLogo\(match, 'away'\)/);
  assert.doesNotMatch(matchesPageSource, /getStaticProps/);
  assert.match(matchesPageSource, /referenceTimestamp/);
  assert.match(matchesPageSource, /isUpcoming\(match, referenceTimestamp\)/);
  assert.match(matchesPageSource, /isPastKickoff\(match, referenceTimestamp\)/);
  assert.doesNotMatch(matchesPageSource, /status === 'FINISHED'[\s\S]{0,120}: !finished/);

  const matchDetailSource = await readFile(matchDetailPage, 'utf8');
  assert.doesNotMatch(matchDetailSource, brokenEncoding);
  assert.match(matchDetailSource, /TeamIdentity/);
  assert.match(matchDetailSource, /resolveMatchTeamLogo/);
  assert.match(matchDetailSource, /Assistant FootIQ/);
  assert.match(matchDetailSource, /getAssistantMatch/);
  assert.match(matchDetailSource, /getStaticProps/);
  assert.match(matchDetailSource, /getStaticPaths/);

  const predictionsPageSource = await readFile(predictionsPage, 'utf8');
  assert.doesNotMatch(predictionsPageSource, brokenEncoding);
  assert.match(predictionsPageSource, /TeamIdentity/);
  assert.match(predictionsPageSource, /resolveMatchTeamLogo\(prediction, 'home'\)/);
  assert.match(predictionsPageSource, /resolveMatchTeamLogo\(prediction, 'away'\)/);
  assert.match(predictionsPageSource, /calibration_version/);
  assert.match(predictionsPageSource, /Probabilités calibrées/);
  assert.match(predictionsPageSource, /Assistant/);
  assert.match(predictionsPageSource, /Cote/);
  assert.match(predictionsPageSource, /Expected value|EV/);
  assert.match(predictionsPageSource, /getAssistantPredictions/);
  assert.match(predictionsPageSource, /UpgradePrompt/);

  const pricingSource = await readFile(pricingPage, 'utf8');
  assert.doesNotMatch(pricingSource, brokenEncoding);
  assert.match(pricingSource, /Pricing/);
  assert.match(pricingSource, /Bientôt disponible/);
  assert.match(pricingSource, /createCheckoutSession/);
  assert.match(apiClientSource, /plan_code/);
  assert.match(apiClientSource, /billing_interval/);

  const profileSource = await readFile(profilePage, 'utf8');
  assert.doesNotMatch(profileSource, brokenEncoding);
  assert.match(profileSource, /Abonnement/);
  assert.match(profileSource, /getMySubscription/);
  assert.match(profileSource, /createPortalSession/);
  assert.match(profileSource, /Gérer l'abonnement|GÃ©rer l'abonnement/);

  const upgradePromptSource = await readFile(upgradePrompt, 'utf8');
  assert.match(upgradePromptSource, /export function UpgradePrompt/);
  assert.match(upgradePromptSource, /\/pricing/);

  const premiumGateSource = await readFile(premiumGate, 'utf8');
  assert.match(premiumGateSource, /export function PremiumGate/);
  assert.match(premiumGateSource, /canAccessFeature/);

  const entitlementGateSource = await readFile(entitlementGate, 'utf8');
  assert.match(entitlementGateSource, /export function EntitlementGate/);
  assert.match(entitlementGateSource, /hasEntitlement/);

  const upgradeCardSource = await readFile(upgradeCard, 'utf8');
  assert.match(upgradeCardSource, /export function UpgradeCard/);
  assert.match(upgradeCardSource, /\/pricing/);

  const entitlementHelperSource = await readFile(entitlementHelpers, 'utf8');
  assert.match(entitlementHelperSource, /requireEntitlement/);
  assert.match(entitlementHelperSource, /value_bets/);

  const featureAccessSource = await readFile(featureAccess, 'utf8');
  assert.match(featureAccessSource, /canViewValueBets/);
  assert.match(featureAccessSource, /getFeatureLimit/);

  const dashboardPageSource = await readFile(dashboardPage, 'utf8');
  assert.doesNotMatch(dashboardPageSource, brokenEncoding);
  assert.match(dashboardPageSource, /GetServerSideProps/);
  assert.match(dashboardPageSource, /referenceTime/);
  assert.match(dashboardPageSource, /isUpcoming\(match, referenceTimestamp\)/);
  assert.match(dashboardPageSource, /isPastKickoff\(match, referenceTimestamp\)/);
  assert.match(dashboardPageSource, /TeamCrest name=\{prediction\.home_team\} logoUrl=/);
  assert.match(dashboardPageSource, /Assistant du jour/);
  assert.match(dashboardPageSource, /getAssistantDailyBrief/);
  assert.match(dashboardPageSource, /Plan actuel|Abonnement/);
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
  assert.match(performancePageSource, /Shadow backtesting|Backtesting shadow/);
  assert.match(performancePageSource, /Comparaison candidat/);
  assert.match(performancePageSource, /Calibration & confiance/);
  assert.match(performancePageSource, /Gouvernance/);
  assert.match(performancePageSource, /Pipeline IA/);
  assert.match(performancePageSource, /Qualité des recommandations/);
  assert.match(performancePageSource, /Analyse value bet/);
  assert.match(performancePageSource, /UpgradePrompt/);
  assert.match(performancePageSource, /getAssistantDailyBrief/);
  assert.match(performancePageSource, /formatMetricWhenAvailable/);
  assert.match(performancePageSource, /invalid_predictions/);
  assert.match(performancePageSource, /production_metrics/);
  assert.match(performancePageSource, /shadowHasMetrics/);
  assert.doesNotMatch(performancePageSource, /Précision shadow<\/span>\s*<strong>\{shadowBacktesting\.shadow_accuracy\}%/);

  assert.match(predictionsPageSource, /Value Bets/);
  assert.match(predictionsPageSource, /Cote réelle non disponible/);

  assert.match(matchDetailSource, /Value bets du match/);

  assert.match(dashboardPageSource, /Opportunités value/);

  const adminPageValueSource = await readFile(adminPage, 'utf8');
  assert.match(adminPageValueSource, /Contrôle value bets/);

  assert.match(adminPageValueSource, /Billing SaaS/);

  const myBetsSource = await readFile(new URL('../pages/my-bets.tsx', import.meta.url), 'utf8');
  assert.match(myBetsSource, /ROI sur paris value/);
  assert.match(myBetsSource, /Limite du plan gratuit|UpgradePrompt/);

  const valueEngineSource = await readFile(valueBetEngine, 'utf8');
  assert.match(valueEngineSource, /def evaluate_value_bet/);

  const uiSource = await readFile(uiComponents, 'utf8');
  assert.doesNotMatch(uiSource, brokenEncoding);
  assert.match(uiSource, /export function TeamLogo/);
  assert.match(uiSource, /onError=\{\(\) => setFailed\(true\)\}/);
  assert.match(uiSource, /export function TeamIdentity/);
  assert.match(uiSource, /export function TeamCrest/);
  assert.match(uiSource, /resolveTeamLogoUrl/);

  const teamAssetsSource = await readFile(teamAssets, 'utf8');
  assert.doesNotMatch(teamAssetsSource, brokenEncoding);
  assert.match(teamAssetsSource, /team-logos/);
  assert.match(teamAssetsSource, /resolveTeamLogoUrl/);
  assert.match(teamAssetsSource, /getTeamInitials/);

  const teamLogosSource = await readFile(teamLogos, 'utf8');
  assert.doesNotMatch(teamLogosSource, brokenEncoding);
  assert.match(teamLogosSource, /crests\.football-data\.org/);
  assert.match(teamLogosSource, /resolveTeamLogo/);
  assert.match(teamLogosSource, /resolveMatchTeamLogo/);
  assert.match(teamLogosSource, /getTeamInitials/);

  const teamLogoSource = await readFile(teamLogoComponent, 'utf8');
  assert.doesNotMatch(teamLogoSource, brokenEncoding);
  assert.match(teamLogoSource, /export function TeamLogo/);
  assert.match(teamLogoSource, /onError=\{\(\) => setFailed\(true\)\}/);
  assert.match(teamLogoSource, /loading=/);

  const teamIdentitySource = await readFile(teamIdentityComponent, 'utf8');
  assert.doesNotMatch(teamIdentitySource, brokenEncoding);
  assert.match(teamIdentitySource, /export function TeamIdentity/);
  assert.match(teamIdentitySource, /TeamLogo/);

  const layoutSource = await readFile(layoutSourceFile, 'utf8');
  assert.doesNotMatch(layoutSource, brokenEncoding);
  assert.match(layoutSource, /href="\/dashboard"[\s\S]*Tableau de bord[\s\S]*<\/Link>/);
  assert.match(layoutSource, /\{ href: '\/matches', label: 'Matchs'/);
  assert.match(layoutSource, /href="\/super-admin"/);
  assert.match(layoutSource, /isSuperAdmin/);

  const superAdminPageSource = await readFile(superAdminPage, 'utf8');
  assert.doesNotMatch(superAdminPageSource, brokenEncoding);
  assert.match(superAdminPageSource, /Super Admin SaaS/);
  assert.match(superAdminPageSource, /samir\.elh@outlook\.fr/);
  assert.match(superAdminPageSource, /requireSuperAdmin/);
  assert.match(superAdminPageSource, /Aucun paiement réel enregistré/);
  assert.match(superAdminPageSource, /Production Health/);

  const superAdminApiSource = await readFile(apiClient, 'utf8');
  assert.match(superAdminApiSource, /getSuperAdminOverview/);
  assert.match(superAdminApiSource, /getSuperAdminUsers/);
  assert.match(superAdminApiSource, /getPayments/);
  assert.match(superAdminApiSource, /\/api\/super-admin\/overview/);
  assert.match(superAdminApiSource, /\/api\/billing\/create-checkout-session/);
  assert.match(superAdminApiSource, /\/api\/billing\/create-portal-session/);

  const checkoutProxySource = await readFile(billingCheckoutProxy, 'utf8');
  assert.match(checkoutProxySource, /requireBearerToken: true/);
  assert.match(checkoutProxySource, /\/billing\/create-checkout-session/);

  const portalProxySource = await readFile(billingPortalProxy, 'utf8');
  assert.match(portalProxySource, /requireBearerToken: true/);
  assert.match(portalProxySource, /\/billing\/create-portal-session/);

  const webhookSource = await readFile(stripeWebhookProxy, 'utf8');
  assert.match(webhookSource, /bodyParser: false/);
  assert.match(webhookSource, /Stripe-Signature/);
  assert.match(webhookSource, /\/billing\/webhook/);
  assert.doesNotMatch(webhookSource, /STRIPE_SECRET_KEY|STRIPE_WEBHOOK_SECRET/);

  const productionHealthSource = await readFile(productionHealthProxy, 'utf8');
  assert.match(productionHealthSource, /\/system\/production-health/);

  for (const proxyFile of [superAdminOverviewProxy, superAdminUsersProxy, superAdminPaymentsProxy, superAdminPlansProxy, authMeProxy]) {
    const proxySource = await readFile(proxyFile, 'utf8');
    assert.match(proxySource, /requireBearerToken: true/);
    assert.doesNotMatch(proxySource, /footiq-pro-production\.up\.railway\.app/);
    assert.doesNotMatch(proxySource, publicAdminKeyPattern);
  }

  const onboardingSource = await readFile(onboarding, 'utf8');
  assert.match(onboardingSource, /completeOnboarding/);
  assert.match(onboardingSource, /localStorage/);
  assert.doesNotMatch(onboardingSource, brokenEncoding);

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

  for (const cronSource of [await readFile(hourlyCron, 'utf8'), await readFile(matchFinishedCron, 'utf8'), await readFile(dailyLearningCron, 'utf8')]) {
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



