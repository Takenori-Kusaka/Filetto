// /api/** の JSON を取る。画面のための別の API の層は作らない(ADR-0003)

export type TrashItem = {
	path: string;
	trashed_at: string;
	// 完全削除までの残日数。無期限なら null
	remaining_days: number | null;
};

export async function fetchTrash(fetcher: typeof fetch = fetch): Promise<TrashItem[]> {
	const res = await fetcher('/api/trash');
	if (!res.ok) throw new Error(`ゴミ箱の一覧を取れない(HTTP ${res.status})`);
	return res.json();
}
