// PR のマージ先が既定ブランチであることを検査する(#95 依頼2)。
//
//   node scripts/gate/pr-base-check.mjs [--base <ref>] [--body-file <path>]
//
// CI では GITHUB_BASE_REF と、環境変数 PR_BODY から読みます。
//
// **積み上げ PR を禁じません。理由の記載を求めます。**
// 積み上げが正当な場面はあります。一方、親が squash マージされると子の持つ
// 親のコミットは既定ブランチのどこにも存在しなくなり、内容が失われることが
// あります(PR #87)。禁じるのではなく、作者が承知していることを残させます。
//
// 記載が無ければ落とします。**警告だけでは、理由の記載を求めたことになりません。**
//
// 出力の原則:
//   - マージ先が既定ブランチのときも、そのことを出力する

import fs from 'node:fs';
import path from 'node:path';
import { ROOT, fail, notice } from './config.mjs';

const args = process.argv.slice(2);
const argOf = (name, fallback) => {
  const i = args.indexOf(name);
  return i >= 0 && args[i + 1] ? args[i + 1] : fallback;
};

const POLICY_PATH = path.join(ROOT, 'scripts/gate/pr-base-policy.json');

if (!fs.existsSync(POLICY_PATH)) {
  fail('scripts/gate/pr-base-policy.json がありません。方針を書いてください');
  process.exit(1);
}

const policy = JSON.parse(fs.readFileSync(POLICY_PATH, 'utf8'));
const DEFAULT_BASE = policy.defaultBase;
const MARKER = policy.justificationMarker;

if (!DEFAULT_BASE || !MARKER) {
  fail('pr-base-policy.json に defaultBase と justificationMarker を書いてください');
  process.exit(1);
}

const base = argOf('--base', process.env.GITHUB_BASE_REF ?? '');

if (!base) {
  fail(
    'マージ先を特定できません。--base か GITHUB_BASE_REF を渡してください。' +
      '特定できないまま通すと、検査を実施していない状態を通過した記録として残ります'
  );
  process.exit(1);
}

const bodyFile = argOf('--body-file', null);
const body = bodyFile ? fs.readFileSync(bodyFile, 'utf8') : (process.env.PR_BODY ?? '');

console.log(`既定ブランチ: ${DEFAULT_BASE}`);
console.log(`この PR のマージ先: ${base}`);

if (base === DEFAULT_BASE) {
  notice(`pr-base-check: マージ先は ${DEFAULT_BASE} です`);
  process.exit(0);
}

// 積み上げ PR。理由の記載を求める
const justification = body
  .split(/\r?\n/)
  .map((l) => l.trim())
  .find((l) => l.startsWith(MARKER));

const reason = justification ? justification.slice(MARKER.length).trim() : '';

if (!reason) {
  fail(
    `マージ先が ${DEFAULT_BASE} ではありません(${base})。積み上げ PR は禁じませんが、理由の記載を求めます。\n` +
      `  PR 本文へ次の形で1行書いてください:\n` +
      `    ${MARKER} <なぜ ${DEFAULT_BASE} ベースにできないか>\n` +
      `  親が squash マージされると、子が持つ親のコミットは ${DEFAULT_BASE} のどこにも存在しなくなります。\n` +
      `  親のマージ後は、必ず本 PR を ${DEFAULT_BASE} へ張り替えてください`
  );
  process.exit(1);
}

console.log(`\n${MARKER} ${reason}`);
console.log(
  `\n親がマージされたら、本 PR を ${DEFAULT_BASE} へ張り替えてください。` +
    `張り替えないままマージすると、内容が ${DEFAULT_BASE} へ到達しません`
);
notice(`pr-base-check: マージ先は ${base} です。理由の記載を確認しました`);
process.exit(0);
