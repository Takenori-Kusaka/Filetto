<script lang="ts">
	import { fetchTrash } from '../../lib/api';
	import TrashList from '../../lib/TrashList.svelte';
</script>

<h1>ゴミ箱</h1>

{#await fetchTrash()}
	<p>読み込み中</p>
{:then items}
	<TrashList {items} />
{:catch error}
	<p>{error.message}</p>
{/await}
