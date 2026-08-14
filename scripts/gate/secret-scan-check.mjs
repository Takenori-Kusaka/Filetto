// 秘匿情報の混入検査の判定部(G-5 基準7)。
//
//   detect-secrets scan --all-files ... | node scripts/gate/secret-scan-check.mjs
//
// **本基準は、標準が「台帳記録による通過を認めない唯一の基準」としています。**
//
// それにもかかわらず、`adapters/python.json` の `secretScan` は空のままでした。
// `adapter.mjs` が空を任意の検査として扱うため、**「実施しません」と出力して
// exit 0 になっていました**(#58 運用上の注意1)。直近100実行で0回落ちたのは、
// 検査が通っていたからではなく、**検査していなかったから**です。
//
// 出力の原則:
//   - 検出0件のときも0件であることを出力する
//   - **入力が空なら落とす。** 道具が動かなかったことを合格として記録しません
//   - 除外したものは理由とともに出力する

import fs from 'node:fs';
import path from 'node:path';
import { ROOT, fail, notice } from './config.mjs';

const POLICY_PATH = path.join(ROOT, 'scripts/gate/secret-scan-policy.json');

if (!fs.existsSync(POLICY_PATH)) {
  fail('scripts/gate/secret-scan-policy.json がありません。方針を書いてください');
  process.exit(1);
}
const policy = JSON.parse(fs.readFileSync(POLICY_PATH, 'utf8'));

const ALLOWED = new Map((policy.allowed ?? []).map((a) => [a.path, a.reason]));

const raw = fs.readFileSync(0, 'utf8').trim();

if (!raw) {
  fail(
    '検査の出力がありません。detect-secrets が動いていない可能性があります。' +
      '空の入力を合格として記録しません'
  );
  process.exit(1);
}

let report;
try {
  report = JSON.parse(raw);
} catch {
  fail('検査の出力を JSON として解釈できませんでした');
  process.exit(1);
}

if (!report.results || typeof report.results !== 'object') {
  fail('検査の出力に results がありません。detect-secrets の形式を確認してください');
  process.exit(1);
}

const detected = [];
const allowed = [];

for (const [file, entries] of Object.entries(report.results)) {
  const rel = file.split(/[\\/]/).join('/');
  for (const e of entries) {
    const row = { file: rel, type: e.type, line: e.line_number };
    if (ALLOWED.has(rel)) allowed.push({ ...row, reason: ALLOWED.get(rel) });
    else detected.push(row);
  }
}

const plugins = (report.plugins_used ?? []).length;
console.log(`検査した規則: ${plugins} 件`);
console.log(`検出したファイル: ${Object.keys(report.results).length} 件`);

if (allowed.length) {
  console.log(`\n理由を添えて除外したもの: ${allowed.length} 件`);
  for (const a of allowed) console.log(`  ${a.file}:${a.line} ${a.type}  ${a.reason}`);
} else {
  console.log('\n理由を添えて除外したもの: 0 件');
}

console.log(`\n秘匿情報の疑い: ${detected.length} 件`);
for (const d of detected) console.log(`  ${d.file}:${d.line} ${d.type}`);

if (detected.length) {
  for (const d of detected) {
    fail(
      `${d.file}:${d.line} 秘匿情報の疑い(${d.type})。` +
        '秘匿情報でない場合は scripts/gate/secret-scan-policy.json の allowed へ、パスと理由を書いてください'
    );
  }
}

notice(`secret-scan: ${plugins} 規則で検査、${detected.length} 件検出、${allowed.length} 件を除外`);
process.exit(detected.length ? 1 : 0);
