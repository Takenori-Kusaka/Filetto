// 依存関係のライセンス検査(G-5 基準5 / ip-clearance)の判定部。
//
//   pip-licenses --format=json --from=all | node scripts/gate/license-check.mjs
//
// pip-licenses の --allow-only は、報告された文字列を許可一覧と単純に文字列比較します。
// そのため SPDX の複合式(`Apache-2.0 OR BSD-3-Clause`)は、構成要素がすべて許可範囲でも
// 不一致になります。--partial-match は逆に `MIT` の許可で `MIT-0` を通してしまいます。
// どちらも判定として成立しないため、判定をこちらへ持ちます。
//
// 読む順序は PEP 639 に従います。
//   1. License-Expression (PEP 639 の正本)
//   2. License-Metadata   (旧 License フィールド)
//   3. License-Classifier (`License ::` 分類子。補助)
//
// 出力の原則:
//   - 対象が0件のときは、0件であることを出力する
//   - 分類子から補正して通したものは、必ず一覧で出力する(黙って通さない)
//
// 判断記録: context/decisions/0007-allowed-licenses.md
// 調査記録: docs/platform/PL-0001-ip-clearance-pep639.md

import { readFileSync } from 'node:fs';
import { pathToFileURL } from 'node:url';

const ALLOWED = (process.env.PIT_IN_ALLOWED_LICENSES ?? '')
  .split(';')
  .map((s) => s.trim())
  .filter(Boolean);

// 検査対象から外すパッケージ。既定は空(現行の挙動と同じ)。
// `pip install -e .` が自分自身を検査対象に含めることへの対処に使えます。
// allowedLicenses は依存関係に許すライセンスの一覧であり、自プロジェクトのライセンスとは
// 別の概念です(ADR-0007)。既定を空にしてあるのは、検査範囲の変更が PO の判断だからです。
const SELF_PACKAGES = (process.env.PIT_IN_SELF_PACKAGES ?? '')
  .split(';')
  .map((s) => normalizeName(s))
  .filter(Boolean);

// 分類子・自由記述を SPDX 識別子へ補正する表。
// ambiguous: true は「分類子が複数の SPDX を含みうる」もの。通すが必ず出力する。
const NORMALIZE = {
  'MIT License': { spdx: 'MIT' },
  'MIT No Attribution License (MIT-0)': { spdx: 'MIT-0' },
  'Apache Software License': { spdx: 'Apache-2.0', ambiguous: true },
  'Apache 2.0': { spdx: 'Apache-2.0' },
  'Apache-2': { spdx: 'Apache-2.0' },
  'BSD License': { spdx: 'BSD-3-Clause', ambiguous: true },
  'ISC License (ISCL)': { spdx: 'ISC' },
  'Mozilla Public License 2.0 (MPL 2.0)': { spdx: 'MPL-2.0' },
  'Python Software Foundation License': { spdx: 'PSF-2.0' },
  PSFL: { spdx: 'PSF-2.0' },
  'GNU Affero General Public License v3 or later (AGPLv3+)': { spdx: 'AGPL-3.0-or-later' },
};

const UNKNOWN = new Set(['', 'UNKNOWN', 'UNKNOWN LICENSE']);

function normalizeName(name) {
  return String(name ?? '')
    .trim()
    .toLowerCase()
    .replace(/[-_.]+/g, '-');
}

// ---- SPDX 式の評価 -------------------------------------------------------
// AND は OR より強く結合する(SPDX Specification Annex D)。
// OR = いずれかが許可範囲にあればよい(利用者が選べるため)。
// AND = すべてが許可範囲にある必要がある。

function tokenize(expr) {
  return expr
    .replace(/([()])/g, ' $1 ')
    .split(/\s+/)
    .filter(Boolean);
}

function isAllowedAtom(atom, allowed) {
  if (allowed.has(atom)) return true;
  // `GPL-2.0+` のような後方互換表記
  if (atom.endsWith('+') && allowed.has(atom.slice(0, -1))) return true;
  if (allowed.has(`${atom}+`)) return true;
  return false;
}

function parseExpression(tokens, allowed) {
  let i = 0;

  function primary() {
    if (tokens[i] === undefined) throw new Error('式が途中で終わっています');
    if (tokens[i] === '(') {
      i += 1;
      const v = orExpr();
      if (tokens[i] !== ')') throw new Error('括弧が閉じていません');
      i += 1;
      return v;
    }
    if (tokens[i] === ')') throw new Error('対応する開き括弧がありません');
    const parts = [tokens[i]];
    i += 1;
    // `GPL-2.0 WITH Classpath-exception-2.0` は1つの識別子として扱う
    while (tokens[i] && tokens[i].toUpperCase() === 'WITH') {
      if (tokens[i + 1] === undefined) throw new Error('WITH の後に例外識別子がありません');
      parts.push(tokens[i], tokens[i + 1]);
      i += 2;
    }
    return isAllowedAtom(parts.join(' '), allowed);
  }

  function andExpr() {
    let v = primary();
    while (tokens[i] && tokens[i].toUpperCase() === 'AND') {
      i += 1;
      v = primary() && v;
    }
    return v;
  }

  function orExpr() {
    let v = andExpr();
    while (tokens[i] && tokens[i].toUpperCase() === 'OR') {
      i += 1;
      v = andExpr() || v;
    }
    return v;
  }

  const result = orExpr();
  if (i !== tokens.length) throw new Error(`解釈できない字句: ${tokens.slice(i).join(' ')}`);
  return result;
}

