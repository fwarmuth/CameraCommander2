<script lang="ts">
  import { onMount } from "svelte";

  import { api, ApiError } from "../lib/api/client";
  import type { CameraSettings } from "../lib/api/types";
  import { hardwareStatus, refreshStatus } from "../lib/stores";

  let settings: CameraSettings = $state({});
  let pending: Record<string, string | number | boolean> = $state({});
  let search = $state("");
  let stepDeg = $state(1);
  let autofocus = $state(false);
  let captureUrl = $state("");
  let message = $state("Load camera settings to begin.");
  let busy = $state(false);
  let activeTab = $state("Planning");
  let collapsedGroups = $state(new Set<string>());

  const planningKeys = [
    "main.imgsettings.iso",
    "main.capturesettings.shutterspeed",
    "main.capturesettings.aperture",
    "main.imgsettings.whitebalance",
    "main.capturesettings.exposurecompensation",
    "main.capturesettings.focusmode",
    "main.imgsettings.imageformat",
    "main.imgsettings.imageformatcf",
    "main.imgsettings.imageformatsd",
    "main.imgsettings.imagequality",
    "main.settings.datetime",
  ];

  let cameraFault = $derived(
    $hardwareStatus?.camera.state === "error" || $hardwareStatus?.camera.state === "disconnected"
  );
  let tripodFault = $derived(
    $hardwareStatus?.tripod.state === "error" || $hardwareStatus?.tripod.state === "disconnected"
  );
  let tiltMin = $derived($hardwareStatus?.tripod.tilt_min_deg ?? -90);
  let tiltMax = $derived($hardwareStatus?.tripod.tilt_max_deg ?? 90);
  let currentTilt = $derived($hardwareStatus?.tripod.position_tilt_deg ?? 0);
  let canTiltDown = $derived(currentTilt - stepDeg >= tiltMin);
  let canTiltUp = $derived(currentTilt + stepDeg <= tiltMax);

  let groups = $derived(Object.keys(settings).reduce(
    (acc, key) => {
      if (search && !key.toLowerCase().includes(search.toLowerCase())) return acc;
      
      const parts = key.split(".");
      const tabName = parts.length > 1 ? parts[1] : "other";
      if (!acc[tabName]) acc[tabName] = {};
      
      const subGroup = parts.length > 2 ? parts.slice(2, -1).join(".") || "general" : "general";
      if (!acc[tabName][subGroup]) acc[tabName][subGroup] = [];
      acc[tabName][subGroup].push(key);
      
      return acc;
    },
    {} as Record<string, Record<string, string[]>>,
  ));

  let tabs = $derived(["Planning", ...Object.keys(groups).sort()]);

  function getSubGroups(tab: string): Record<string, string[]> {
    if (tab === "Planning") {
      const essential = Object.keys(settings).filter((k) => {
        const lower = k.toLowerCase();
        return (
          planningKeys.includes(k) ||
          lower.includes("iso") ||
          lower.includes("shutter") ||
          lower.includes("aperture") ||
          lower.includes("whitebalance") ||
          lower.includes("imageformat")
        );
      });
      return { "Essential Shoot Settings": essential };
    }
    return groups[tab] || {};
  }

  function describe(error: unknown, fallback: string): string {
    if (error instanceof ApiError) return `${error.payload.error}: ${error.message}`;
    if (error instanceof Error) return error.message;
    return fallback;
  }

  async function loadSettings(): Promise<void> {
    busy = true;
    try {
      settings = await api.cameraSettings();
      pending = Object.fromEntries(
        Object.entries(settings).map(([key, value]) => [key, value.current ?? ""]),
      );
      message = "Camera settings loaded.";
    } catch (error) {
      message = describe(error, "Failed to load settings");
    } finally {
      busy = false;
    }
  }

  async function applySettings(): Promise<void> {
    busy = true;
    try {
      settings = await api.updateCameraSettings(pending);
      message = "Camera settings applied.";
    } catch (error) {
      message = describe(error, "Failed to apply settings");
    } finally {
      busy = false;
    }
  }

  async function capture(): Promise<void> {
    busy = true;
    try {
      const result = await api.captureCamera(autofocus);
      captureUrl = result.download_url ?? `/api/camera/captures/${result.capture_id}`;
      message = `Captured ${Math.round(result.size_bytes / 1024)} KiB.`;
    } catch (error) {
      message = describe(error, "Capture failed");
    } finally {
      busy = false;
    }
  }

  async function nudge(deltaPan: number, deltaTilt: number): Promise<void> {
    busy = true;
    try {
      await api.nudgeTripod(deltaPan, deltaTilt);
      await refreshStatus();
      message = `Nudged pan ${deltaPan}, tilt ${deltaTilt}.`;
    } catch (error) {
      message = describe(error, "Nudge failed");
    } finally {
      busy = false;
    }
  }

  async function stop(): Promise<void> {
    busy = true;
    try {
      await api.stopTripod();
      await refreshStatus();
      message = "Tripod stop sent.";
    } catch (error) {
      message = describe(error, "Stop failed");
    } finally {
      busy = false;
    }
  }

  async function toggleDrivers(): Promise<void> {
    if (!$hardwareStatus?.tripod) return;
    busy = true;
    try {
      await api.setTripodDrivers(!$hardwareStatus.tripod.drivers_enabled);
      await refreshStatus();
      message = `Tripod drivers ${$hardwareStatus.tripod.drivers_enabled ? "enabled" : "disabled"}.`;
    } catch (error) {
      message = describe(error, "Failed to toggle drivers");
    } finally {
      busy = false;
    }
  }

  function toggleCollapse(group: string) {
    if (collapsedGroups.has(group)) {
      collapsedGroups.delete(group);
    } else {
      collapsedGroups.add(group);
    }
    collapsedGroups = new Set(collapsedGroups); // Trigger reactivity in Svelte 5
  }

  onMount(() => {
    void loadSettings();
  });
