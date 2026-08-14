// 受入基準の曖昧語を検出する(G-5 基準4)。
//
//   node scripts/gate/spec-lint.mjs [対象ディレクトリ...]
//
// 既定の対象は specs/ と docs/。1件でも検出したら失敗させます。
// 曖昧語が残った受入基準は、実装されるか否かが不定になるためです。
//
// ## 検査しない区間
//
// **判定者が記入した文は、機械で判定しません。**
//
// 標準 5.7.4 は「記述の実質性を機械的に判定して、承認の可否を自動的に決めては
// ならない」と定めています。判定記録は判定が成立した証拠であり(第4章 共通ルール4)、
// その成立を語句検査が止める構図は、この条項に抵触します。判定者の言葉を書き換える
// ことは記録の改竄にあたるため、書き換えでは解けません。
//
//   <!-- spec-lint-ignore start: 判定者の記入欄。標準 5.7.4 により機械で判定しない -->
//   判断: 条件付き決裁
//   理由: ...
//   <!-- spec-lint-ignore end -->
//
// **理由の記載を求めます。** 理由の無い除外は落とします。パスで除外しないのは、
// 判定記録の中でも受入基準を転記した部分は検査されるべきだからです。
// また `CLAUDE.md` は「判定はファイルパスではなく変更の性質で行う」としています。
//
// 行単位の逃がしは従来どおり `<!-- spec-lint-ok -->` です。
//
// 出力の原則: 除外した区間は、件数と理由を必ず出力します。0件のときも出力します。

import fs from 'node:fs';
import path from 'node:path';
import { ROOT, fail, notice } from './config.mjs';

const POLICY_PATH = path.join(ROOT, 'scripts/gate/spec-lint-policy.json');

if (!fs.existsSync(POLICY_PATH)) {
  fail('scripts/gate/spec-lint-policy.json がありません。禁止語と方針を書いてください');
  process.exit(1);
}
const policy = JSON.parse(fs.readFileSync(POLICY_PATH, 'utf8'));

const BANNED = policy.bannedWords ?? [];
if (!BANNED.length) {
  fail('spec-lint-policy.json の bannedWords が空です。0語のまま通すと、検査を実施していない状態を通過した記録として残ります');
  process.exit(1);
}

// 引用ブロック(行頭 `>`)は既定で検査しません。閣議決定文書の条文や調査票の
// 選択肢は、こちらの都合で書き換えられないためです。書き換えると引用が原文と
// 一致しなくなります(#104)。
//
// ただし enforcedPaths の配下では引用も検査します。**受入基準の正本であり、
// 引用の形にすれば禁止語を書けるという抜け道を作らないため**です。
const QUOTE = policy.quoteBlock ?? {};
const QUOTE_LINE = /^\s*>/;

/** glob をごく小さな部分集合で照合する(`**` `*` のみ) */
function globToRegExp(glob) {
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
    } else if (SPECIAL.includes(c)) {
      re += String.fromCharCode(92) + c;
    } else {
      re += c;
    }
  }
  return new RegExp('^' + re + '$');
}

export function isQuoteEnforced(rel, q = QUOTE) {
  if (!q.exempt) return true;
  return (q.enforcedPaths ?? []).some((p) => globToRegExp(p).test(rel));
}

const IGNORE_START = /<!--\s*spec-lint-ignore\s+start\s*:?\s*(.*?)\s*-->/;
const IGNORE_END = /<!--\s*spec-lint-ignore\s+end\s*-->/;

const targets = process.argv.slice(2).length ? process.argv.slice(2) : (policy.targets ?? ['specs', 'docs']);

function walk(dir, out) {
  if (!fs.existsSync(dir)) return;
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) walk(p, out);
    else if (e.name.endsWith('.md')) out.push(p);
  }
}

// path.resolve は絶対パスの指定をそのまま扱います(path.join は連結してしまう)
const files = [];
for (const t of targets) walk(path.resolve(ROOT, t), files);

if (!files.length) {
  notice(`検査対象がありません(${targets.join(', ')})`);
  process.exit(0);
}

let hits = 0;
let malformed = 0;
let quoteSkipped = 0;
const quoteFiles = new Set();
const ignored = [];

