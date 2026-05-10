<script lang="ts">
  import { onMount } from "svelte";

  import { calibration, hardwareStatus, refreshStatus, startEventStream } from "./lib/stores";
  import LiveControl from "./views/LiveControl.svelte";
  import Library from "./views/Library.svelte";
  import Monitor from "./views/Monitor.svelte";
  import Planner from "./views/Planner.svelte";

  let view = $state("live");

  onMount(() => {
    void refreshStatus();
    startEventStream();
  });
</script>

<main class="min-h-screen bg-stone-50 font-sans text-stone-900">
  <header class="bg-stone-900 px-6 py-4 text-white flex justify-between items-center">
    <h1 class="text-xl font-bold tracking-tight">CameraCommander2</h1>
    <div class="flex gap-4 text-xs uppercase tracking-widest font-bold">
      <span class="text-stone-400">
        Cam:
        <span class={$hardwareStatus?.camera.state === "connected" ? "text-green-400" : "text-red-400"}>
          {$hardwareStatus?.camera.state ?? "disconnected"}
        </span>
      </span>
      <span class="text-stone-400">
        Tripod:
        <span class={$calibration === "homed" ? "text-green-400" : "text-amber-400"}>
          {$calibration}
        </span>
      </span>
    </div>
  </header>

  <nav class="bg-white border-b border-stone-200 px-6 flex gap-8">
    <button class="py-4 border-b-2 font-medium {view === 'live' ? 'border-orange-500 text-stone-900' : 'border-transparent text-stone-500'}" onclick={() => view = 'live'}>Live Control</button>
    <button class="py-4 border-b-2 font-medium {view === 'planner' ? 'border-orange-500 text-stone-900' : 'border-transparent text-stone-500'}" onclick={() => view = 'planner'}>Planner</button>
    <button class="py-4 border-b-2 font-medium {view === 'monitor' ? 'border-orange-500 text-stone-900' : 'border-transparent text-stone-500'}" onclick={() => view = 'monitor'}>Monitor</button>
    <button class="py-4 border-b-2 font-medium {view === 'library' ? 'border-orange-500 text-stone-900' : 'border-transparent text-stone-500'}" onclick={() => view = 'library'}>Library</button>
  </nav>

  <section class="p-6">
    {#if view === 'live'}
      <LiveControl />
    {:else if view === 'planner'}
      <Planner />
    {:else if view === 'monitor'}
      <Monitor />
    {:else}
      <Library />
    {/if}
  </section>
</main>
