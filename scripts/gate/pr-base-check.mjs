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
import { execFileSync } from 'node:child_process';
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

// ---- 本文とマージ先をどこから読むか --------------------------------------
//
// **イベントのペイロードを当てにしません。**
//
// `github.event.pull_request.body` は、そのイベントを起こしたときの本文です。
// 本文を編集しても `pull_request` の既定の types に `edited` が無いため起動せず、
// `gh run rerun` は同じペイロードを再生するため、**編集後の本文は永久に読まれません**。
// 理由を書いても通らない、という状態になります(#119)。
//
// そのため、PR 番号が分かるときは **GitHub API から取り直します**。
// 取り直せないときはイベントの値へ落とし、**どちらを読んだかを必ず出力します**。

export function fetchFromApi(prNumber, exec = execFileSync) {
  try {
    const out = exec('gh', ['pr', 'view', String(prNumber), '--json', 'body,baseRefName'], {
      encoding: 'utf8',
      maxBuffer: 16 * 1024 * 1024,
    });
    const o = JSON.parse(out);
    return { body: o.body ?? '', base: o.baseRefName ?? '', source: 'GitHub API(いまの本文)' };
  } catch (e) {
    return { error: String(e.message).split(String.fromCharCode(10))[0] };
  }
}

const prNumber = argOf('--pr', process.env.PR_NUMBER ?? '');
const bodyFile = argOf('--body-file', null);

let base = argOf('--base', process.env.GITHUB_BASE_REF ?? '');
let body = bodyFile ? fs.readFileSync(bodyFile, 'utf8') : (process.env.PR_BODY ?? '');
let source = bodyFile ? `--body-file ${bodyFile}` : 'イベントのペイロード';

if (prNumber && !bodyFile) {
  const api = fetchFromApi(prNumber);
  if (api.error) {
    console.log(`GitHub API から取り直せませんでした(${api.error})。イベントの値を使います`);
  } else {
    body = api.body;
    base = argOf('--base', api.base || base);
    source = api.source;
  }
}

if (!base) {
  fail(
    'マージ先を特定できません。--base か GITHUB_BASE_REF か --pr を渡してください。' +
      '特定できないまま通すと、検査を実施していない状態を通過した記録として残ります'
  );
  process.exit(1);
}

console.log(`既定ブランチ: ${DEFAULT_BASE}`);
console.log(`この PR のマージ先: ${base}`);
console.log(`本文の出所: ${source}`);

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
      `  親のマージ後は、必ず本 PR を ${DEFAULT_BASE} へ張り替えてください。\n` +
      `\n` +
      `  **本文を編集しただけでは CI は起動しません。** pull_request の既定の types に edited が\n` +
      `  含まれないためです(#119)。理由を書いたら、次のどちらかを実行してください。\n` +
      `    gh run rerun --failed <run-id>\n` +
      `    (または新しいコミットを積む)\n` +
      `  再実行では、本検査が GitHub API から「いまの本文」を読み直します`
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
