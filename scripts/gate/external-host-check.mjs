// 組織の管理外のホストへの参照を検出する(#115)。
//
//   node scripts/gate/external-host-check.mjs [対象...]
//
// 2026-08-14、着手決裁の資料を claude.ai の Artifact として発行しました。
// **組織が保存期間もアクセス権も制御できないホストに、決裁の入力が置かれた状態**
// になりました。決裁記録から参照すべき対象が、組織の外にあることになります。
//
// ## この検査の限界
//
// **見つけられるのは、リポジトリに残った参照だけです。**
//
// **発行そのものは検出できません。** 今回の事故は、発行しても**リポジトリに痕跡が
// 残らなかった**ために、起票まで誰も気づきませんでした。**発行の遮断は
// `.claude/settings.json` の `permissions` で行います。本検査はその代わりにはなりません。**
//
// この限界を出力へ毎回書きます。**「検査が通ったから外部へ出していない」と読まれると、
// 検査が実態より広い保証をしているように見えるためです。**
//
// 出力の原則:
//   - 0件のときも0件であることを出力する
//   - 除外した行は理由とともに出力する

import fs from 'node:fs';
import path from 'node:path';
import { ROOT, fail, notice } from './config.mjs';

const CONFIG_PATH = path.join(ROOT, 'scripts/gate/external-hosts.json');

if (!fs.existsSync(CONFIG_PATH)) {
  fail('scripts/gate/external-hosts.json がありません。検出するホストを書いてください');
  process.exit(1);
}
const config = JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf8'));

const HOSTS = config.deniedHosts ?? [];
if (!HOSTS.length) {
  fail(
    'external-hosts.json の deniedHosts が空です。0件のまま通すと、' +
      '検査を実施していない状態を通過した記録として残ります'
  );
  process.exit(1);
}

const ALLOW = config.allowMarker ? new RegExp(config.allowMarker) : null;
const targets = process.argv.slice(2).length ? process.argv.slice(2) : (config.targets ?? ['docs']);

function walk(p, out) {
  if (!fs.existsSync(p)) return;
  const st = fs.statSync(p);
  if (st.isFile()) {
    out.push(p);
    return;
  }
  for (const e of fs.readdirSync(p, { withFileTypes: true })) {
    const full = path.join(p, e.name);
    if (e.isDirectory()) walk(full, out);
    else if (e.name.endsWith('.md')) out.push(full);
  }
}

const files = [];
for (const t of targets) walk(path.resolve(ROOT, t), files);

if (!files.length) {
  notice(`検査対象がありません(${targets.join(', ')})`);
  process.exit(0);
}

let hits = 0;
const allowed = [];

for (const f of files) {
  const rel = path.relative(ROOT, f).split(path.sep).join('/');
  const lines = fs.readFileSync(f, 'utf8').split(/\r?\n/);

  lines.forEach((line, i) => {
    const found = HOSTS.filter((h) => line.includes(h));
    if (!found.length) return;

    const m = ALLOW ? line.match(ALLOW) : null;
    if (m) {
      allowed.push({ rel, line: i + 1, hosts: found, reason: m.groups?.reason ?? '' });
      return;
    }
    for (const h of found) {
      hits++;
      fail(
        `${rel}:${i + 1} 組織の管理外のホスト "${h}" への参照があります。` +
          '決裁資料・レビュー資料の置き場はリポジトリ内です(#115)。' +
          '記録として書く必要がある場合は、行末へ `<!-- external-host-ok: 理由 -->` を付けてください'
      );
    }
  });
}

console.log(`検査したファイル: ${files.length} 件`);
console.log(`検出するホスト: ${HOSTS.length} 件`);

if (allowed.length) {
  console.log(`\n理由を添えて除外した行: ${allowed.length} 件`);
  for (const a of allowed) console.log(`  ${a.rel}:${a.line}  ${a.hosts.join(', ')}  ${a.reason}`);
} else {
  console.log('\n理由を添えて除外した行: 0 件');
}

console.log(`\n組織の管理外のホストへの参照: ${hits} 件`);
console.log(
  '\n【この検査の限界】見つけられるのはリポジトリに残った参照だけです。' +
    '発行そのものは検出できません。発行の遮断は .claude/settings.json の permissions で行います'
);

notice(`external-host-check: ${files.length} ファイルを検査、${hits} 件検出`);
process.exit(hits ? 1 : 0);
