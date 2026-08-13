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

// ---- 3. AI 実行費(ccusage) --------------------------------------------------
// 価格表を自前で持ちません。ccusage(OSS)が LiteLLM の価格から金額を出します。
// ccusage は ~/.claude のセッション記録を読むため、**CI では取れません。**

export function summarizeCcusage(rows, pattern) {
  const re = new RegExp(pattern, 'i');
  const target = rows.filter((r) => re.test(r.projectPath ?? ''));
  const byProject = new Map();
  const totals = { sessions: 0, cost: 0, output: 0, input: 0, cacheRead: 0, cacheCreate: 0, spanMs: 0 };
  const intervals = [];

  for (const r of target) {
    const key = String(r.projectPath).split(/[\/]/).pop();
    const v = byProject.get(key) ?? { sessions: 0, cost: 0 };
    v.sessions += 1;
    v.cost += r.totalCost ?? 0;
    byProject.set(key, v);

    totals.sessions += 1;
    totals.cost += r.totalCost ?? 0;
    totals.output += r.outputTokens ?? 0;
    totals.input += r.inputTokens ?? 0;
    totals.cacheRead += r.cacheReadTokens ?? 0;
    totals.cacheCreate += r.cacheCreationTokens ?? 0;

    const a = Date.parse(r.firstActivity);
    const b = Date.parse(r.lastActivity);
    if (Number.isFinite(a) && Number.isFinite(b) && b >= a) {
      totals.spanMs += b - a;
      intervals.push([a, b]);
    }
  }

  // 5つの作業ツリーは同時に動くため、単純な合計は実時間を超えます。重なりを潰します
  intervals.sort((x, y) => x[0] - y[0]);
  let mergedMs = 0;
  let cur = null;
  for (const [a, b] of intervals) {
    if (!cur) cur = [a, b];
    else if (a <= cur[1]) cur[1] = Math.max(cur[1], b);
    else {
      mergedMs += cur[1] - cur[0];
      cur = [a, b];
    }
  }
  if (cur) mergedMs += cur[1] - cur[0];

  return { ...totals, mergedMs, byProject, matched: target.length, scanned: rows.length };
}

function readCcusage() {
  const file = argOf('--ccusage-json', null);
  const cfg = config.aiUsage ?? {};
  try {
    const raw = file
      ? fs.readFileSync(path.resolve(file), 'utf8')
      : run('npx', ['-y', cfg.tool ?? 'ccusage@latest', ...(cfg.command ?? ['claude', 'session', '--json'])]);
    const o = JSON.parse(raw);
    const rows = o.sessions ?? o.session ?? [];
    if (!Array.isArray(rows)) return { error: 'ccusage の出力を解釈できません' };
    return summarizeCcusage(rows, cfg.projectPathPattern ?? 'Filetto');
  } catch (e) {
    return { error: `ccusage を実行できません(${String(e.message).split(String.fromCharCode(10))[0]})` };
  }
}

// ---- 4. 稼働時間(git のコミット間隔からの推定) ------------------------------
// **人の自己申告を求めません。** 確度は高くありません。値ではなく推移を見ます。

export function estimateEffortHours(commits, cfg) {
  const maxGap = (cfg.maxCommitGapMinutes ?? 120) * 60000;
  const first = (cfg.firstCommitMinutes ?? 30) * 60000;
  const alias = cfg.authorAliases ?? {};

  const byAuthor = new Map();
  for (const c of commits) {
    const a = alias[c.author] ?? c.author;
    if (!byAuthor.has(a)) byAuthor.set(a, []);
    byAuthor.get(a).push(c.time);
  }

  const perAuthor = [];
  let totalMs = 0;
  for (const [a, tsRaw] of byAuthor) {
    const ts = [...tsRaw].sort((x, y) => x - y);
    let ms = first;
    for (let i = 1; i < ts.length; i++) {
      const d = ts[i] - ts[i - 1];
      ms += d < maxGap ? d : first;
    }
    perAuthor.push({ author: a, commits: ts.length, hours: ms / 3600000 });
    totalMs += ms;
  }
  return { hours: totalMs / 3600000, perAuthor };
}

function measureEffort() {
  try {
    const out = run('git', ['log', 'origin/main', '--pretty=%at|%an']);
    const commits = out
      .trim()
      .split(String.fromCharCode(10))
      .filter(Boolean)
      .map((l) => {
        const [t, ...rest] = l.split('|');
        return { time: Number(t) * 1000, author: rest.join('|') };
      });
    if (!commits.length) return { error: 'origin/main のコミットが読めません' };
    return { ...estimateEffortHours(commits, config.effort ?? {}), commits: commits.length };
  } catch (e) {
    return { error: `git log に失敗しました: ${e.message}` };
  }
}

// ---- 5. 進捗の代理指標 ------------------------------------------------------
// **進捗そのものではありません。** git から取れるものだけで組みます。

