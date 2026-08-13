// 投入量を測る(#107)。稼働・AI 実行費・成果物の内訳のうち、機械で取れるものを出す。
//
//   node scripts/gate/investment-measure.mjs [--markdown] [--ai-usage <dir>]
//
// 標準 7.7.2 は予算消化率・消化進捗比・AI実行予算の消化率を指標として定めています。
// 本案件はそれを一度も測っていませんでした。**測っていなければ、費用が先行して
// いることに気づく契機がありません。**
//
// 測れるもの:
//   1. マージ済み PR の分類(プロセス / プロダクト / ゲート記録 / 実装コード)
//   2. 実装コード・テスト・検査の装置・文書の行数
//   3. AI の応答数とトークン(--ai-usage を渡したときだけ。§AI 実行費)
//
// 測れないもの:
//   稼働時間。人が台帳へ書きます。
//
// ## AI 実行費について
//
// **Claude Code のセッション記録から取れます。** ただし記録は利用者のマシンの
// `~/.claude/projects/<作業ツリー>/*.jsonl` にあり、**リポジトリにも CI にもありません。**
// そのため CI では取れず、手元で `--ai-usage` を渡したときだけ出します。
//
// 出力の原則:
//   - 0件のときも0件と出す
//   - **分類できないファイルは未分類として出し、失敗させる。** 規則を増やさずに
//     新しい領域が増えると、内訳が実態とずれたまま「測った」記録が残ります

import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { pathToFileURL } from 'node:url';
import { ROOT, fail, notice } from './config.mjs';

const args = process.argv.slice(2);
const argOf = (name, fallback) => {
  const i = args.indexOf(name);
  return i >= 0 && args[i + 1] ? args[i + 1] : fallback;
};
const has = (name) => args.includes(name);

const CONFIG_PATH = path.join(ROOT, 'scripts/gate/investment-classes.json');

if (!fs.existsSync(CONFIG_PATH)) {
  fail('scripts/gate/investment-classes.json がありません。分類規則を書いてください');
  process.exit(1);
}
const config = JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf8'));

/** glob をごく小さな部分集合で照合する(`**` `*` のみ) */
export function globToRegExp(glob) {
  const SPECIAL = '.+^${}()|[]';
  let re = '';
  for (let i = 0; i < glob.length; i++) {
    const c = glob[i];
    if (c === '*') {
      if (glob[i + 1] === '*') {
        if (glob[i + 2] === '/') {
          re += '(?:.*/)?';
          i += 2;
        } else {
          re += '.*';
          i += 1;
        }
      } else {
        re += '[^/]*';
      }
    } else if (c === '\\') {
      re += '\\\\';
    } else if (SPECIAL.includes(c)) {
      re += '\\' + c;
    } else {
      re += c;
    }
  }
  return new RegExp('^' + re + '$');
}

/** ファイルの分類。先に一致した規則を採る。一致しなければ null */
export function classifyFile(file, classes = config.classes) {
  for (const c of classes) {
    for (const p of c.patterns) {
      if (globToRegExp(p).test(file)) return c.id;
    }
  }
  return null;
}

/** PR の分類。変更行数がいちばん多い区分をその PR の区分とする */
export function classifyPr(files, classes = config.classes) {
  const perClass = new Map();
  const unclassified = [];
  for (const f of files) {
    const id = classifyFile(f.path, classes);
    const lines = (f.additions ?? 0) + (f.deletions ?? 0);
    if (!id) {
      unclassified.push(f.path);
      continue;
    }
    perClass.set(id, (perClass.get(id) ?? 0) + lines);
  }
  let top = null;
  let max = -1;
  for (const [id, n] of perClass) {
    if (n > max) {
      max = n;
      top = id;
    }
  }
  return { dominant: top, perClass, unclassified };
}

function run(cmd, argv) {
  return execFileSync(cmd, argv, { cwd: ROOT, encoding: 'utf8', maxBuffer: 128 * 1024 * 1024 });
}

// ---- 1. マージ済み PR の分類 ---------------------------------------------

