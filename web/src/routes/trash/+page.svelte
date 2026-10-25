<script lang="ts">
	import { deleteFile, fetchTrash, restoreFile } from '../../lib/api';
	import TrashList from '../../lib/TrashList.svelte';

	// 操作の結果は一覧の上の文で示す。トースト・ポップアップは使わない(受入基準12)
	let listing = $state(fetchTrash());
	let message = $state('');
	let target = $state('');

	const reload = () => {
		listing = fetchTrash();
	};

	async function remove(event: SubmitEvent) {
		event.preventDefault();
		const path = target.trim();
		if (!path) return;
		try {
			await deleteFile(path);
			message = `${path} をゴミ箱へ移した`;
			target = '';
		} catch (e) {
			message = (e as Error).message;
		}
		reload();
	}

	async function restore(path: string) {
		try {
			await restoreFile(path);
			message = `${path} を削除前の場所へ戻した`;
		} catch (e) {
			// 409(同名衝突)も含め、API の理由をそのまま示す。復元は行われていない
			message = (e as Error).message;
		}
		reload();
	}
</script>

<h1>ゴミ箱</h1>

<form onsubmit={remove}>
	<label>
		削除するファイル(原本ディレクトリからの相対パス)
		<input bind:value={target} placeholder="docs/a.txt" />
	</label>
	<button type="submit">ゴミ箱へ移す</button>
</form>

{#if message}
	<p>{message}</p>
{/if}

{#await listing}
	<p>読み込み中</p>
{:then items}
	<TrashList {items} onrestore={restore} />
{:catch error}
	<p>{error.message}</p>
{/await}