</script>

<section class="grid gap-6 xl:grid-cols-[1fr_0.9fr]">
  <div class="grid gap-6">
    <div class="rounded-3xl bg-white p-6 shadow-sm flex flex-col">
      <div class="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p class="text-xs font-bold uppercase tracking-[0.35em] text-amber-700">Live Control</p>
          <h2 class="mt-2 text-2xl font-black">Camera settings</h2>
        </div>
        <div class="flex gap-2">
           <input type="text" placeholder="Search settings..." class="rounded-full border border-stone-200 px-4 py-2 text-sm focus:border-amber-500 focus:outline-none focus:ring-2 focus:ring-amber-500/20" bind:value={search} />
           <button class="rounded-full border px-4 py-2 font-bold hover:bg-stone-50 transition" disabled={busy} onclick={loadSettings}>Reload</button>
        </div>
      </div>

      {#if cameraFault}
        <p class="mt-4 rounded-2xl bg-red-100 p-3 font-bold text-red-800 border border-red-200">Camera is {$hardwareStatus?.camera.state ?? "unknown"}; capture controls are disabled.</p>
      {/if}

      <nav class="mt-6 flex gap-1 overflow-x-auto rounded-2xl bg-stone-100 p-1 no-scrollbar">
        {#each tabs as tab}
          <button
            class={`whitespace-nowrap rounded-xl px-3 py-1.5 text-xs font-bold transition ${
              activeTab === tab ? "bg-white text-stone-900 shadow-sm" : "text-stone-500 hover:text-stone-700"
            }`}
            onclick={() => (activeTab = tab)}
          >
            {tab === "Planning" ? "Planning" : tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        {/each}
      </nav>

      <div class="mt-4 flex-grow grid max-h-[32rem] gap-6 overflow-auto pr-2 custom-scrollbar">
        {#each Object.entries(getSubGroups(activeTab)) as [subGroup, keys]}
          <div class="grid gap-3">
            {#if subGroup}
              <button 
                class="flex items-center justify-between w-full group text-left"
                onclick={() => toggleCollapse(subGroup)}
              >
                <h4 class="text-[10px] font-black uppercase tracking-widest text-stone-400 group-hover:text-stone-600 transition">{subGroup.replace(".", " / ")}</h4>
                <span class="text-[10px] text-stone-300 group-hover:text-stone-500 transition">{collapsedGroups.has(subGroup) ? 'EXPAND' : 'COLLAPSE'}</span>
              </button>
            {/if}
            
            {#if !collapsedGroups.has(subGroup)}
              <div class="grid gap-3">
                {#each keys as key}
                  {@const descriptor = settings[key]}
                  <label class="grid gap-2 rounded-2xl border border-stone-200 p-3 md:grid-cols-[1fr_14rem] md:items-center hover:border-stone-300 transition-colors">
                    <span>
                      <strong class="block text-sm">{key.split(".").pop()}</strong>
                      <span class="text-[10px] uppercase tracking-wider text-stone-400 font-mono">{key}</span>
                    </span>
                    {#if descriptor.choices?.length}
                      <select class="rounded-xl border border-stone-300 bg-white p-2 text-sm focus:border-amber-500 focus:outline-none" bind:value={pending[key]}>
                        {#each descriptor.choices as choice}
                          <option value={choice}>{choice}</option>
                        {/each}
                      </select>
                    {:else if descriptor.type === 'RANGE'}
                      <div class="flex items-center gap-3">
                         <input type="range" class="grow accent-amber-500" min={descriptor.range?.min} max={descriptor.range?.max} step={descriptor.range?.step} bind:value={pending[key]} />
                         <span class="text-xs font-mono w-10 text-right tabular-nums">{pending[key]}</span>
                      </div>
                    {:else}
                      <input class="rounded-xl border border-stone-300 bg-white p-2 text-sm focus:border-amber-500 focus:outline-none" bind:value={pending[key]} />
                    {/if}
                  </label>
                {/each}
              </div>
            {/if}
          </div>
        {:else}
           <p class="py-12 text-center text-stone-400 text-sm italic">No settings found matching "{search}"</p>
        {/each}
      </div>

      <div class="mt-5 pt-5 border-t border-stone-100 flex flex-wrap items-center gap-4">
        <button class="rounded-full bg-stone-900 px-6 py-3 font-black text-white hover:bg-stone-800 active:scale-95 transition disabled:opacity-50" disabled={busy || cameraFault} onclick={applySettings}>Apply settings</button>
        <label class="flex items-center gap-2 font-bold text-sm cursor-pointer select-none">
            <input type="checkbox" class="w-4 h-4 rounded border-stone-300 text-amber-500 focus:ring-amber-500" bind:checked={autofocus} /> 
            Autofocus
        </label>
        <div class="flex-grow"></div>
        <button class="rounded-full bg-amber-500 px-6 py-3 font-black text-stone-950 hover:bg-amber-400 active:scale-95 transition disabled:opacity-50 shadow-sm shadow-amber-200" disabled={busy || cameraFault} onclick={capture}>Test capture</button>
      </div>
    </div>

    <div class="rounded-3xl bg-[#17211f] p-6 text-[#f8f1e5] shadow-md border border-stone-800">
      <div class="flex items-center justify-between mb-4">
          <h3 class="text-xl font-black">Live view</h3>
          <span class="flex h-2 w-2 rounded-full bg-green-500 animate-pulse"></span>
      </div>
      <img class="aspect-video w-full rounded-2xl bg-black object-contain ring-1 ring-white/10" src="/api/camera/preview/stream" alt="Camera live preview" />
      
      <div class="mt-6 grid grid-cols-2 md:grid-cols-3 gap-4 border-t border-stone-800 pt-6">
        {#each planningKeys.filter(k => settings[k]) as key}
          {@const descriptor = settings[key]}
          <div class="flex flex-col gap-1">
            <span class="text-[9px] font-black uppercase tracking-widest text-stone-500">{key.split(".").pop()}</span>
            {#if descriptor.choices?.length}
              <select 
                class="bg-transparent text-sm font-bold text-amber-200 border-none p-0 focus:ring-0 cursor-pointer hover:text-white transition-colors" 
                bind:value={pending[key]}
                onchange={() => applySettings()}
              >
                {#each descriptor.choices as choice}
                  <option class="bg-stone-900 text-white" value={choice}>{choice}</option>
                {/each}
              </select>
            {:else}
              <input 
                class="bg-transparent text-sm font-bold text-amber-200 border-none p-0 focus:ring-0 hover:text-white transition-colors" 
                bind:value={pending[key]}
                onchange={() => applySettings()}
              />
            {/if}
          </div>
        {/each}
      </div>

      {#if captureUrl}
        <div class="mt-4 flex justify-end">
            <a class="inline-flex items-center gap-2 rounded-full bg-white px-5 py-2.5 font-bold text-stone-950 hover:bg-stone-100 transition active:scale-95 shadow-lg" href={captureUrl} target="_blank" rel="noreferrer">
                <span>Open latest capture</span>
                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                </svg>
            </a>
        </div>
      {/if}
    </div>
  </div>

  <aside class="rounded-3xl bg-white p-6 shadow-sm border border-stone-100">
    <h3 class="text-xl font-black">Tripod nudge</h3>
    {#if tripodFault}
      <p class="mt-4 rounded-2xl bg-red-100 p-3 font-bold text-red-800 border border-red-200">Tripod is {$hardwareStatus?.tripod.state ?? "unknown"}; nudge controls are disabled.</p>
    {/if}

    <dl class="mt-5 grid gap-3 text-sm">
      <div class="rounded-2xl bg-stone-100 p-3">
        <dt class="text-[10px] font-black uppercase tracking-widest text-stone-400">Current Position</dt>
        <dd class="mt-1 text-lg font-bold tabular-nums tracking-tight text-stone-700">{($hardwareStatus?.tripod.position_pan_deg ?? 0).toFixed(2)}° pan / {currentTilt.toFixed(2)}° tilt</dd>
      </div>
      <div class="rounded-2xl bg-stone-100 p-3">
        <dt class="text-[10px] font-black uppercase tracking-widest text-stone-400">Safety window</dt>
        <dd class="mt-1 font-bold text-stone-600">{tiltMin}° to {tiltMax}° tilt</dd>
      </div>
    </dl>

    <div class="mt-8 flex items-end justify-between gap-4">
      <label class="grid grow gap-1.5">
        <span class="text-xs font-black uppercase tracking-widest text-stone-400">Step degrees</span>
        <input class="rounded-xl border border-stone-200 p-3 font-bold focus:border-amber-500 focus:outline-none transition tabular-nums" type="number" min="0.1" step="0.1" bind:value={stepDeg} />
      </label>
    </div>

    <div class="mt-8 grid grid-cols-3 gap-3 max-w-[280px] mx-auto">
      <span></span>
      <button class="aspect-square rounded-2xl bg-stone-900 p-4 font-black text-white hover:bg-stone-800 active:scale-90 transition disabled:opacity-30 disabled:hover:bg-stone-900" title="Tilt Up" disabled={busy || tripodFault || !canTiltUp} onclick={() => nudge(0, stepDeg)}>
        <svg xmlns="http://www.w3.org/2000/svg" class="h-8 w-8 mx-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 15l7-7 7 7" /></svg>
      </button>
      <span></span>
      <button class="aspect-square rounded-2xl bg-stone-900 p-4 font-black text-white hover:bg-stone-800 active:scale-90 transition disabled:opacity-30 disabled:hover:bg-stone-900" title="Pan Left" disabled={busy || tripodFault} onclick={() => nudge(-stepDeg, 0)}>
        <svg xmlns="http://www.w3.org/2000/svg" class="h-8 w-8 mx-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" /></svg>
      </button>
      <div class="grid gap-2">
        <button
            class={`rounded-xl py-2 text-[8px] font-black uppercase tracking-widest shadow-sm transition active:scale-95 ${
            $hardwareStatus?.tripod.drivers_enabled ? "bg-green-500 text-white" : "bg-stone-200 text-stone-600"
            }`}
            onclick={toggleDrivers}
        >
            {$hardwareStatus?.tripod.drivers_enabled ? "Motors On" : "Motors Off"}
        </button>
        <button class="rounded-xl bg-red-600 p-4 font-black text-white hover:bg-red-500 active:scale-90 transition disabled:opacity-30 disabled:hover:bg-red-600 shadow-md shadow-red-100" title="Emergency Stop" disabled={busy || tripodFault} onclick={stop}>
            <div class="h-4 w-4 mx-auto bg-white rounded-sm"></div>
        </button>
      </div>
      <button class="aspect-square rounded-2xl bg-stone-900 p-4 font-black text-white hover:bg-stone-800 active:scale-90 transition disabled:opacity-30 disabled:hover:bg-stone-900" title="Pan Right" disabled={busy || tripodFault} onclick={() => nudge(stepDeg, 0)}>
        <svg xmlns="http://www.w3.org/2000/svg" class="h-8 w-8 mx-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" /></svg>
      </button>
      <span></span>
      <button class="aspect-square rounded-2xl bg-stone-900 p-4 font-black text-white hover:bg-stone-800 active:scale-90 transition disabled:opacity-30 disabled:hover:bg-stone-900" title="Tilt Down" disabled={busy || tripodFault || !canTiltDown} onclick={() => nudge(0, -stepDeg)}>
        <svg xmlns="http://www.w3.org/2000/svg" class="h-8 w-8 mx-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" /></svg>
      </button>
      <span></span>
    </div>

    <div class="mt-12 flex justify-center">
        <button 
            class="text-[10px] font-black uppercase tracking-[0.2em] text-stone-300 hover:text-amber-600 transition"
            onclick={async () => { await api.homeTripod(); await refreshStatus(); message = "Home set to current position."; }}
        >
            Reset Home (0,0)
        </button>
    </div>

    <p class="mt-12 whitespace-pre-wrap rounded-2xl bg-stone-50 border border-stone-100 p-4 text-xs font-medium text-stone-500 italic leading-relaxed shadow-inner">
      <span class="not-italic text-stone-400 font-black mr-2 uppercase tracking-tighter">Status:</span>
      {message}
    </p>
  </aside>
</section>

<style>
    .no-scrollbar::-webkit-scrollbar {
        display: none;
    }
    .no-scrollbar {
        -ms-overflow-style: none;
        scrollbar-width: none;
    }
    .custom-scrollbar::-webkit-scrollbar {
        width: 6px;
    }
    .custom-scrollbar::-webkit-scrollbar-track {
        background: transparent;
    }
    .custom-scrollbar::-webkit-scrollbar-thumb {
        background: #e7e5e4;
        border-radius: 10px;
    }
    .custom-scrollbar::-webkit-scrollbar-thumb:hover {
        background: #d6d3d1;
    }
</style>
