// 記録の整合を検査する(#145)。
//
//   node scripts/gate/record-integrity.mjs [--issues-json <path>] [--today <YYYY-MM-DD>]
//
// **AI が記録を落としても検出されるようにするためのものです。**
//
// 2026-08-14 の1日で、記録を落とした事例が4件ありました。判定記録の空欄・Issue の
// 閉じ忘れ・承認欄とゲートの取り違え・標準に無い判定値。**いずれも「忘れないように
// する」では解決しません。忘れても検出される仕組みが要ります。**
//
// **記述の実質性を判定しません**(標準 5.7.4)。空欄かどうか、語が一致するかどうか、
// 参照先が存在するかどうかだけを見ます。
//
// 検査:
//   1 判定記録の空欄        判定日時・結果が空欄のまま main にあるもの
//   2 台帳と Issue の整合    台帳が未解決とする行の Issue が閉じている
//   3 承認欄と判定記録の整合  spec が「通過」と書くのに判定記録が無い/結果が空欄
//   4 判定値の語彙          「通過」「差し戻し」以外の語
//   5 期限超過              期限を過ぎた行が未返却のまま
//
// 出力の原則: すべての検査で、0件のときも0件であることを出力します。

import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { ROOT, fail, notice } from './config.mjs';

const args = process.argv.slice(2);
const argOf = (name, fallback) => {
  const i = args.indexOf(name);
  return i >= 0 && args[i + 1] ? args[i + 1] : fallback;
};

const CONFIG_PATH = path.join(ROOT, 'scripts/gate/record-integrity.json');
if (!fs.existsSync(CONFIG_PATH)) {
  fail('scripts/gate/record-integrity.json がありません。検査の対象を書いてください');
  process.exit(1);
}
const config = JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf8'));

const read = (rel) => {
  const p = path.join(ROOT, rel);
  return fs.existsSync(p) ? fs.readFileSync(p, 'utf8') : null;
};

/** Markdown の 2 列表から「項目 → 値」を拾う */
export function fieldsOf(text) {
  const out = new Map();
  for (const line of text.split(/\r?\n/)) {
    const m = line.match(/^\|\s*(.+?)\s*\|\s*(.*?)\s*\|\s*$/);
    if (!m) continue;
    // 3列以上の表の見出し行を拾わないため、値に区切りが残るものは捨てます
    if (m[1].includes('|') || m[2].includes('|')) continue;
    const key = m[1].replace(/\*/g, '').trim();
    const value = m[2].replace(/\*/g, '').trim();
    if (!out.has(key)) out.set(key, value);
  }
  return out;
}

const EMPTY = new Set(config.gateRecords?.emptyValues ?? ['']);
export const isEmpty = (v) => v === undefined || EMPTY.has(v.trim());

const results = [];
const say = (name, items, describe) => {
  console.log(`\n## ${name}: ${items.length} 件`);
  for (const it of items) console.log(`  ${describe(it)}`);
  results.push({ name, count: items.length, items });
};

// ---- 判定記録を読む --------------------------------------------------------

const gr = config.gateRecords ?? {};
const gateDir = path.join(ROOT, gr.dir ?? 'docs/gates');
const recordFiles = fs.existsSync(gateDir)
  ? fs.readdirSync(gateDir).filter((f) => f.endsWith('.md')).sort()
  : [];

const records = [];
const notRecords = [];

for (const f of recordFiles) {
  const rel = `${gr.dir}/${f}`;
  const fields = fieldsOf(read(rel) ?? '');
  const gate = fields.get(gr.gateField ?? 'ゲート');
  const resultField = (gr.resultFields ?? ['結果']).find((k) => fields.has(k));
  // 判定記録かどうかは中身で決めます。パスでは決めません
  if (gate === undefined || resultField === undefined) {
    notRecords.push(rel);
    continue;
  }
  records.push({ rel, fields, gate, resultField, result: fields.get(resultField) });
}

console.log(`判定記録: ${records.length} 件(判定記録でない ${notRecords.length} 件)`);
for (const n of notRecords) console.log(`  判定記録として扱わない: ${n}`);

// ---- 1 判定記録の空欄 ------------------------------------------------------

