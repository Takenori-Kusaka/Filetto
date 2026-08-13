// 作業ツリーが古い定義で動いていないかを、セッション開始時に見えるようにする(#95 依頼4)。
//
// SessionStart フックとして起動します。**止めません。見えるようにするだけです。**
// 作業中にブランチにいるのは正常であり、問題は「気づかないまま古い定義で動くこと」です。
//
// 実際に起きた事象:
//   Filetto-qm が docs/log-process-compass-217 に留まり、origin/main より 47 コミット
//   遅れていた。そのブランチ時点の .claude/settings.json は deny 22件を持っており、
//   gh pr merge が遮断され続けた。git pull はそのブランチを取りに行くため、何度
//   実行しても HEAD は変わらなかった。
//
// 見るのは3つです。
//   1. 上流が消えているか(delete_branch_on_merge により、マージ済みブランチは消える)
//   2. origin/main からどれだけ遅れているか
//   3. **ロールの挙動を決めるファイルが origin/main と違うか**
//
// 3 が本体です。1 と 2 だけでは「遅れているが、挙動に関わる差は無い」場合と
// 区別できません。
//
// 出力の原則: 差が無いときも「差はありません」と出します。無言で終わると、
// フックが動いたのか動いていないのかが分かりません。

import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const CONFIG_PATH = path.join(ROOT, '.claude/worktree-freshness.json');

const config = fs.existsSync(CONFIG_PATH)
  ? JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf8'))
  : {};

const DEFAULT_BASE = config.defaultBase ?? 'main';
// ロールの挙動を決めるファイル。ここが古いと、古い規約のまま動きます
const WATCHED = config.watchedPaths ?? [
  '.claude/settings.json',
  '.claude/guard.json',
  '.claude/skills',
  '.claude/agents',
  'CLAUDE.md',
];

const git = (argv) => {
  try {
    return execFileSync('git', argv, { cwd: ROOT, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).trim();
  } catch {
    return null;
  }
};

function main() {
  if (git(['rev-parse', '--is-inside-work-tree']) !== 'true') return;

  const branch = git(['rev-parse', '--abbrev-ref', 'HEAD']);
  const baseRef = git(['rev-parse', '--verify', '--quiet', `origin/${DEFAULT_BASE}^{commit}`])
    ? `origin/${DEFAULT_BASE}`
    : null;

  if (!baseRef) {
    console.log(
      `[作業ツリー] origin/${DEFAULT_BASE} が手元にありません。git fetch origin を実行してください`
    );
    return;
  }

  if (branch === DEFAULT_BASE) {
    const behind = git(['rev-list', '--count', `HEAD..${baseRef}`]);
    if (behind && behind !== '0') {
      console.log(`[作業ツリー] ${DEFAULT_BASE} にいますが ${behind} コミット遅れています。git pull を実行してください`);
      return;
    }
    console.log(`[作業ツリー] ${DEFAULT_BASE} の最新です。${baseRef} との差はありません`);
    return;
  }

  const lines = [`[作業ツリー] いま ${branch} にいます(${DEFAULT_BASE} ではありません)`];

  // 上流が消えている = マージ済みで、リモートのブランチが削除された
  const upstream = git(['rev-parse', '--abbrev-ref', '--symbolic-full-name', '@{upstream}']);
  if (upstream) {
    const upstreamGone = git(['rev-parse', '--verify', '--quiet', `${upstream}^{commit}`]) === null;
    if (upstreamGone) {
      lines.push(
        `  上流 ${upstream} は消えています。**マージ済みの可能性が高いです。** ` +
          `git switch ${DEFAULT_BASE} && git pull を実行してください`
      );
    }
  }

  const behind = git(['rev-list', '--count', `HEAD..${baseRef}`]);
  if (behind && behind !== '0') lines.push(`  ${baseRef} より ${behind} コミット遅れています`);

  // 挙動を決めるファイルの差。ここが本体。
  //
  // 三点(base...HEAD)ではなく二点(base HEAD)で比べます。三点は共通の祖先からの
  // 差を見るため、**base 側だけが進んだ変更が出てきません。** 本件で見たいのは
  // まさにそれ(main が進み、手元が取り残された)です。
  const diff = git(['diff', '--name-only', baseRef, 'HEAD', '--', ...WATCHED]);
  const changed = diff ? diff.split('\n').filter(Boolean) : [];

  if (changed.length) {
    lines.push(`  **ロールの挙動を決めるファイルが ${baseRef} と違います: ${changed.length} 件**`);
    for (const f of changed) lines.push(`    ${f}`);
    lines.push(
      `  古い規約・古い遮断設定のまま動いている可能性があります。` +
        `${DEFAULT_BASE} へ戻すか、この差が意図したものかを確かめてください`
    );
    lines.push(
      `  **.claude/settings.json はセッション開始時に読まれます。** ` +
        `ブランチを切り替えたら Claude Code を再起動してください`
    );
  } else {
    lines.push(`  ロールの挙動を決めるファイルに ${baseRef} との差はありません`);
  }

  console.log(lines.join('\n'));
}

main();
