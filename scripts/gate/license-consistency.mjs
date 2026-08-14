// ライセンスの宣言が食い違っていないかを検査する(#112)。
//
//   node scripts/gate/license-consistency.mjs
//
// README が「コードは MIT」と書き、LICENSE と pyproject.toml は AGPL-3.0-or-later
// でした。**公開後に回収が難しい種類の誤りです。**
//
// 何を突き合わせるか:
//   1. pyproject.toml の license(コードのライセンスの正本)
//   2. README の機械可読な宣言(code= と docs=)
//   3. LICENSE / LICENSE-docs の全文の見出し
//
// **README の文章から推測しません。** 推測は、書き換えの取りこぼしを検出できません。
// 宣言が無ければ落とします。
//
// 出力の原則: 突き合わせた値をすべて出力します。合致しているときも出します。

import fs from 'node:fs';
import path from 'node:path';
import { ROOT, fail, notice } from './config.mjs';

const CONFIG_PATH = path.join(ROOT, 'scripts/gate/license-declaration.json');

if (!fs.existsSync(CONFIG_PATH)) {
  fail('scripts/gate/license-declaration.json がありません。宣言の照合先を書いてください');
  process.exit(1);
}
const config = JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf8'));

function read(rel) {
  const p = path.join(ROOT, rel);
  return fs.existsSync(p) ? fs.readFileSync(p, 'utf8') : null;
}

/** ライセンス全文の見出しが、その SPDX 識別子のものと一致するか */
export function titleMatches(text, spdx, titles) {
  const want = titles[spdx];
  if (!want) return { ok: false, reason: `SPDX 識別子 ${spdx} の見出しが titles にありません` };
  const head = text.split(/\r?\n/).slice(0, 12).join(' ');
  return head.toUpperCase().includes(want.toUpperCase())
    ? { ok: true, want }
    : { ok: false, reason: `全文の見出しが「${want}」ではありません`, want };
}

let bad = 0;
const rows = [];

// 1. 正本
const truth = config.sourceOfTruth ?? {};
const truthText = read(truth.file);
let codeSpdx = null;

if (!truthText) {
  fail(`${truth.file} がありません。コードのライセンスの正本です`);
  bad++;
} else {
  const m = truthText.match(new RegExp(truth.pattern, 'm'));
  if (!m) {
    fail(`${truth.file} から license を読み取れません`);
    bad++;
  } else {
    codeSpdx = m[1];
    rows.push([`${truth.file}(正本)`, `code = ${codeSpdx}`]);
  }
}

// 2. README の宣言
const readmeText = read(config.readmeFile);
let declared = null;

if (!readmeText) {
  fail(`${config.readmeFile} がありません`);
  bad++;
} else {
  const m = readmeText.match(new RegExp(config.readmeMarker));
  if (!m) {
    fail(
      `${config.readmeFile} に機械可読なライセンス宣言がありません。次の1行を置いてください:\n` +
        `    <!-- license: code=${codeSpdx ?? '<SPDX>'} docs=<SPDX> -->\n` +
        '  文章から推測しません。推測では、書き換えの取りこぼしを検出できません'
    );
    bad++;
  } else {
    declared = m.groups;
    rows.push([config.readmeFile, `code = ${declared.code} / docs = ${declared.docs}`]);
  }
}

// 3. 正本と README の突き合わせ
if (codeSpdx && declared && declared.code !== codeSpdx) {
  fail(
    `コードのライセンスが食い違っています。${truth.file} は ${codeSpdx}、` +
      `${config.readmeFile} は ${declared.code} と書いています`
  );
  bad++;
}

// 4. 全文の見出し
for (const f of config.licenseFiles ?? []) {
  const text = read(f.file);
  if (!text) {
    fail(`${f.file} がありません`);
    bad++;
    continue;
  }
  const spdx = f.id === 'code' ? (declared?.code ?? codeSpdx) : declared?.[f.id];
  if (!spdx) {
    rows.push([f.file, '照合できません(宣言が無いため)']);
    continue;
  }
  const t = titleMatches(text, spdx, config.titles ?? {});
  rows.push([f.file, t.ok ? `${spdx}(見出し一致)` : `${spdx} — ${t.reason}`]);
  if (!t.ok) {
    fail(`${f.file} が ${spdx} の全文ではありません。${t.reason}`);
    bad++;
  }
}

console.log('突き合わせた宣言:');
for (const [k, v] of rows) console.log(`  ${k.padEnd(24)} ${v}`);

notice(`license-consistency: ${rows.length} 件を突き合わせ、${bad} 件の食い違いを検出`);
process.exit(bad ? 1 : 0);
