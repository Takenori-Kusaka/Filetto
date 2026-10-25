<script lang="ts">
	import type { TrashItem } from './api';

	// 残日数は一覧の中の文字だけで示す。完全削除の予告をトースト・ポップアップ・バッジで出さない(受入基準12)
	let { items }: { items: TrashItem[] } = $props();

	const remaining = (days: number | null) => (days === null ? '無期限' : `残り ${days} 日`);
</script>

{#if items.length === 0}
	<p>ゴミ箱は空です</p>
{:else}
	<ul>
		{#each items as item (item.path)}
			<li>
				<span>{item.path}</span>
				<span>{remaining(item.remaining_days)}</span>
			</li>
		{/each}
	</ul>
{/if}
