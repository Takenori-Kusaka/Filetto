// 二重エンコード(UTF-8をCP932として誤読し、UTF-8として保存し直した破損)を検出する(#27)。
//
//   node scripts/gate/double-encoding-check.mjs [対象ディレクトリ...]
//
// 既定の対象はリポジトリ全体。1文字でも出たら失敗させます。
// 破損後のファイルは妥当な UTF-8 のため、file コマンドや既存の検査では検出できません。

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { ROOT, fail, notice } from './config.mjs';

const BAD_CHARS = ['蠖', '縺', '繧', '繝', '蜿'];

const EXCLUDE_DIRS = new Set(['.git', 'node_modules', '.venv', 'dist', 'build']);
const BINARY_EXT = new Set([
  '.pdf', '.png', '.jpg', '.jpeg', '.gif', '.ico', '.doc', '.docx',
  '.xls', '.xlsx', '.ppt', '.pptx', '.zip', '.woff', '.woff2', '.ttf',
]);
// これらは検査すべき文字そのものを、検査の仕様として本文に含む
const EXCLUDE_FILES = new Set([
  'docs/session-definitions/README.md',
  'docs/session-definitions/platform.md',
  '.claude/skills/platform/SKILL.md',
  path.relative(ROOT, fileURLToPath(import.meta.url)).split(path.sep).join('/'),
]);

const targets = process.argv.slice(2).length ? process.argv.slice(2) : ['.'];

function walk(dir, out) {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    if (EXCLUDE_DIRS.has(e.name)) continue;
    const p = path.join(dir, e.name);
    if (e.isDirectory()) walk(p, out);
    else if (!BINARY_EXT.has(path.extname(e.name))) out.push(p);
  }
}

const files = [];
for (const t of targets) walk(path.join(ROOT, t), files);

let hits = 0;
let scanned = 0;

for (const f of files) {
  const rel = path.relative(ROOT, f).split(path.sep).join('/');
  if (EXCLUDE_FILES.has(rel)) continue;
  let text;
  try {
    text = fs.readFileSync(f, 'utf8');
  } catch {
    continue;
  }
  scanned++;
  const lines = text.split(/\r?\n/);
  lines.forEach((line, i) => {
    for (const c of BAD_CHARS) {
      let idx = line.indexOf(c);
      while (idx >= 0) {
        hits++;
        fail(`${rel}:${i + 1}:${idx + 1} 二重エンコードの疑い(文字 "${c}")`);
        idx = line.indexOf(c, idx + 1);
      }
    }
  });
}

notice(`double-encoding-check: ${scanned} ファイルを検査、${hits} 件検出`);
process.exit(hits ? 1 : 0);
