<script lang="ts">
  import { onMount } from "svelte";

  import { calibration, hardwareStatus, refreshStatus, startEventStream } from "./lib/stores";
  import LiveControl from "./views/LiveControl.svelte";
  import Library from "./views/Library.svelte";
  import Monitor from "./views/Monitor.svelte";
  import Planner from "./views/Planner.svelte";

  type View = "live" | "planner" | "monitor" | "library";

  const tabs: Array<{ id: View; label: string }> = [
    { id: "live", label: "Live Control" },
    { id: "planner", label: "Planner" },
    { id: "monitor", label: "Monitor" },
    { id: "library", label: "Library" },
  ];

  let view: View = "planner";

  onMount(() => {
    startEventStream();
    void refreshStatus();
  });
</script>

<svelte:head>
  <title>CameraCommander2</title>
</svelte:head>

<main class="min-h-screen px-4 py-5 md:px-8">
  <section class="mx-auto max-w-7xl overflow-hidden rounded-[2rem] border border-stone-900/10 bg-white/70 shadow-2xl shadow-stone-900/10 backdrop-blur">
    <header class="grid gap-5 bg-[#17211f] px-6 py-6 text-[#f8f1e5] md:grid-cols-[1fr_auto] md:px-8">
      <div>
        <p class="text-xs uppercase tracking-[0.45em] text-amber-200/80">CameraCommander2</p>
        <h1 class="mt-2 text-3xl font-black tracking-tight md:text-5xl">Motion shoot console</h1>
      </div>
      <div class="grid gap-2 text-sm md:min-w-72">
        <div class="rounded-2xl bg-white/10 px-4 py-3">
          <span class="text-stone-300">Camera</span>
          <strong class="float-right">{$hardwareStatus?.camera.state ?? "unknown"}</strong>
        </div>
        <div class="rounded-2xl bg-white/10 px-4 py-3">
          <span class="text-stone-300">Tripod</span>
          <strong class="float-right">{$hardwareStatus?.tripod.state ?? "unknown"}</strong>
        </div>
        <div class="rounded-2xl bg-white/10 px-4 py-3">
          <span class="text-stone-300">Calibration</span>
          <strong class="float-right">{$calibration}</strong>
        </div>
      </div>
    </header>

    <nav class="flex gap-2 overflow-x-auto border-b border-stone-900/10 bg-stone-50 px-4 py-3">
      {#each tabs as tab}
        <button
          class={`rounded-full px-4 py-2 text-sm font-bold transition ${
            view === tab.id ? "bg-amber-500 text-stone-950" : "bg-white text-stone-700 hover:bg-stone-100"
          }`}
          on:click={() => (view = tab.id)}
        >
          {tab.label}
        </button>
      {/each}
    </nav>

    <div class="p-4 md:p-8">
      {#if view === "live"}
        <LiveControl />
      {:else if view === "planner"}
        <Planner />
      {:else if view === "monitor"}
        <Monitor />
      {:else}
        <Library on:reloadPlanner={() => (view = "planner")} />
      {/if}
    </div>
  </section>
</main>
