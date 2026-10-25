// F-001 受入基準11(画面の側): 一覧を開いたとき、残日数を含む一覧を API から取る
import { describe, expect, it } from 'vitest';
import { fetchTrash } from './api';

describe('fetchTrash', () => {
	it('/api/trash から残日数を含む一覧を取る', async () => {
		const calls: string[] = [];
		const fake = (async (url: string) => {
			calls.push(url);
			return new Response(
				JSON.stringify([{ path: 'a.txt', trashed_at: '2026-10-25T00:00:00Z', remaining_days: 7 }]),
				{ status: 200, headers: { 'content-type': 'application/json' } }
			);
		}) as typeof fetch;

		const items = await fetchTrash(fake);

		expect(calls).toEqual(['/api/trash']);
		expect(items[0].remaining_days).toBe(7);
	});

	it('API が失敗したら例外にする(空の一覧に見せない)', async () => {
		const fake = (async () => new Response('', { status: 500 })) as typeof fetch;
		await expect(fetchTrash(fake)).rejects.toThrow();
	});
});
