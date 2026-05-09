<script lang="ts">
  import { createEventDispatcher, onMount } from "svelte";

  import { api, ApiError } from "../lib/api/client";
  import type { Session, SessionSummary } from "../lib/api/types";
  import { plannerConfiguration } from "../lib/stores";

  const dispatch = createEventDispatcher<{ reloadPlanner: void }>();

  let items: SessionSummary[] = [];
  let total = 0;
  let tag = "";
  let selected: Session | null = null;
  let message = "";
  let busy = false;

  function describe(error: unknown, fallback: string): string {
    if (error instanceof ApiError) return `${error.payload.error}: ${error.message}`;
    if (error instanceof Error) return error.message;
    return fallback;
  }

  async function load(): Promise<void> {
    busy = true;
    try {
      const result = await api.sessions({ tag: tag || undefined });
      items = result.items;
      total = result.total;
      message = total ? `${total} session${total === 1 ? "" : "s"} found.` : "No sessions found.";
    } catch (error) {
      message = describe(error, "Failed to load sessions");
    } finally {
      busy = false;
    }
  }

  async function inspect(sessionId: string): Promise<void> {
    busy = true;
    try {
      selected = await api.session(sessionId);
      message = `Inspecting ${selected.name ?? selected.session_id}.`;
    } catch (error) {
      message = describe(error, "Failed to inspect session");
    } finally {
      busy = false;
    }
  }

  async function reloadPlanner(): Promise<void> {
    if (!selected) return;
    try {
      const config = await api.sessionConfig(selected.session_id);
      plannerConfiguration.set(config);
      dispatch("reloadPlanner");
      message = "Configuration loaded into Planner.";
    } catch (error) {
      message = describe(error, "Failed to reload configuration");
    }
  }

  async function assemble(): Promise<void> {
    if (!selected) return;
    busy = true;
    try {
      selected = await api.assembleSession(selected.session_id);
      message = "Video assembly queued/completed.";
      await load();
    } catch (error) {
      message = describe(error, "Failed to assemble video");
    } finally {
      busy = false;
    }
  }

  async function remove(sessionId: string): Promise<void> {
    busy = true;
    try {
      await api.deleteSession(sessionId);
      if (selected?.session_id === sessionId) selected = null;
      await load();
      message = "Session deleted.";
    } catch (error) {
      message = describe(error, "Failed to delete session");
    } finally {
      busy = false;
    }
  }

  function assetUrl(path: string): string {
    if (!selected) return "#";
    return `/api/sessions/${selected.session_id}/assets/${encodeURIComponent(path)}`;
  }

  onMount(() => {
    void load();
  });
</script>

<section class="grid gap-6 xl:grid-cols-[1fr_0.85fr]">
  <div class="rounded-3xl bg-white p-6 shadow-sm">
    <div class="flex flex-wrap items-start justify-between gap-4">
      <div>
        <p class="text-xs font-bold uppercase tracking-[0.35em] text-amber-700">Library</p>
        <h2 class="mt-2 text-2xl font-black">Session library</h2>
      </div>
      <button class="rounded-full border px-4 py-2 font-bold" disabled={busy} on:click={load}>Refresh</button>
    </div>

    <div class="mt-5 flex flex-wrap gap-3">
      <input class="rounded-xl border p-3" placeholder="Filter tag" bind:value={tag} />
      <button class="rounded-full bg-stone-900 px-5 py-3 font-black text-white" disabled={busy} on:click={load}>Apply</button>
    </div>

    <div class="mt-5 overflow-hidden rounded-2xl border">
      <table class="w-full text-left text-sm">
        <thead class="bg-stone-100 text-xs uppercase tracking-[0.2em] text-stone-500">
          <tr>
            <th class="p-3">Session</th>
            <th class="p-3">Frames</th>
            <th class="p-3">Flags</th>
            <th class="p-3">Actions</th>
          </tr>
        </thead>
        <tbody>
          {#each items as session}
            <tr class="border-t">
              <td class="p-3">
                <strong>{session.name ?? session.session_id}</strong>
                <span class="block text-xs text-stone-500">{new Date(session.created_at).toLocaleString()} · {session.kind}</span>
              </td>
              <td class="p-3">{session.frames_captured ?? 0} / {session.frames_planned ?? 0}</td>
              <td class="p-3">
                {#each Object.entries(session.flags ?? {}).filter(([, enabled]) => enabled) as [flag]}
                  <span class="mr-1 rounded-full bg-amber-100 px-2 py-1 text-xs font-bold text-amber-800">{flag}</span>
                {/each}
              </td>
              <td class="p-3">
                <button class="rounded-full border px-3 py-1 font-bold" on:click={() => inspect(session.session_id)}>Inspect</button>
                <button class="ml-2 rounded-full border px-3 py-1 font-bold text-red-700" on:click={() => remove(session.session_id)}>Delete</button>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>

    <p class="mt-4 rounded-2xl bg-stone-100 p-4 text-sm text-stone-700">{message}</p>
  </div>

  <aside class="rounded-3xl bg-[#17211f] p-6 text-[#f8f1e5] shadow-sm">
    <h3 class="text-xl font-black">Inspector</h3>
    {#if selected}
      <p class="mt-3 font-mono text-xs text-stone-300">{selected.session_id}</p>
      <h4 class="mt-2 text-2xl font-black">{selected.name ?? "Unnamed session"}</h4>
      <p class="mt-2 text-sm text-stone-300">{selected.status} · {selected.kind}</p>
      <div class="mt-5 flex flex-wrap gap-3">
        <button class="rounded-full bg-white px-4 py-2 font-bold text-stone-950" on:click={reloadPlanner}>Reload settings</button>
        <button class="rounded-full bg-amber-500 px-4 py-2 font-bold text-stone-950" disabled={busy} on:click={assemble}>Assemble video</button>
      </div>

      <h5 class="mt-6 font-black">Assets</h5>
      <div class="mt-2 grid gap-2">
        {#each selected.assets as asset}
          <a class="rounded-2xl bg-white/10 p-3 text-sm hover:bg-white/15" href={assetUrl(asset.path)} target="_blank" rel="noreferrer">
            <strong>{asset.kind}</strong>
            <span class="block truncate text-stone-300">{asset.path}</span>
          </a>
        {/each}
      </div>

      <h5 class="mt-6 font-black">Configuration</h5>
      <pre class="mt-2 max-h-80 overflow-auto rounded-2xl bg-black/30 p-3 text-xs">{JSON.stringify(selected.configuration, null, 2)}</pre>
    {:else}
      <p class="mt-4 text-stone-300">Select a session to inspect metadata, assets, and the original configuration.</p>
    {/if}
  </aside>
</section>