const blanks = [];
for (const r of records) {
  for (const key of [...(gr.requiredFields ?? []), r.resultField]) {
    if (isEmpty(r.fields.get(key))) blanks.push({ ...r, key });
  }
}
say('検査1 判定記録の空欄', blanks, (b) => `${b.rel} の「${b.key}」が空欄です(ゲート ${b.gate})`);

// ---- 4 判定値の語彙 --------------------------------------------------------

const vocab = config.resultVocabulary ?? [];
const badWords = [];
for (const r of records) {
  if (isEmpty(r.result)) continue;
  const rule = vocab.find((v) => new RegExp(v.gatePattern).test(r.gate));
  if (!rule) {
    badWords.push({ ...r, reason: `ゲート「${r.gate}」に対応する語彙が resultVocabulary にありません` });
    continue;
  }
  const value = r.result.replace(/[()（）].*$/, '').trim();
  if (!rule.allowed.some((a) => value === a || r.result.startsWith(a))) {
    badWords.push({ ...r, reason: `「${r.result}」は ${rule.allowed.join(' / ')} のいずれでもありません` });
  }
}
say('検査4 判定値の語彙', badWords, (b) => `${b.rel} ${b.reason}`);

// ---- 3 承認欄と判定記録の整合 ----------------------------------------------

const sa = config.specApproval ?? {};
const specDir = path.join(ROOT, sa.dir ?? 'specs');
const specs = fs.existsSync(specDir)
  ? fs.readdirSync(specDir, { withFileTypes: true }).filter((e) => e.isDirectory()).map((e) => e.name)
  : [];

const approvalIssues = [];
const heading = new RegExp(sa.headingPattern ?? '^##\\s*承認');
const linkRe = new RegExp(sa.recordLinkPattern ?? '\\(([^)]+\\.md)\\)');

