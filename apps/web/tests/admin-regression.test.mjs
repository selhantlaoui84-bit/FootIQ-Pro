import { readFile } from 'node:fs/promises';
import assert from 'node:assert/strict';

const refreshProxy = new URL('../pages/api/admin/refresh-data.ts', import.meta.url);
const diagnosticsProxy = new URL('../pages/api/admin/diagnostics.ts', import.meta.url);
const adminPage = new URL('../pages/admin.tsx', import.meta.url);
const backendMain = new URL('../../api/main.py', import.meta.url);

async function run() {
  const refreshSource = await readFile(refreshProxy, 'utf8');
  assert.match(refreshSource, /process\.env\.ADMIN_API_KEY/);
  assert.match(refreshSource, /status\(500\)\.json\(\{ detail: 'ADMIN_API_KEY missing on Vercel server environment' \}\)/);
  assert.equal(refreshSource.includes(['NEXT', 'PUBLIC', 'ADMIN', 'API', 'KEY'].join('_')), false);

  const diagnosticsSource = await readFile(diagnosticsProxy, 'utf8');
  assert.match(diagnosticsSource, /hasAdminApiKey/);
  assert.match(diagnosticsSource, /Boolean\(adminApiKey\)/);
  assert.doesNotMatch(diagnosticsSource, /ADMIN_API_KEY\s*:/);
  assert.doesNotMatch(diagnosticsSource, /adminApiKey\s*:/);
  assert.doesNotMatch(diagnosticsSource, /adminApiKey\s*,/);

  const adminPageSource = await readFile(adminPage, 'utf8');
  assert.match(adminPageSource, /setError\(response\.detail \?\? response\.error \?\? 'Actualisation impossible\.'\)/);
  assert.match(adminPageSource, /\{error && <section className="banner error">\{error\}<\/section>\}/);
  assert.match(adminPageSource, /refreshInfo\?\.storage === 'postgresql' && \(refreshInfo\?\.matches_imported \?\? 0\) > 0/);
  assert.match(adminPageSource, /Données actualisées<\/span><strong>\{dataImported \? 'oui' : 'non'\}/);

  const backendSource = await readFile(backendMain, 'utf8');
  assert.match(backendSource, /data_imported = refresh_storage == "postgresql" and refresh_matches_imported > 0/);
  assert.match(backendSource, /next_step = "build_feature_store"/);
  assert.match(backendSource, /"data_imported": data_imported/);
}

run()
  .then(() => {
    console.log('admin regression checks passed');
  })
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