for (const f of files) {
  const rel = path.relative(ROOT, f).split(path.sep).join('/');
  const lines = fs.readFileSync(f, 'utf8').split(/\r?\n/);

  let inFence = false;
  let ignoreFrom = null;
  let ignoreReason = '';

  lines.forEach((line, i) => {
    const lineNo = i + 1;

    // コード塀の中は、注記も本文も検査しません。塀の中の注記は説明のための例です
    if (/^\s*```/.test(line)) {
      inFence = !inFence;
      return;
    }
    if (inFence) return;

    // 除外区間の開始・終了。区間の外にある `end` と、理由の無い `start` は落とす
    const start = line.match(IGNORE_START);
    if (start) {
      if (ignoreFrom !== null) {
        malformed++;
        fail(`${rel}:${lineNo} spec-lint-ignore start が入れ子になっています(${ignoreFrom} 行目から未閉鎖)`);
        return;
      }
      const reason = start[1].trim();
      if (!reason) {
        malformed++;
        fail(
          `${rel}:${lineNo} spec-lint-ignore start に理由がありません。` +
            '`<!-- spec-lint-ignore start: 理由 -->` の形で、なぜ検査しないかを書いてください'
        );
        return;
      }
      ignoreFrom = lineNo;
      ignoreReason = reason;
      return;
    }
    if (IGNORE_END.test(line)) {
      if (ignoreFrom === null) {
        malformed++;
        fail(`${rel}:${lineNo} 対応する spec-lint-ignore start がありません`);
        return;
      }
      ignored.push({ rel, from: ignoreFrom, to: lineNo, lines: lineNo - ignoreFrom - 1, reason: ignoreReason });
      ignoreFrom = null;
      ignoreReason = '';
      return;
    }
    if (ignoreFrom !== null) return;
    if (/<!--\s*spec-lint-ok/.test(line)) return;

    // 引用ブロック。一次資料の逐語引用を書き換えさせないため
    if (QUOTE_LINE.test(line) && !isQuoteEnforced(rel)) {
      if (BANNED.some((w) => line.includes(w))) {
        quoteSkipped++;
        quoteFiles.add(rel);
      }
      return;
    }

    for (const w of BANNED) {
      let idx = line.indexOf(w);
      while (idx >= 0) {
        hits++;
        fail(`${rel}:${lineNo}:${idx + 1} 曖昧語 "${w}" があります。条件と期待動作で書き直してください`);
        idx = line.indexOf(w, idx + w.length);
      }
    }
  });

  if (ignoreFrom !== null) {
    malformed++;
    fail(`${rel}:${ignoreFrom} spec-lint-ignore start が閉じられていません。ファイル末尾まで検査されません`);
  }
}

// 何をどれだけ検査したか。ディレクトリごとに出す
const byDir = new Map();
for (const f of files) {
  const rel = path.relative(ROOT, f).split(path.sep).join('/');
  const dir = rel.split('/').slice(0, 2).join('/');
  byDir.set(dir, (byDir.get(dir) ?? 0) + 1);
}
console.log('検査した範囲:');
for (const [dir, n] of [...byDir].sort()) console.log(`  ${dir}  ${n} ファイル`);

if (quoteSkipped) {
  console.log('');
  console.log(`引用ブロックとして検査から外した行: ${quoteSkipped} 行(${quoteFiles.size} ファイル)`);
  for (const f of [...quoteFiles].sort()) console.log(`  ${f}`);
  console.log(`  ${(QUOTE.enforcedPaths ?? []).join(' / ')} の配下では引用も検査します`);
} else {
  console.log('');
  console.log('引用ブロックとして検査から外した行: 0 行');
}

if (ignored.length) {
  const totalLines = ignored.reduce((a, b) => a + b.lines, 0);
  console.log(`\n検査から外した区間: ${ignored.length} 件(${totalLines} 行)`);
  for (const g of ignored) console.log(`  ${g.rel}:${g.from}-${g.to}(${g.lines} 行)  ${g.reason}`);
} else {
  console.log('\n検査から外した区間: 0 件');
}

console.log(`\nspec-lint: ${files.length} ファイルを検査、${hits} 件検出`);
process.exit(hits || malformed ? 1 : 0);