for (const s of specs) {
  const rel = `${sa.dir}/${s}/${sa.file ?? 'spec.md'}`;
  const text = read(rel);
  if (!text) continue;
  const lines = text.split(/\r?\n/);
  let inSection = false;
  lines.forEach((line, i) => {
    if (/^##\s/.test(line)) inSection = heading.test(line);
    if (!inSection) return;
    if (!line.includes(sa.passWord ?? '通過')) return;
    if (!line.startsWith('|')) return;

    const m = line.match(linkRe);
    if (!m) {
      approvalIssues.push({ rel, line: i + 1, reason: '「通過」と書かれていますが、判定記録への参照がありません' });
      return;
    }
    const target = m[1].split('/').pop();
    const rec = records.find((r) => r.rel.endsWith(`/${target}`));
    if (!rec) {
      approvalIssues.push({ rel, line: i + 1, reason: `参照先 ${target} が判定記録として見つかりません` });
      return;
    }
    if (isEmpty(rec.result)) {
      approvalIssues.push({ rel, line: i + 1, reason: `参照先 ${target} の結果欄が空欄です` });
    }
  });
}
say('検査3 承認欄と判定記録の整合', approvalIssues, (a) => `${a.rel}:${a.line} ${a.reason}`);

// ---- 台帳を読む ------------------------------------------------------------

const dl = config.debtLedger ?? {};
const ledgerText = read(dl.file ?? 'docs/debt-ledger.md');
const ledgerRows = [];

if (ledgerText) {
  const rowRe = new RegExp(dl.rowPattern ?? '^\\|\\s*(D-\\d+)\\s*\\|');
  for (const line of ledgerText.split(/\r?\n/)) {
    const m = line.match(rowRe);
    if (!m) continue;
    const cells = line.split('|').map((c) => c.replace(/\*/g, '').trim());
    const issue = line.match(new RegExp(dl.issuePattern ?? 'issues/(\\d+)'));
    ledgerRows.push({
      id: m[1],
      cells,
      status: cells.find((c) => [...(dl.openStatuses ?? []), ...(dl.closedStatuses ?? [])].some((s) => c.startsWith(s))),
      deadline: cells[6],
      issue: issue ? Number(issue[1]) : null,
    });
  }
}
console.log(`\n技術負債台帳: ${ledgerRows.length} 行`);

// ---- 2 台帳と Issue の整合 -------------------------------------------------

const issuesJson = argOf('--issues-json', null);
let issues = null;
try {
  const raw = issuesJson
    ? fs.readFileSync(path.resolve(issuesJson), 'utf8')
    : execFileSync('gh', ['issue', 'list', '--state', 'all', '--limit', '500', '--json', 'number,state'], {
        cwd: ROOT,
        encoding: 'utf8',
        maxBuffer: 32 * 1024 * 1024,
      });
  issues = new Map(JSON.parse(raw).map((i) => [i.number, i.state]));
} catch (e) {
  issues = null;
  console.log(`\n## 検査2 台帳と Issue の整合: 実施できません`);
  console.log(`  Issue の一覧を取得できませんでした(${String(e.message).split(String.fromCharCode(10))[0]})`);
  results.push({ name: '検査2 台帳と Issue の整合', count: 0, skipped: true });
}

if (issues) {
  const mismatched = [];
  const mustOpen = dl.issueMustBeOpen ?? [];
  const mustClosed = dl.issueMustBeClosed ?? [];
  for (const r of ledgerRows) {
    if (!r.issue) {
      mismatched.push({ id: r.id, reason: 'Issue への参照がありません' });
      continue;
    }
    const state = issues.get(r.issue);
    if (state === undefined) {
      mismatched.push({ id: r.id, reason: `Issue #${r.issue} が見つかりません` });
      continue;
    }
    const status = (r.status ?? '').split(/[(（]/)[0];
    if (mustOpen.some((w) => status.startsWith(w)) && state === 'CLOSED') {
      mismatched.push({
        id: r.id,
        reason: `状態が「${status}」(対処していない)ですが Issue #${r.issue} は閉じています。台帳が古いか、Issue を早く閉じました`,
      });
    }
    if (mustClosed.some((w) => status.startsWith(w)) && state === 'OPEN') {
      mismatched.push({
        id: r.id,
        reason: `状態が「${status}」(成果物は main にある)ですが Issue #${r.issue} は開いています。閉じ忘れの疑いがあります`,
      });
    }
  }
  say('検査2 台帳と Issue の整合', mismatched, (m) => `${m.id} ${m.reason}`);
}

// ---- 5 期限超過 ------------------------------------------------------------

const today = argOf('--today', new Date().toISOString().slice(0, 10));
const overdue = [];
const unparsable = [];

for (const r of ledgerRows) {
  const isOpenRow = (dl.openStatuses ?? []).some((s) => (r.status ?? '').startsWith(s));
  if (!isOpenRow) continue;
  const m = (r.deadline ?? '').match(/(\d{4})[-/](\d{2})[-/](\d{2})/);
  if (!m) {
    unparsable.push(r);
    continue;
  }
  const d = `${m[1]}-${m[2]}-${m[3]}`;
  if (d < today) overdue.push({ ...r, date: d });
}

say('検査5 期限超過', overdue, (o) => `${o.id} 期限 ${o.date} を過ぎて「${o.status}」のままです`);
console.log(`\n期限が日付として読めない行: ${unparsable.length} 件`);
for (const u of unparsable) console.log(`  ${u.id} 期限「${u.deadline}」。日付ではないため期限超過を判定していません`);

// ---- まとめ ----------------------------------------------------------------

console.log('');
const failed = results.filter((r) => !r.skipped && r.count > 0);
for (const r of results) {
  console.log(`${r.name}: ${r.skipped ? '実施できません' : `${r.count} 件`}`);
}

for (const b of blanks) fail(`${b.rel} の「${b.key}」が空欄です。判定は成立していません`);
for (const b of badWords) fail(`${b.rel} ${b.reason}`);
for (const a of approvalIssues) fail(`${a.rel}:${a.line} ${a.reason}`);
for (const o of overdue) fail(`${o.id} 期限 ${o.date} を過ぎて「${o.status}」のままです`);
for (const m of results.find((r) => r.name.startsWith('検査2'))?.items ?? []) fail(`${m.id} ${m.reason}`);

notice(
  `record-integrity: 判定記録 ${records.length} 件・台帳 ${ledgerRows.length} 行を検査、` +
    `${failed.reduce((a, b) => a + b.count, 0)} 件検出`
);

process.exit(failed.length ? 1 : 0);
