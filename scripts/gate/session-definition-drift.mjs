// ロール定義の正本と、各ランタイム向け生成物の乖離を検出する(#43)。
//
//   node scripts/gate/session-definition-drift.mjs
//
// 二重管理は既に2件の事故を起こしています(#27 の破損が #42 で発見されるまで
// .gemini 側へ移植されたまま残っていた)。生成経路を作っても、手で書き換えられれば
// 同じことが起きます。検出はそれとは独立に要ります。
//
// 対応と、許容する差分は scripts/gate/session-definition-map.json に書きます。
// 運用に依存する値をスクリプトの定数にしません(context/standards/extensibility.md)。
//
// 許容する差分は「事実として異なる記述」だけです。たとえば `gh pr merge` は
// Claude Code では設定で拒否されますが、Gemini CLI では拒否されません。
// 同じ文を配ると、事実と異なる記述が配られます。
//
// 出力の原則:
//   - 対象が0件のときは、0件であることを出力する
//   - 許容した差分は、許容した理由とともに必ず出力する(黙って通さない)

import fs from 'node:fs';
import path from 'node:path';
import { ROOT, fail, notice } from './config.mjs';

const MAP_PATH = path.join(ROOT, 'scripts/gate/session-definition-map.json');

function readText(rel) {
  return fs.readFileSync(path.join(ROOT, rel), 'utf8').replace(/\r\n/g, '\n');
}

/** SKILL.md から YAML frontmatter を落として本文だけにする */
function bodyOfSkill(text) {
  return text.replace(/^---\n[\s\S]*?\n---\n/, '').trim();
}

/** Gemini CLI の TOML から prompt の中身を取り出す */
function promptOfGeminiToml(text) {
  const m = text.match(/^prompt = """\n([\s\S]*?)"""\s*$/m);
  if (!m) return null;
  // TOML の基本文字列はバックスラッシュをエスケープする
  return m[1].replace(/\\\\/g, '\\').trim();
}

const EXTRACTORS = {
  'gemini-toml': promptOfGeminiToml,
};

/** 最長共通部分列。差分を挿入・削除の塊として出す */
function diffLines(a, b) {
  const n = a.length;
  const m = b.length;
  const lcs = Array.from({ length: n + 1 }, () => new Uint32Array(m + 1));
  for (let i = n - 1; i >= 0; i--) {
    for (let j = m - 1; j >= 0; j--) {
      lcs[i][j] = a[i] === b[j] ? lcs[i + 1][j + 1] + 1 : Math.max(lcs[i + 1][j], lcs[i][j + 1]);
    }
  }
  const out = [];
  let i = 0;
  let j = 0;
  while (i < n && j < m) {
    if (a[i] === b[j]) {
      i++;
      j++;
    } else if (lcs[i + 1][j] >= lcs[i][j + 1]) {
      out.push({ kind: 'source-only', line: i + 1, text: a[i] });
      i++;
    } else {
      out.push({ kind: 'generated-only', line: j + 1, text: b[j] });
      j++;
    }
  }
  while (i < n) out.push({ kind: 'source-only', line: ++i, text: a[i - 1] });
  while (j < m) out.push({ kind: 'generated-only', line: ++j, text: b[j - 1] });
  return out;
}

// ---- 実行 ----------------------------------------------------------------

if (!fs.existsSync(MAP_PATH)) {
  fail(`${path.relative(ROOT, MAP_PATH)} がありません。対応を書いてください`);
  process.exit(1);
}

const map = JSON.parse(fs.readFileSync(MAP_PATH, 'utf8'));
const pairs = map.pairs ?? [];

if (!pairs.length) {
  fail(
    'session-definition-map.json の pairs が空です。対応が0件のまま通すと、' +
      '検査を実施していない状態を通過した記録として残ります'
  );
  process.exit(1);
}

let drifted = 0;
let allowedCount = 0;

for (const pair of pairs) {
  const label = `${pair.source} → ${pair.generated}`;

  if (!fs.existsSync(path.join(ROOT, pair.source))) {
    fail(`${label}: 正本 ${pair.source} がありません`);
    drifted++;
    continue;
  }
  if (!fs.existsSync(path.join(ROOT, pair.generated))) {
    fail(`${label}: 生成物 ${pair.generated} がありません`);
    drifted++;
    continue;
  }

  const extract = EXTRACTORS[pair.format];
  if (!extract) {
    fail(`${label}: format "${pair.format}" の取り出し方が未定義です`);
    drifted++;
    continue;
  }

  const source = bodyOfSkill(readText(pair.source));
  let generated = extract(readText(pair.generated));

  if (generated === null) {
    fail(`${label}: ${pair.generated} から prompt を取り出せませんでした`);
    drifted++;
    continue;
  }

  // 生成物の末尾に付く定型文(移植注記と {{args}})を落とす
  if (pair.allowedTrailer) {
    const trailer = pair.allowedTrailer.replace(/\r\n/g, '\n').trim();
    if (!generated.endsWith(trailer)) {
      fail(`${label}: 末尾の定型文が map の allowedTrailer と一致しません`);
      drifted++;
      continue;
    }
    generated = generated.slice(0, generated.length - trailer.length).trim();
  }

  // 事実として異なる記述を、正本側の表現へ寄せてから比べる
  for (const d of pair.allowedDifferences ?? []) {
    const from = d.generated.replace(/\r\n/g, '\n');
    if (!generated.includes(from)) {
      fail(
        `${label}: 許容差分が生成物に見つかりません。map の allowedDifferences が古くなっています\n` +
          `  探した文字列: ${JSON.stringify(from.slice(0, 60))}...`
      );
      drifted++;
      continue;
    }
    generated = generated.replace(from, d.source.replace(/\r\n/g, '\n'));
    allowedCount++;
    console.log(`  許容: ${label}`);
    console.log(`    理由: ${d.reason}`);
    console.log(`    正本  : ${d.source}`);
    console.log(`    生成物: ${d.generated}`);
  }

  const diff = diffLines(source.split('\n'), generated.split('\n'));
  if (diff.length) {
    drifted++;
    fail(`${label}: 乖離 ${diff.length} 行`);
    for (const d of diff) {
      const mark = d.kind === 'source-only' ? '正本にのみ' : '生成物にのみ';
      console.log(`  ${mark} ${d.kind === 'source-only' ? pair.source : pair.generated}:${d.line}  ${d.text}`);
    }
    console.log(`  正本を ${pair.source} とします。生成物を合わせるか、`);
    console.log(`  事実として異なる記述であれば session-definition-map.json の allowedDifferences へ理由とともに書いてください`);
  }
}

// 生成物が未整備のロール定義を数え上げる。失敗はさせないが、黙ってもいない。
// roleDefinitions に書いた実在のファイルのうち、pairs に無いものが未展開です。
const mapped = new Set(pairs.map((p) => p.source));
const unmapped = [];
const missing = [];
for (const rel of map.roleDefinitions ?? []) {
  if (!fs.existsSync(path.join(ROOT, rel))) {
    missing.push(rel);
    continue;
  }
  if (!mapped.has(rel)) unmapped.push(rel);
}
if (missing.length) {
  for (const rel of missing) fail(`roleDefinitions に書かれた ${rel} がありません`);
  drifted += missing.length;
}

console.log(`許容した差分: ${allowedCount} 件`);
console.log(`未展開のロール定義: ${unmapped.length} 件`);
for (const u of unmapped) console.log(`  ${u}`);

notice(`session-definition-drift: ${pairs.length} 組を検査、${drifted} 組で乖離を検出`);
process.exit(drifted ? 1 : 0);
