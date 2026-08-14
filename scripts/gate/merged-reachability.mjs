// マージ済み PR の内容が既定ブランチへ到達しているかを検査する(#95 依頼3)。
//
//   node scripts/gate/merged-reachability.mjs [--limit 300] [--json <path>]
//
// GitHub の「MERGED」表示は、既定ブランチへ到達したことを意味しません。
// マージ先が既定ブランチでない PR は、親が squash マージされた時点で
// 親ブランチへ入るだけになり、**内容がどこにも残らないことがあります**。
// 実際に PR #87 がこれで失われ、PR #94 として出し直しました。
//
// 判定は「マージコミットが既定ブランチの祖先か」で行います。
//
// ブランチ先端では判定できません。squash マージは新しい commit を作るため、
// **正常にマージされた PR でもブランチ先端は既定ブランチの祖先になりません。**
// 先端で判定すると、ほぼ全件が未到達と出ます(実測: 64件中63件)。
//
// 出力の原則:
//   - 対象が0件のときは、0件であることを出力する
//   - 到達済みも件数を出す。未到達だけを出すと「何件見たのか」が残らない

import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { ROOT, fail, notice } from './config.mjs';

const args = process.argv.slice(2);
const argOf = (name, fallback) => {
  const i = args.indexOf(name);
  return i >= 0 && args[i + 1] ? args[i + 1] : fallback;
};

const LIMIT = argOf('--limit', '300');
const JSON_OUT = argOf('--json', null);

const POLICY_PATH = path.join(ROOT, 'scripts/gate/pr-base-policy.json');
const policy = fs.existsSync(POLICY_PATH) ? JSON.parse(fs.readFileSync(POLICY_PATH, 'utf8')) : {};
const DEFAULT_BASE = policy.defaultBase ?? 'main';

function run(cmd, argv) {
  return execFileSync(cmd, argv, { cwd: ROOT, encoding: 'utf8', maxBuffer: 64 * 1024 * 1024 });
}

/** 既定ブランチの参照を決める。CI では origin/<base>、手元でも同じものを使う。
 *  --base-ref は判定の基準を差し替えます。テストが履歴の取得の深さに依存しないためのものです */
function resolveBaseRef() {
  const override = argOf('--base-ref', null);
  for (const ref of override ? [override] : [`origin/${DEFAULT_BASE}`, DEFAULT_BASE]) {
    try {
      run('git', ['rev-parse', '--verify', '--quiet', `${ref}^{commit}`]);
      return ref;
    } catch {
      /* 次を試す */
    }
  }
  return null;
}

function isAncestor(sha, ref) {
  try {
    run('git', ['merge-base', '--is-ancestor', sha, ref]);
    return true;
  } catch {
    return false;
  }
}

function hasCommit(sha) {
  try {
    run('git', ['cat-file', '-e', `${sha}^{commit}`]);
    return true;
  } catch {
    return false;
  }
}

// ---- 実行 ----------------------------------------------------------------

const baseRef = resolveBaseRef();
if (!baseRef) {
  fail(`既定ブランチ ${DEFAULT_BASE} が見つかりません。fetch-depth: 0 で取得してください`);
  process.exit(1);
}

// --pr-json は取得済みの一覧を読みます。テストが gh に依存しないためのものです
const PR_JSON = argOf('--pr-json', null);

let prs;
try {
  prs = PR_JSON
    ? JSON.parse(fs.readFileSync(path.isAbsolute(PR_JSON) ? PR_JSON : path.join(ROOT, PR_JSON), 'utf8'))
    : JSON.parse(
        run('gh', [
          'pr', 'list',
          '--state', 'merged',
          '--limit', LIMIT,
          '--json', 'number,title,baseRefName,headRefName,mergedAt,mergeCommit',
        ])
      );
} catch (e) {
  fail(`マージ済み PR の一覧を取得できませんでした: ${e.message}`);
  process.exit(1);
}
if (!Array.isArray(prs)) {
  fail('マージ済み PR の一覧が配列ではありません');
  process.exit(1);
}

