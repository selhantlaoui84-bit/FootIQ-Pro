import fs from 'node:fs';
import path from 'node:path';

const root = process.cwd();
const scanTargets = [
  'pages',
  'components',
  'src-layout.tsx',
  'lib/mock-data.ts',
].map((item) => path.join(root, item));

const forbidden = [
  /Model evaluation/,
  /Feature importance/,
  />\s*Storage\s*</,
  />\s*Accuracy\s*</,
  />\s*Count\s*</,
  />\s*Status\s*</,
  />\s*Generated\s*</,
  />\s*Prediction\s*</,
  /A EVITER/,
  /Pr\?diction|mod\?le|g\?n\?r|d\?saccord|\?viter/,
  new RegExp('\\u00c3|\\ufffd'),
];

function collectFiles(target) {
  if (!fs.existsSync(target)) return [];
  const stat = fs.statSync(target);
  if (stat.isFile()) return [target];
  return fs.readdirSync(target, { withFileTypes: true }).flatMap((entry) => {
    const fullPath = path.join(target, entry.name);
    if (entry.isDirectory()) return collectFiles(fullPath);
    if (/\.(tsx|ts)$/.test(entry.name)) return [fullPath];
    return [];
  });
}

const files = scanTargets.flatMap(collectFiles);
const findings = [];

for (const file of files) {
  const rel = path.relative(root, file);
  if (rel.includes(`${path.sep}api${path.sep}`)) continue;
  const text = fs.readFileSync(file, 'utf8');
  const lines = text.split(/\r?\n/);
  lines.forEach((line, index) => {
    if (/^\s*(export\s+)?type\s|^\s*(export\s+)?interface\s|^\s*\w+\??:\s|^\s*import\s|^\s*export function\s/.test(line)) return;
    const likelyVisible = rel.endsWith('mock-data.ts') || rel.endsWith('src-layout.tsx') || line.includes('>') || line.includes('aria-label') || line.includes('placeholder') || line.includes('title=');
    if (!likelyVisible) return;
    for (const pattern of forbidden) {
      if (pattern.test(line)) {
        findings.push(`${rel}:${index + 1}: ${line.trim()}`);
        break;
      }
    }
  });
}

if (findings.length) {
  console.error('Audit français UI échoué. Chaînes à corriger:');
  console.error(findings.slice(0, 80).join('\n'));
  process.exit(1);
}

console.log('Audit français UI OK.');
