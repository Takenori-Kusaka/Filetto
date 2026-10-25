// F-001 受入基準11・12(画面の側)。受入基準だけを入力に書いた検査
import { render } from 'svelte/server';
import { describe, expect, it } from 'vitest';
import TrashList from './TrashList.svelte';
import type { TrashItem } from './api';

const item = (path: string, remaining_days: number | null): TrashItem => ({
	path,
	trashed_at: '2026-10-25T00:00:00Z',
	remaining_days
});

const rowOf = (body: string, path: string): string => {
	const row = body.split('<li').find((r) => r.includes(path));
	if (!row) throw new Error(`${path} の行が無い`);
	return row;
};

describe('ゴミ箱の一覧(受入基準11)', () => {
	it('各項目に完全削除までの残日数を表示する', () => {
		const { body } = render(TrashList, {
			props: { items: [item('docs/a.txt', 7), item('b.txt', 0)] }
		});
		expect(rowOf(body, 'docs/a.txt')).toContain('残り 7 日');
		expect(rowOf(body, 'b.txt')).toContain('残り 0 日');
	});

	it('無期限の項目は無期限と表示する', () => {
		const { body } = render(TrashList, { props: { items: [item('c.txt', null)] } });
		expect(rowOf(body, 'c.txt')).toContain('無期限');
	});

	it('ゴミ箱が空ならその旨を表示する', () => {
		const { body } = render(TrashList, { props: { items: [] } });
		expect(body).toContain('ゴミ箱は空です');
	});
});

describe('完全削除の予告を通知しない(受入基準12)', () => {
	it('期限の近い項目でもトースト・ポップアップ・バッジの要素を出さない', () => {
		const { body } = render(TrashList, {
			props: { items: [item('a.txt', 1), item('b.txt', 0)] }
		});
		expect(body).not.toMatch(/role="(alert|alertdialog|status|dialog)"/);
		expect(body).not.toMatch(/aria-live|<dialog|popover/);
		expect(body).not.toMatch(/class="[^"]*(toast|badge|popup|snackbar)/i);
	});
});