function measurePrs() {
  let prs;
  try {
    prs = JSON.parse(
      run('gh', ['pr', 'list', '--state', 'merged', '--limit', '500', '--json', 'number,title,mergedAt,files'])
    );
  } catch (e) {
    return { error: `gh pr list に失敗しました: ${e.message}` };
  }

  const byClass = new Map(config.classes.map((c) => [c.id, { prs: 0, lines: 0 }]));
  const unclassified = new Set();
  let noFiles = 0;

  for (const pr of prs) {
    const files = pr.files ?? [];
    if (!files.length) {
      noFiles++;
      continue;
    }
    const r = classifyPr(files);
    for (const u of r.unclassified) unclassified.add(u);
    for (const [id, n] of r.perClass) byClass.get(id).lines += n;
    if (r.dominant) byClass.get(r.dominant).prs += 1;
  }

  return { total: prs.length, byClass, unclassified: [...unclassified], noFiles };
}

// ---- 2. 行数 ---------------------------------------------------------------

function countLines(targets) {
  const out = [];
  for (const t of targets) {
    let files = 0;
    let lines = 0;
    for (const p of t.paths) {
      const root = path.join(ROOT, p);
      if (!fs.existsSync(root)) continue;
      const stack = [root];
      while (stack.length) {
        const dir = stack.pop();
        for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
          const full = path.join(dir, e.name);
          if (e.isDirectory()) {
            stack.push(full);
            continue;
          }
          if (!t.extensions.includes(path.extname(e.name))) continue;
          files++;
          lines += fs.readFileSync(full, 'utf8').split('\n').length;
        }
      }
    }
    out.push({ ...t, files, lines });
  }
  return out;
}

// ---- 3. AI の応答数とトークン ---------------------------------------------

export function measureAiUsage(dir, pattern = config.aiUsage?.worktreePattern) {
  if (!fs.existsSync(dir)) return { error: `${dir} がありません` };
  if (!pattern) return { error: 'investment-classes.json に aiUsage.worktreePattern がありません' };
  const re = new RegExp(pattern);

  const totals = { responses: 0, input: 0, output: 0, cacheRead: 0, cacheCreate: 0 };
  const byModel = new Map();
  const byWorktree = new Map();
  let sessions = 0;

  const worktrees = fs
    .readdirSync(dir, { withFileTypes: true })
    .filter((e) => e.isDirectory())
    .map((e) => e.name)
    .filter((n) => re.test(n));

  if (!worktrees.length) return { error: `${pattern} に一致する作業ツリーがありません` };

  for (const w of worktrees) {
    const wt = { responses: 0, output: 0 };
    for (const f of fs.readdirSync(path.join(dir, w)).filter((x) => x.endsWith('.jsonl'))) {
      sessions++;
      const text = fs.readFileSync(path.join(dir, w, f), 'utf8');
      for (const line of text.split('\n')) {
        if (!line.trim()) continue;
        let o;
        try {
          o = JSON.parse(line);
        } catch {
          continue;
        }
        const u = o?.message?.usage;
        if (!u) continue;
        totals.responses++;
        wt.responses++;
        totals.input += u.input_tokens ?? 0;
        totals.output += u.output_tokens ?? 0;
        wt.output += u.output_tokens ?? 0;
        totals.cacheRead += u.cache_read_input_tokens ?? 0;
        totals.cacheCreate += u.cache_creation_input_tokens ?? 0;
        const m = o.message.model ?? '不明';
        byModel.set(m, (byModel.get(m) ?? 0) + 1);
      }
    }
    byWorktree.set(w, wt);
  }

  return { sessions, worktrees: worktrees.length, totals, byModel, byWorktree };
}

// ---- 実行 ------------------------------------------------------------------
// import されたときは実行しません(テストから分類の関数だけを読み込むため)。

const invokedDirectly = process.argv[1] ? pathToFileURL(process.argv[1]).href === import.meta.url : false;

