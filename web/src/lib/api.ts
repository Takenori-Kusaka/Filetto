// /api/** の JSON を取る。画面のための別の API の層は作らない(ADR-0003)

export type TrashItem = {
	path: string;
	trashed_at: string;
	// 完全削除までの残日数。無期限なら null
	remaining_days: number | null;
};

// 復元先に同名のファイルがある(API の 409)。復元は行われていない
export class RestoreConflictError extends Error {}

// パスの区切りは残し、各部分だけを符号化する
const encodePath = (path: string) => path.split('/').map(encodeURIComponent).join('/');

export async function fetchTrash(fetcher: typeof fetch = fetch): Promise<TrashItem[]> {
	const res = await fetcher('/api/trash');
	if (!res.ok) throw new Error(`ゴミ箱の一覧を取れない(HTTP ${res.status})`);
	return res.json();
}

// 削除はゴミ箱への移動。原本の実体は消えない
export async function deleteFile(path: string, fetcher: typeof fetch = fetch): Promise<TrashItem> {
	const res = await fetcher(`/api/files/${encodePath(path)}`, { method: 'DELETE' });
	if (!res.ok) throw new Error(`${path} を削除できない(HTTP ${res.status})`);
	return res.json();
}

export async function restoreFile(path: string, fetcher: typeof fetch = fetch): Promise<TrashItem> {
	const res = await fetcher(`/api/trash/${encodePath(path)}/restore`, { method: 'POST' });
	if (res.status === 409) {
		throw new RestoreConflictError(`${path} に同名のファイルがあるため、復元しなかった`);
	}
	if (!res.ok) throw new Error(`${path} を復元できない(HTTP ${res.status})`);
	return res.json();
}