function measureProgress() {
  const cfg = config.progress ?? {};
  const gates = cfg.gates ?? [];
  const dir = path.join(ROOT, cfg.gateRecordDir ?? 'docs/gates');
  const records = fs.existsSync(dir) ? fs.readdirSync(dir).filter((f) => f.endsWith('.md')) : [];
  const passed = gates.filter((g) => records.some((f) => f.toLowerCase().startsWith(g.toLowerCase().replace('-', ''))));

  const specDir = path.join(ROOT, cfg.specDir ?? 'specs');
  const specs = fs.existsSync(specDir)
    ? fs.readdirSync(specDir, { withFileTypes: true }).filter((e) => e.isDirectory()).map((e) => e.name)
    : [];
  const withPlan = specs.filter((s) => fs.existsSync(path.join(specDir, s, cfg.planFile ?? 'plan.md')));

  return { gates: gates.length, gatesWithRecord: passed.length, passed, specs: specs.length, withPlan: withPlan.length };
}

// ---- 実行 ------------------------------------------------------------------
// import されたときは実行しません(テストから関数だけを読み込むため)。

const invokedDirectly = process.argv[1] ? pathToFileURL(process.argv[1]).href === import.meta.url : false;

if (invokedDirectly) {
  const prs = measurePrs();
  const lines = countLines(config.lineCountTargets ?? []);
  const effort = measureEffort();
  const progress = measureProgress();
  const ai = has('--no-ai') ? { error: '--no-ai が指定されました' } : readCcusage();

  const md = has('--markdown');
  const out = [];
  const say = (s = '') => out.push(s);
  const k = (n) => Math.round(n).toLocaleString();
  const h = (ms) => (ms / 3600000).toFixed(1);

  // 1. 投入
  if (md) {
    say('### 投入(すべて機械が出した値。自己申告はありません)');
    say();
    say('| 項目 | 値 | 出所 | 確度 |');
    say('| --- | --- | --- | --- |');
    say(
      ai.error
        ? `| AI 実行費 | 取得できません | ${ai.error} | — |`
        : `| AI 実行費 | **$${ai.cost.toFixed(2)}** | ccusage(${ai.matched} セッション) | 中。価格表は ccusage が持つ |`
    );
    say(
      effort.error
        ? `| 稼働時間 | 取得できません | ${effort.error} | — |`
        : `| 稼働時間(推定) | **${effort.hours.toFixed(1)} 時間** | git のコミット間隔 ${effort.commits} 件 | **低。値ではなく推移を見る** |`
    );
    if (!ai.error) {
      say(`| セッションが動いていた実時間 | ${h(ai.mergedMs)} 時間 | ccusage の活動時刻(重なりを潰した値) | 低 |`);
      say(`| 出力トークン | ${k(ai.output)} | ccusage | 高 |`);
    }
  } else {
    say('## 投入');
    say(ai.error ? `  AI 実行費: 取得できません(${ai.error})` : `  AI 実行費  $${ai.cost.toFixed(2)}(${ai.matched} セッション)`);
    if (!ai.error) {
      say(`  出力 ${k(ai.output)} / 入力 ${k(ai.input)} / キャッシュ読み ${k(ai.cacheRead)}`);
      for (const [w, v] of [...ai.byProject].sort((a, b) => b[1].cost - a[1].cost)) {
        say(`    ${w}  $${v.cost.toFixed(2)}(${v.sessions} セッション)`);
      }
      say(`  セッションが動いていた実時間 ${h(ai.mergedMs)} 時間(重なりを潰した値)`);
    }
    say(effort.error ? `  稼働時間: 取得できません(${effort.error})` : `  稼働時間(推定) ${effort.hours.toFixed(1)} 時間 / コミット ${effort.commits} 件`);
    if (!effort.error) for (const a of effort.perAuthor) say(`    ${a.author}  ${a.commits} コミット  ${a.hours.toFixed(1)} 時間`);
  }

  // 2. 成果物の内訳
  say();
  if (md) {
    say('### 成果物の内訳');
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
    else say(`  合計 ${prs.total} 件 / 変更ファイルを取得できなかった PR ${prs.noFiles} 件`);
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

  // 3. 進捗の代理指標
  say();
  const perGate = progress.gates ? Math.round((progress.gatesWithRecord / progress.gates) * 100) : 0;
  if (md) {
    say('### 進捗の代理指標(進捗そのものではありません)');
    say();
    say('| 指標 | 値 |');
    say('| --- | --- |');
    say(`| 判定記録のあるゲート | ${progress.gatesWithRecord} / ${progress.gates}(${perGate}%)  ${progress.passed.join(' ')} |`);
    say(`| 実装計画のある機能 | ${progress.withPlan} / ${progress.specs} |`);
    if (!ai.error && !effort.error) {
      const perGateCost = progress.gatesWithRecord ? ai.cost / progress.gatesWithRecord : 0;
      say(`| ゲート1つあたりの AI 実行費 | $${perGateCost.toFixed(2)} |`);
    }
  } else {
    say('## 進捗の代理指標');
    say(`  判定記録のあるゲート ${progress.gatesWithRecord} / ${progress.gates}(${perGate}%)  ${progress.passed.join(' ')}`);
    say(`  実装計画のある機能 ${progress.withPlan} / ${progress.specs}`);
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
