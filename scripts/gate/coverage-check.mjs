// カバレッジの下限を検査する(G-5 基準3)。
//
//   node scripts/gate/coverage-check.mjs
//
// アダプタの coverageSummary が指すファイルを読み、process.config.json の下限と比べます。
// coverageSummary が null の場合、判定を実施しない扱いとして記録します(通過させます)。
// 「検査していない」ことと「基準を満たした」ことを、記録の上で区別するためです。

import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { loadConfig, loadAdapter, ROOT, fail, notice, warn, hasTarget, matchGlob } from './config.mjs';
import { isProductCode, THRESHOLD_FILES } from './check-pr.mjs';

const config = loadConfig();
const adapter = loadAdapter(config);
const threshold = config.ci?.coverageThreshold ?? 80;

if (!hasTarget(adapter)) {
  notice(`カバレッジ判定: 対象プロジェクトが見つかりません。未実施として記録します`);
  writeResult({ measured: false, reason: 'No target project found' });
  process.exit(0);
}

const rel = adapter.coverageSummary;
if (!rel) {
  warn(`アダプタ ${adapter.id} はカバレッジの集計ファイルを持ちません。判定を実施しない扱いで記録します`);
  writeResult({ measured: false, reason: 'coverageSummary が null' });
  process.exit(0);
}

const p = path.join(ROOT, rel);
if (!fs.existsSync(p)) {
  fail(`カバレッジの集計ファイルがありません: ${rel}。テストの実行設定を確認してください`);
  process.exit(1);
}

const raw = JSON.parse(fs.readFileSync(p, 'utf8'));
// 測定の対象のコードが0行(製品のコードを置く前の基盤だけの状態)。istanbul は割合を "Unknown" と出す。
// 「対象なし」として記録して通す(標準 第4章 G-5「検査対象が存在しない場合の扱い」)。実装が始まった後に出たら、
// 測定の対象(package.json の coverage の --include など)が製品のコードの置き場と合っていない
const total = raw.total?.lines?.total ?? raw.totals?.num_statements;
if (total === 0) {
  // 製品のコード(文書・記録・強制層・設定・テスト以外のファイル)が既にあるのに0行なら、測定の対象の設定の不備である。
  // 「対象なし」で通すと、測定していない状態を通過として残すため、失敗させる
  const product = productFiles();
  if (product.length) {
    fail(
      `カバレッジの測定対象が0行ですが、製品のコードがあります(${product.slice(0, 5).join(', ')}${product.length > 5 ? ` ほか ${product.length - 5} 件` : ''})。` +
        '測定の対象(node では package.json の coverage の --include)を、製品のコードの置き場に合わせてください'
    );
    writeResult({ measured: false, reason: '測定対象が0行だが製品のコードがある', product: product.slice(0, 20) });
    process.exit(1);
  }
  warn(`カバレッジ判定: ${rel} の測定対象が0行で、製品のコードもありません。対象なしとして記録します`);
  writeResult({ measured: false, reason: '測定対象のコードが0行' });
  process.exit(0);
}
let pct = null;

// istanbul(coverage-summary.json)形式
if (raw.total?.lines?.pct !== undefined) pct = raw.total.lines.pct;
// pytest-cov(coverage.json)形式
else if (raw.totals?.percent_covered !== undefined) pct = raw.totals.percent_covered;

if (pct === null) {
  fail(`${rel} からカバレッジを読み取れません。istanbul 形式または pytest-cov 形式に対応しています`);
  process.exit(1);
}

// 測定対象が小さすぎる間は、閾値が何も保証しません。
//
// 2026-08-14 の実測では、実装コードの statements が **2** で、カバレッジは 100%
// でした。**2行のうち2行が通れば 100% です。** 下限90%という数値は、この状態では
// 品質について何も述べていません。
//
// **判定を実施しない場合も、実施しなかったことを出力し証跡へ残します。**
// 「通過した」と「判定していない」を区別できる形にします。
//
// **切り替えの条件を statements の数で置いているのは暫定です。** 本来は
// 「どのフェーズから実装向けの検査を有効にするか」をプロセスの構成が定めるべきで、
// 標準にも process.config.json にもその欄がありません
// (process-compass へ起票済み)。欄ができたら、そちらへ差し替えます。
const minStatements = config.ci?.coverageMinStatements ?? 0;
const statements = raw.totals?.num_statements ?? raw.total?.lines?.total ?? null;

if (minStatements > 0 && statements !== null && statements < minStatements) {
  writeResult({ measured: false, pct, threshold, statements, minStatements, reason: '測定対象が下限未満' });
  notice(
    `カバレッジの判定を実施しません。測定対象が ${statements} 文で、` +
      `判定を始める下限 ${minStatements} 文に達していません(実測 ${pct}%)。` +
      `この状態では下限 ${threshold}% は品質について何も述べません`
  );
  process.exit(0);
}

const ok = pct >= threshold;
writeResult({ measured: true, pct, threshold, statements, ok });

if (!ok) {
  fail(`カバレッジ ${pct}% が下限 ${threshold}% を下回っています(測定対象 ${statements} 文)`);
  process.exit(1);
}
notice(`カバレッジ ${pct}%(下限 ${threshold}% / 測定対象 ${statements} 文)`);

/** リポジトリが追跡しているファイルのうち、製品のコード(check-pr と同じ分類)で、テストでないもの */
function productFiles() {
  let files = [];
  try {
    files = execFileSync('git', ['ls-files', '-z'], { cwd: ROOT, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).split('\0').filter(Boolean);
  } catch {
    return [];
  }
  let testPatterns = [];
  try {
    testPatterns = JSON.parse(fs.readFileSync(path.join(ROOT, '.claude/guard.json'), 'utf8')).testPatterns ?? [];
  } catch {
    // ガードの設定が無ければ、テストの識別を行わない
  }
  const thresholdGlobs = [...THRESHOLD_FILES, ...(Array.isArray(adapter.thresholdFiles) ? adapter.thresholdFiles : [])];
  return files.filter((f) => isProductCode(f, thresholdGlobs) && !testPatterns.some((g) => matchGlob(g, f)));
}

function writeResult(o) {
  const dir = path.join(ROOT, 'evidence');
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, 'coverage-result.json'), JSON.stringify(o, null, 2) + '\n', 'utf8');
}
