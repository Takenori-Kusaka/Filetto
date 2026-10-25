// F-001 受入基準5(画面の側): ゴミ箱の各項目から復元を実行できる
import { render } from 'svelte/server';
import { describe, expect, it } from 'vitest';
import TrashList from './TrashList.svelte';

describe('ゴミ箱の一覧の復元の操作', () => {
	it('各項目に復元のボタンを置く', () => {
		const { body } = render(TrashList, {
			props: {
				items: [
					{ path: 'a.txt', trashed_at: '2026-10-25T00:00:00Z', remaining_days: 7 },
					{ path: 'b.txt', trashed_at: '2026-10-25T00:00:00Z', remaining_days: null }
				],
				onrestore: () => {}
			}
		});
		const rows = body.split('<li').slice(1);
		expect(rows).toHaveLength(2);
		for (const row of rows) expect(row).toMatch(/<button[^>]*>復元<\/button>/);
	});
});