// 内容が別経路で到達済みと確認できた PR。件数と理由を必ず出力します
const RESOLVED = new Map((policy.resolved ?? []).map((r) => [r.pr, r]));

const reached = [];
const unreached = [];
const resolved = [];
const unknown = [];
const nonDefaultBase = [];

for (const pr of prs) {
  const sha = pr.mergeCommit?.oid;
  const row = {
    number: pr.number,
    title: pr.title,
    base: pr.baseRefName,
    head: pr.headRefName,
    mergedAt: pr.mergedAt,
    mergeCommit: sha ?? null,
  };

  if (pr.baseRefName !== DEFAULT_BASE) nonDefaultBase.push(row);

  if (!sha) {
    unknown.push({ ...row, reason: 'マージコミットが取得できません' });
    continue;
  }
  if (!hasCommit(sha)) {
    unknown.push({ ...row, reason: '手元にコミットがありません(履歴の取得が浅い可能性)' });
    continue;
  }
  if (isAncestor(sha, baseRef)) reached.push(row);
  else if (RESOLVED.has(pr.number)) resolved.push({ ...row, ...RESOLVED.get(pr.number) });
  else unreached.push(row);
}

// 既に到達している PR が resolved に残っていたら、方針が古くなった証拠として落とす
const staleResolved = [...RESOLVED.keys()].filter(
  (n) => !resolved.some((r) => r.number === n) && prs.some((p) => p.number === n)
);

console.log(`既定ブランチ: ${DEFAULT_BASE}(参照 ${baseRef})`);
console.log(`検査したマージ済み PR: ${prs.length} 件`);
console.log(`到達している: ${reached.length} 件`);

console.log(`\nマージ先が ${DEFAULT_BASE} でない PR: ${nonDefaultBase.length} 件`);
for (const r of nonDefaultBase) console.log(`  #${r.number} base=${r.base}  ${r.title}`);

console.log(`\n別経路で到達済みと確認した PR: ${resolved.length} 件`);
for (const r of resolved) console.log(`  #${r.number} ${r.resolvedBy}  ${r.reason}`);

console.log(`\n到達を判定できなかった PR: ${unknown.length} 件`);
for (const r of unknown) console.log(`  #${r.number} ${r.reason}  ${r.title}`);

console.log(`\n到達していない PR: ${unreached.length} 件`);
for (const r of unreached) {
  console.log(`  #${r.number} base=${r.base} head=${r.head} merge=${r.mergeCommit?.slice(0, 8)}  ${r.title}`);
}

if (JSON_OUT) {
  const out = path.isAbsolute(JSON_OUT) ? JSON_OUT : path.join(ROOT, JSON_OUT);
  fs.mkdirSync(path.dirname(out), { recursive: true });
  fs.writeFileSync(
    out,
    JSON.stringify(
      {
        defaultBase: DEFAULT_BASE,
        checked: prs.length,
        reached: reached.length,
        resolved,
        unreached,
        unknown,
        nonDefaultBase,
      },
      null,
      2
    ) + '\n'
  );
  console.log(`\n記録: ${path.relative(ROOT, out)}`);
}

if (unreached.length) {
  for (const r of unreached) {
    fail(`PR #${r.number} は MERGED ですが ${DEFAULT_BASE} へ到達していません(base=${r.base})`);
  }
}
if (unknown.length) {
  for (const r of unknown) fail(`PR #${r.number} の到達を判定できませんでした: ${r.reason}`);
}
for (const n of staleResolved) {
  fail(
    `PR #${n} は ${DEFAULT_BASE} へ到達しています。pr-base-policy.json の resolved から外してください。` +
      '到達済みのものを例外に残すと、以後の未到達を見落とします'
  );
}

notice(
  `merged-reachability: ${prs.length} 件を検査、到達 ${reached.length} 件、` +
    `別経路で到達済み ${resolved.length} 件、未到達 ${unreached.length} 件、判定不能 ${unknown.length} 件`
);

process.exit(unreached.length || unknown.length || staleResolved.length ? 1 : 0);