export function evaluateExpression(expr, allowed) {
  return parseExpression(tokenize(expr), allowed instanceof Set ? allowed : new Set(allowed));
}

// ---- ライセンスの解決 ----------------------------------------------------

export function resolveLicense(pkg) {
  const expression = pkg['License-Expression'];
  const metadata = pkg['License-Metadata'];
  const classifier = pkg['License-Classifier'];

  if (expression && !UNKNOWN.has(expression)) {
    return { license: expression, source: 'License-Expression' };
  }
  if (metadata && !UNKNOWN.has(metadata)) {
    const n = NORMALIZE[metadata];
    if (n) {
      return { license: n.spdx, source: 'License-Metadata', normalizedFrom: metadata, ambiguous: n.ambiguous };
    }
    return { license: metadata, source: 'License-Metadata' };
  }
  if (classifier && !UNKNOWN.has(classifier)) {
    const n = NORMALIZE[classifier];
    if (n) {
      return { license: n.spdx, source: 'License-Classifier', normalizedFrom: classifier, ambiguous: n.ambiguous };
    }
    return { license: classifier, source: 'License-Classifier' };
  }
  return { license: null, source: null };
}

// 判定の本体。入出力を持たないため、テストから直接呼べます。
export function check(packages, allowedList, selfPackages = []) {
  const allowed = new Set(allowedList);
  const self = new Set(selfPackages.map(normalizeName));
  const denied = [];
  const unresolved = [];
  const normalized = [];
  const skipped = [];

  for (const pkg of packages) {
    const name = `${pkg.Name}:${pkg.Version}`;

    if (self.has(normalizeName(pkg.Name))) {
      skipped.push(name);
      continue;
    }

    const r = resolveLicense(pkg);

    if (!r.license) {
      unresolved.push(name);
      continue;
    }
    if (r.normalizedFrom) normalized.push({ name, ...r });

    let ok;
    try {
      ok = parseExpression(tokenize(r.license), allowed);
    } catch (e) {
      denied.push({ name, license: r.license, source: r.source, reason: `式を解釈できません(${e.message})` });
      continue;
    }
    if (!ok) denied.push({ name, license: r.license, source: r.source, reason: '許可一覧にありません' });
  }

  return { total: packages.length, denied, unresolved, normalized, skipped };
}

// ---- 実行 ----------------------------------------------------------------
// import されたときは実行しません(テストから読み込むため)。

const invokedDirectly = process.argv[1] ? pathToFileURL(process.argv[1]).href === import.meta.url : false;

if (invokedDirectly) {
  if (!ALLOWED.length) {
    console.error(
      '許可ライセンス一覧が空です。process.config.json の ci.allowedLicenses を設定してください。' +
        '空のまま通すと、検査を実施していない状態を通過した記録として残ります'
    );
    process.exit(1);
  }

  const raw = readFileSync(process.env.PIT_IN_LICENSE_JSON || 0, 'utf8').trim();

  let packages;
  try {
    packages = JSON.parse(raw);
  } catch {
    console.error('pip-licenses の JSON を解釈できませんでした。--format=json --from=all で渡してください');
    process.exit(1);
  }
  if (!Array.isArray(packages)) {
    console.error('pip-licenses の JSON が配列ではありません。--format=json --from=all で渡してください');
    process.exit(1);
  }

  const r = check(packages, ALLOWED, SELF_PACKAGES);

  console.log(`許可一覧(${ALLOWED.length}件): ${ALLOWED.join(', ')}`);
  console.log(`検査した依存: ${r.total - r.skipped.length}件(取得 ${r.total}件)`);

  if (r.skipped.length) {
    console.log(`\n自プロジェクトとして検査から外したもの: ${r.skipped.length}件`);
    for (const n of r.skipped) console.log(`  ${n}`);
  } else {
    console.log('\n自プロジェクトとして検査から外したもの: 0件');
  }

  if (r.normalized.length) {
    console.log(`\n分類子・自由記述から SPDX へ補正したもの: ${r.normalized.length}件`);
    for (const n of r.normalized) {
      console.log(
        `  ${n.name}  "${n.normalizedFrom}" → ${n.license}  (${n.source})` +
          (n.ambiguous ? '  ※この分類子は複数の SPDX を含みうる' : '')
      );
    }
  } else {
    console.log('\n分類子・自由記述から SPDX へ補正したもの: 0件');
  }

  if (r.unresolved.length) {
    console.log(`\nライセンスを特定できない依存: ${r.unresolved.length}件`);
    for (const n of r.unresolved) console.log(`  ${n}`);
  } else {
    console.log('\nライセンスを特定できない依存: 0件');
  }

  if (r.denied.length) {
    console.log(`\n許可範囲外の依存: ${r.denied.length}件`);
    for (const d of r.denied) console.log(`  ${d.name}  ${d.license}  (${d.source})  ${d.reason}`);
  } else {
    console.log('\n許可範囲外の依存: 0件');
  }

  if (r.denied.length || r.unresolved.length) {
    console.error('\nip-clearance: 不合格');
    process.exit(1);
  }

  console.log('\nip-clearance: 合格');
}
