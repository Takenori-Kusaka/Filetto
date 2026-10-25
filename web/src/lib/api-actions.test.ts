// F-001 受入基準2・5・6(画面の側)。受入基準だけを入力に書いた検査
import { describe, expect, it } from 'vitest';
import { RestoreConflictError, deleteFile, restoreFile } from './api';

type Call = { url: string; method: string };

const fakeFetch = (status: number, calls: Call[]) =>
	(async (url: string, init?: RequestInit) => {
		calls.push({ url, method: init?.method ?? 'GET' });
		const body = status < 400 ? { path: 'x', trashed_at: '2026-10-25T00:00:00Z', remaining_days: 30 } : { detail: 'ng' };
		return new Response(JSON.stringify(body), {
			status,
			headers: { 'content-type': 'application/json' }
		});
	}) as typeof fetch;

describe('画面からの削除(受入基準2)', () => {
	it('削除は DELETE /api/files/<パス> でゴミ箱へ移す', async () => {
		const calls: Call[] = [];
		await deleteFile('docs/a b.txt', fakeFetch(200, calls));
		expect(calls).toEqual([{ url: '/api/files/docs/a%20b.txt', method: 'DELETE' }]);
	});

	it('削除が失敗したら例外にする', async () => {
		await expect(deleteFile('none.txt', fakeFetch(404, []))).rejects.toThrow();
	});
});

describe('画面からの復元(受入基準5・6)', () => {
	it('復元は POST /api/trash/<パス>/restore で削除前のパスへ戻す', async () => {
		const calls: Call[] = [];
		await restoreFile('docs/a b.txt', fakeFetch(200, calls));
		expect(calls).toEqual([{ url: '/api/trash/docs/a%20b.txt/restore', method: 'POST' }]);
	});

	it('409 は同名衝突として区別した例外にする', async () => {
		const err = await restoreFile('a.txt', fakeFetch(409, [])).catch((e) => e);
		expect(err).toBeInstanceOf(RestoreConflictError);
		expect(err.message).toContain('同名のファイル');
	});

	it('409 以外の失敗は同名衝突として扱わない', async () => {
		const err = await restoreFile('a.txt', fakeFetch(404, [])).catch((e) => e);
		expect(err).toBeInstanceOf(Error);
		expect(err).not.toBeInstanceOf(RestoreConflictError);
	});
});