if (invokedDirectly) {
  const prs = measurePrs();
  const lines = countLines(config.lineCountTargets ?? []);
  const aiDir = argOf('--ai-usage', null);
  const ai = aiDir ? measureAiUsage(path.resolve(aiDir)) : null;

  const md = has('--markdown');
  const out = [];
  const say = (s = '') => out.push(s);

  if (md) {
    say('### 機械で測った値');
    say();
    say('| 区分 | PR件数 | 変更行数 |');
    say('| --- | --- | --- |');
  } else {
    say('## マージ済み PR の分類');
  }

  if (prs.error) {
    fail(prs.error);
  } else {
    for (const c of config.classes) {
      const v = prs.byClass.get(c.id);
      const pct = prs.total ? Math.round((v.prs / prs.total) * 100) : 0;
      if (md) say(`| ${c.label} | ${v.prs}件(${pct}%) | ${v.lines.toLocaleString()}行 |`);
      else say(`  ${c.label.padEnd(8)} ${String(v.prs).padStart(3)}件(${String(pct).padStart(2)}%)  ${v.lines} 行`);
    }
    if (md) say(`| **合計** | **${prs.total}件** | — |`);
    else {
      say(`  合計 ${prs.total} 件`);
      say(`  変更ファイルが取得できなかった PR: ${prs.noFiles} 件`);
    }
  }

  say();
  if (md) {
    say('| 対象 | ファイル数 | 行数 |');
    say('| --- | --- | --- |');
    for (const t of lines) say(`| ${t.label} | ${t.files} | ${t.lines.toLocaleString()} |`);
  } else {
    say('## 行数');
    for (const t of lines) say(`  ${t.label.padEnd(12)} ${String(t.files).padStart(4)} ファイル  ${t.lines} 行`);
  }

  say();
  const k = (n) => n.toLocaleString();
  if (ai && !ai.error) {
    const t = ai.totals;
    if (md) {
      say('| AI の使用量(累計) | 値 |');
      say('| --- | --- |');
      say(`| セッション記録 | ${ai.sessions} ファイル(作業ツリー ${ai.worktrees} 個) |`);
      say(`| 応答数 | ${k(t.responses)} |`);
      say(`| 出力トークン | ${k(t.output)} |`);
      say(`| 入力トークン(キャッシュ外) | ${k(t.input)} |`);
      say(`| キャッシュ読み | ${k(t.cacheRead)} |`);
      say(`| キャッシュ書き | ${k(t.cacheCreate)} |`);
    } else {
      say('## AI の使用量');
      say(`  セッション記録 ${ai.sessions} ファイル(作業ツリー ${ai.worktrees} 個)`);
      say(`  応答 ${k(t.responses)} 件`);
      say(`  出力 ${k(t.output)} / 入力 ${k(t.input)} / キャッシュ読み ${k(t.cacheRead)} / 書き ${k(t.cacheCreate)}`);
      say(`  モデル別: ${[...ai.byModel].map(([m, n]) => `${m}=${n}`).join(', ')}`);
      for (const [w, v] of ai.byWorktree) say(`    ${w}  応答 ${v.responses} 件 / 出力 ${k(v.output)}`);
    }
  } else {
    const msg = ai?.error
      ? `AI の使用量: 取得できません(${ai.error})`
      : 'AI の使用量: 測っていません(--ai-usage <~/.claude/projects> を渡すと測ります)。' +
        'セッション記録は利用者のマシンにあり、リポジトリにも CI にもありません';
    say(md ? msg : `## AI の使用量\n  ${msg}`);
  }

  console.log(out.join('\n'));

  if (!prs.error && prs.unclassified.length) {
    console.log(`\n未分類のファイル: ${prs.unclassified.length} 件`);
    for (const f of prs.unclassified) {
      console.log(`  ${f}`);
      fail(`${f} が分類規則のどれにも一致しません。investment-classes.json へ追加してください`);
    }
  } else if (!prs.error) {
    console.log('\n未分類のファイル: 0 件');
  }

  const failed = Boolean(prs.error) || (prs.unclassified?.length ?? 0) > 0;
  notice(`investment-measure: PR ${prs.total ?? 0} 件を分類、未分類 ${prs.unclassified?.length ?? 0} 件`);
  process.exit(failed ? 1 : 0);
}
