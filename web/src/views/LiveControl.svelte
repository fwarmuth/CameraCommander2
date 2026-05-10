<script lang="ts">
  import { onMount } from "svelte";

  import { api, ApiError } from "../lib/api/client";
  import type { CameraSettings } from "../lib/api/types";
  import { hardwareStatus, refreshStatus } from "../lib/stores";

  let settings: CameraSettings = {};
  let pending: Record<string, string | number | boolean> = {};
  let stepDeg = 1;
  let autofocus = false;
  let captureUrl = "";
  let message = "Load camera settings to begin.";
  let busy = false;
  let activeTab = "Planning";

  const planningKeys = [
    "main.imgsettings.iso",
    "main.capturesettings.shutterspeed",
    "main.capturesettings.aperture",
    "main.imgsettings.whitebalance",
    "main.capturesettings.exposurecompensation",
    "main.capturesettings.focusmode",
  ];

  $: cameraFault =
    $hardwareStatus?.camera.state === "error" || $hardwareStatus?.camera.state === "disconnected";
  $: tripodFault =
    $hardwareStatus?.tripod.state === "error" || $hardwareStatus?.tripod.state === "disconnected";
  $: tiltMin = $hardwareStatus?.tripod.tilt_min_deg ?? -90;
  $: tiltMax = $hardwareStatus?.tripod.tilt_max_deg ?? 90;
  $: currentTilt = $hardwareStatus?.tripod.position_tilt_deg ?? 0;
  $: canTiltDown = currentTilt - stepDeg >= tiltMin;
  $: canTiltUp = currentTilt + stepDeg <= tiltMax;

  $: groups = Object.keys(settings).reduce(
    (acc, key) => {
      const parts = key.split(".");
      const tabName = parts.length > 1 ? parts[1] : "other";
      if (!acc[tabName]) acc[tabName] = {};
      
      const subGroup = parts.length > 2 ? parts.slice(2, -1).join(".") || "general" : "general";
      if (!acc[tabName][subGroup]) acc[tabName][subGroup] = [];
      acc[tabName][subGroup].push(key);
      
      return acc;
    },
    {} as Record<string, Record<string, string[]>>,
  );

  $: tabs = ["Planning", ...Object.keys(groups).sort()];

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

  function getSubGroups(tab: string): Record<string, string[]> {
    if (tab === "Planning") {
      return { "": planningKeys.filter((k) => settings[k]) };
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

  onMount(() => {
    void loadSettings();
  });
</script>

<section class="grid gap-6 xl:grid-cols-[1fr_0.9fr]">
  <div class="grid gap-6">
    <div class="rounded-3xl bg-white p-6 shadow-sm">
      <div class="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p class="text-xs font-bold uppercase tracking-[0.35em] text-amber-700">Live Control</p>
          <h2 class="mt-2 text-2xl font-black">Camera settings</h2>
        </div>
        <button class="rounded-full border px-4 py-2 font-bold" disabled={busy} on:click={loadSettings}>Reload</button>
      </div>

      {#if cameraFault}
        <p class="mt-4 rounded-2xl bg-red-100 p-3 font-bold text-red-800">Camera is {$hardwareStatus?.camera.state ?? "unknown"}; capture controls are disabled.</p>
      {/if}

      <nav class="mt-6 flex gap-1 overflow-x-auto rounded-2xl bg-stone-100 p-1">
        {#each tabs as tab}
          <button
            class={`whitespace-nowrap rounded-xl px-3 py-1.5 text-xs font-bold transition ${
              activeTab === tab ? "bg-white text-stone-900 shadow-sm" : "text-stone-500 hover:text-stone-700"
            }`}
            on:click={() => (activeTab = tab)}
          >
            {tab === "Planning" ? "Planning" : tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        {/each}
      </nav>

      <div class="mt-4 grid max-h-[32rem] gap-6 overflow-auto pr-2">
        {#each Object.entries(getSubGroups(activeTab)) as [subGroup, keys]}
          <div class="grid gap-3">
            {#if subGroup}
              <h4 class="text-[10px] font-black uppercase tracking-widest text-stone-400">{subGroup.replace(".", " / ")}</h4>
            {/if}
            <div class="grid gap-3">
              {#each keys as key}
                {@const descriptor = settings[key]}
                <label class="grid gap-2 rounded-2xl border border-stone-200 p-3 md:grid-cols-[1fr_14rem] md:items-center">
                  <span>
                    <strong class="block text-sm">{key.split(".").pop()}</strong>
                    <span class="text-[10px] uppercase tracking-wider text-stone-400">{key}</span>
                  </span>
                  {#if descriptor.choices?.length}
                    <select class="rounded-xl border border-stone-300 bg-white p-2 text-sm" bind:value={pending[key]}>
                      {#each descriptor.choices as choice}
                        <option value={choice}>{choice}</option>
                      {/each}
                    </select>
                  {:else if descriptor.type === 'RANGE'}
                    <div class="flex items-center gap-2">
                       <input type="range" class="grow" min={descriptor.range?.min} max={descriptor.range?.max} step={descriptor.range?.step} bind:value={pending[key]} />
                       <span class="text-xs w-8 text-right">{pending[key]}</span>
                    </div>
                  {:else}
                    <input class="rounded-xl border border-stone-300 bg-white p-2 text-sm" bind:value={pending[key]} />
                  {/if}
                </label>
              {/each}
            </div>
          </div>
        {/each}
      </div>

      <div class="mt-5 flex flex-wrap gap-3">
        <button class="rounded-full bg-stone-900 px-5 py-3 font-black text-white disabled:opacity-50" disabled={busy || cameraFault} on:click={applySettings}>Apply settings</button>
        <label class="flex items-center gap-2 font-bold"><input type="checkbox" bind:checked={autofocus} /> Autofocus</label>
        <button class="rounded-full bg-amber-500 px-5 py-3 font-black text-stone-950 disabled:opacity-50" disabled={busy || cameraFault} on:click={capture}>Test capture</button>
      </div>
    </div>

    <div class="rounded-3xl bg-[#17211f] p-6 text-[#f8f1e5] shadow-sm">
      <h3 class="text-xl font-black">Live view</h3>
      <img class="mt-4 aspect-video w-full rounded-2xl bg-black object-contain" src="/api/camera/preview/stream" alt="Camera live preview" />
      {#if captureUrl}
        <a class="mt-4 inline-block rounded-full bg-white px-4 py-2 font-bold text-stone-950" href={captureUrl} target="_blank" rel="noreferrer">Open latest capture</a>
      {/if}
    </div>
  </div>

  <aside class="rounded-3xl bg-white p-6 shadow-sm">
    <h3 class="text-xl font-black">Tripod nudge</h3>
    {#if tripodFault}
      <p class="mt-4 rounded-2xl bg-red-100 p-3 font-bold text-red-800">Tripod is {$hardwareStatus?.tripod.state ?? "unknown"}; nudge controls are disabled.</p>
    {/if}

    <dl class="mt-5 grid gap-3 text-sm">
      <div class="rounded-2xl bg-stone-100 p-3">
        <dt class="font-bold">Position</dt>
        <dd>{($hardwareStatus?.tripod.position_pan_deg ?? 0).toFixed(2)} pan / {currentTilt.toFixed(2)} tilt</dd>
      </div>
      <div class="rounded-2xl bg-stone-100 p-3">
        <dt class="font-bold">Tilt window</dt>
        <dd>{tiltMin} to {tiltMax} deg</dd>
      </div>
    </dl>

    <div class="mt-5 flex items-center justify-between gap-4">
      <label class="grid grow gap-1 font-bold">
        Step degrees
        <input class="rounded-xl border p-3" type="number" min="0.1" step="0.1" bind:value={stepDeg} />
      </label>
      <button
        class={`mt-5 rounded-2xl px-6 py-4 text-xs font-black uppercase tracking-widest shadow-sm transition ${
          $hardwareStatus?.tripod.drivers_enabled ? "bg-green-500 text-white" : "bg-stone-200 text-stone-600"
        }`}
        on:click={toggleDrivers}
      >
        Motors: {$hardwareStatus?.tripod.drivers_enabled ? "ON" : "OFF"}
      </button>
    </div>

    <div class="mt-5 grid grid-cols-3 gap-3">
      <span></span>
      <button class="rounded-2xl bg-stone-900 p-4 font-black text-white disabled:opacity-40" disabled={busy || tripodFault || !canTiltUp} on:click={() => nudge(0, stepDeg)}>Tilt +</button>
      <span></span>
      <button class="rounded-2xl bg-stone-900 p-4 font-black text-white disabled:opacity-40" disabled={busy || tripodFault} on:click={() => nudge(-stepDeg, 0)}>Pan -</button>
      <button class="rounded-2xl bg-red-600 p-4 font-black text-white disabled:opacity-40" disabled={busy || tripodFault} on:click={stop}>Stop</button>
      <button class="rounded-2xl bg-stone-900 p-4 font-black text-white disabled:opacity-40" disabled={busy || tripodFault} on:click={() => nudge(stepDeg, 0)}>Pan +</button>
      <span></span>
      <button class="rounded-2xl bg-stone-900 p-4 font-black text-white disabled:opacity-40" disabled={busy || tripodFault || !canTiltDown} on:click={() => nudge(0, -stepDeg)}>Tilt -</button>
      <span></span>
    </div>

    <p class="mt-6 whitespace-pre-wrap rounded-2xl bg-stone-100 p-4 text-sm text-stone-700">{message}</p>
  </aside>
</section>
