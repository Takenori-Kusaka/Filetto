// D-0(意思決定・エスカレーション体制図)の前提条件を検査する。
//
//   node scripts/gate/check-d0.mjs
//
// D-0 は規模によらず必須で、企画承認(G-1)の前提条件です。
// 未承認・期限切れの状態では、G-1 の審議を開始できません。

import fs from 'node:fs';
import path from 'node:path';
import { loadConfig, ROOT, fail, notice, warn } from './config.mjs';

const config = loadConfig();
const D0 = path.join(ROOT, 'docs/D-0-governance.md');

if (config.configured === false) {
  notice('プロセス構成が未設定のため、D-0 の検査は実施しません');
  process.exit(0);
}

if (!fs.existsSync(D0)) {
  fail('docs/D-0-governance.md がありません。templates/00-d0-governance.md を写して作成してください');
  process.exit(1);
}

const text = fs.readFileSync(D0, 'utf8');
const m = text.match(/^---\r?\n([\s\S]*?)\r?\n---/);
if (!m) {
  fail('D-0 に frontmatter がありません');
  process.exit(1);
}

/** 依存パッケージを持たないため、frontmatter は key: value の平坦な形だけを読む */
const fm = {};
for (const line of m[1].split(/\r?\n/)) {
  const kv = line.match(/^([a-z_]+):\s*(.*)$/i);
  if (kv) fm[kv[1]] = kv[2].trim().replace(/^["']|["']$/g, '');
}

const problems = [];
for (const k of ['project_id', 'version', 'approver', 'approved_at', 'approval_scope', 'next_review']) {
  if (!fm[k]) problems.push(`frontmatter の ${k} が空です`);
}

if (fm.next_review) {
  const due = Date.parse(fm.next_review);
  if (Number.isNaN(due)) problems.push(`next_review "${fm.next_review}" を日付として読めません`);
  else if (due < Date.now()) problems.push(`next_review ${fm.next_review} が過ぎています。体制図の見直しを行ってください`);
}

// 本文の表に空欄が残っていないか(| — | や | | を空欄とみなす)
const emptyCells = text
  .split(/\r?\n/)
  .filter((l) => /^\|/.test(l) && /\|\s*(TBD|未定|\?\?\?)\s*\|/i.test(l));
if (emptyCells.length) {
  problems.push(`本文に未記入の欄が ${emptyCells.length} 件あります(TBD / 未定 / ???)`);
}

for (const p of problems) fail(p);
if (problems.length) {
  console.log('');
  console.log('D-0 が承認済みでない状態では、企画承認(G-1)の審議を開始できません');
  process.exit(1);
}

const days = Math.round((Date.parse(fm.next_review) - Date.now()) / 86400000);
if (days < 30) warn(`D-0 の見直し期限まで ${days} 日です`);
notice(`D-0 は承認済みです(承認者: ${fm.approver} / 見直し: ${fm.next_review})`);
