// scripts/gate/license-check.mjs の判定を検証します。
//
//   node --test tests/gate/license-check.test.mjs
//
// CI では tests/gate/test_license_check.py が pytest から本ファイルを起動します。
// 検査の装置そのものを検査します。通ってはならないものが通らないことを、
// 肯定と否定の両方で確かめます。

import test from 'node:test';
import assert from 'node:assert/strict';
import { check, evaluateExpression, resolveLicense } from '../../scripts/gate/license-check.mjs';

const ALLOWED = ['MIT', 'Apache-2.0', 'BSD-2-Clause', 'BSD-3-Clause', 'ISC', 'MPL-2.0', 'PSF-2.0'];

const pkg = (name, fields) => ({
  Name: name,
  Version: '1.0.0',
  'License-Expression': 'UNKNOWN',
  'License-Metadata': 'UNKNOWN',
  'License-Classifier': 'UNKNOWN',
  ...fields,
});

test('SPDX 式: OR はいずれかが許可範囲にあれば通す', () => {
  assert.equal(evaluateExpression('Apache-2.0 OR BSD-3-Clause', ALLOWED), true);
  assert.equal(evaluateExpression('GPL-3.0-only OR MIT', ALLOWED), true);
  assert.equal(evaluateExpression('GPL-3.0-only OR LGPL-3.0-only', ALLOWED), false);
});

test('SPDX 式: AND はすべてが許可範囲にある必要がある', () => {
  assert.equal(evaluateExpression('MIT AND Apache-2.0', ALLOWED), true);
  assert.equal(evaluateExpression('MIT AND GPL-3.0-only', ALLOWED), false);
});

test('SPDX 式: AND は OR より強く結合する', () => {
  assert.equal(evaluateExpression('GPL-3.0-only AND LGPL-3.0-only OR MIT', ALLOWED), true);
  assert.equal(evaluateExpression('MIT OR GPL-3.0-only AND LGPL-3.0-only', ALLOWED), true);
  assert.equal(evaluateExpression('MIT AND GPL-3.0-only OR LGPL-3.0-only', ALLOWED), false);
});

test('SPDX 式: 括弧が結合順序を上書きする', () => {
  assert.equal(evaluateExpression('(MIT AND GPL-3.0-only) OR Apache-2.0', ALLOWED), true);
  assert.equal(evaluateExpression('(MIT OR GPL-3.0-only) AND LGPL-3.0-only', ALLOWED), false);
  assert.equal(evaluateExpression('(MIT OR GPL-3.0-only) AND Apache-2.0', ALLOWED), true);
});

test('SPDX 式: WITH は1つの識別子として扱う', () => {
  assert.equal(evaluateExpression('GPL-2.0-only WITH Classpath-exception-2.0', ALLOWED), false);
  assert.equal(
    evaluateExpression('GPL-2.0-only WITH Classpath-exception-2.0', [
      ...ALLOWED,
      'GPL-2.0-only WITH Classpath-exception-2.0',
    ]),
    true
  );
});

test('SPDX 式: 部分一致では通さない', () => {
  assert.equal(evaluateExpression('MIT-0', ALLOWED), false);
  assert.equal(evaluateExpression('Apache-2.0-with-LLVM-exception', ALLOWED), false);
});

test('SPDX 式: 壊れた式は例外にする(黙って通さない)', () => {
  assert.throws(() => evaluateExpression('(MIT OR Apache-2.0', ALLOWED));
  assert.throws(() => evaluateExpression('MIT AND', ALLOWED));
  assert.throws(() => evaluateExpression('MIT WITH', ALLOWED));
});

test('読む順序: License-Expression を最優先する(PEP 639)', () => {
  const r = resolveLicense(
    pkg('x', { 'License-Expression': 'MIT', 'License-Metadata': 'Apache-2.0', 'License-Classifier': 'BSD License' })
  );
  assert.deepEqual(r, { license: 'MIT', source: 'License-Expression' });
});

test('読む順序: Expression が無ければ Metadata、無ければ Classifier', () => {
  assert.equal(resolveLicense(pkg('x', { 'License-Metadata': 'Apache-2.0' })).source, 'License-Metadata');
  assert.equal(resolveLicense(pkg('x', { 'License-Classifier': 'MIT License' })).source, 'License-Classifier');
});

test('読む順序: 3箇所すべて UNKNOWN なら特定できないとする', () => {
  assert.equal(resolveLicense(pkg('x', {})).license, null);
});

test('補正: 分類子・自由記述を SPDX へ直し、直したことを記録する', () => {
  const r = resolveLicense(pkg('x', { 'License-Classifier': 'MIT License' }));
  assert.equal(r.license, 'MIT');
  assert.equal(r.normalizedFrom, 'MIT License');

  const m = resolveLicense(pkg('x', { 'License-Metadata': 'PSFL' }));
  assert.equal(m.license, 'PSF-2.0');
  assert.equal(m.normalizedFrom, 'PSFL');
});

test('補正: 複数の SPDX を含みうる分類子には印を付ける', () => {
  assert.equal(resolveLicense(pkg('x', { 'License-Classifier': 'Apache Software License' })).ambiguous, true);
  assert.equal(resolveLicense(pkg('x', { 'License-Classifier': 'BSD License' })).ambiguous, true);
  assert.equal(resolveLicense(pkg('x', { 'License-Classifier': 'MIT License' })).ambiguous, undefined);
});

test('本件の発見の元: PyJWT と cryptography が通る(#60)', () => {
  const r = check(
    [
      pkg('PyJWT', { 'License-Expression': 'MIT' }),
      pkg('cryptography', { 'License-Expression': 'Apache-2.0 OR BSD-3-Clause' }),
    ],
    ALLOWED
  );
  assert.deepEqual(r.denied, []);
  assert.deepEqual(r.unresolved, []);
});

test('否定: 許可していない MIT-0 は落とす(--partial-match が通してしまうもの)', () => {
  const r = check([pkg('cffi', { 'License-Expression': 'MIT-0' })], ALLOWED);
  assert.equal(r.denied.length, 1);
  assert.equal(r.denied[0].license, 'MIT-0');
});

test('否定: ライセンスを特定できない依存は落とす', () => {
  const r = check([pkg('mystery', {})], ALLOWED);
  assert.equal(r.unresolved.length, 1);
  assert.equal(r.denied.length, 0);
});

test('自プロジェクトの除外は既定で行わない(検査範囲の変更は PO の判断)', () => {
  const self = [pkg('filetto', { 'License-Expression': 'AGPL-3.0-or-later' })];
  assert.equal(check(self, ALLOWED).denied.length, 1);
  assert.equal(check(self, ALLOWED, ['filetto']).denied.length, 0);
  assert.equal(check(self, ALLOWED, ['filetto']).skipped.length, 1);
});

test('自プロジェクトの照合は PyPI の正規化規則に従う', () => {
  const r = check([pkg('My_Project.Name', { 'License-Expression': 'AGPL-3.0-or-later' })], ALLOWED, [
    'my-project-name',
  ]);
  assert.equal(r.skipped.length, 1);
});

test('件数は取得した総数を返す', () => {
  const r = check([pkg('a', { 'License-Expression': 'MIT' }), pkg('b', { 'License-Expression': 'MIT' })], ALLOWED);
  assert.equal(r.total, 2);
});
