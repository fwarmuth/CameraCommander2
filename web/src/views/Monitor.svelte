<script lang="ts">
  import { api } from "../lib/api/client";
  import { activeJob, hardwareStatus, refreshStatus } from "../lib/stores";

  let message = "";

  $: framesCompleted = $activeJob?.progress?.frames_completed ?? 0;
  $: framesTotal = $activeJob?.progress?.frames_total ?? 0;
  $: progress =
    framesTotal > 0 ? Math.round((framesCompleted / framesTotal) * 100) : 0;

  async function stop(): Promise<void> {
    if (!$activeJob) return;
    activeJob.set(await api.stopJob($activeJob.job_id));
  }
</script>

<section class="grid gap-6 lg:grid-cols-[1fr_0.8fr]">
  <div class="rounded-3xl bg-white p-6 shadow-sm">
    <div class="flex items-start justify-between gap-4">
      <div>
        <p class="text-xs font-bold uppercase tracking-[0.35em] text-amber-700">Monitor</p>
        <h2 class="text-2xl font-black">Active job</h2>
      </div>
      <button class="rounded-full border px-4 py-2 font-bold" on:click={refreshStatus}>Refresh</button>
    </div>

    {#if $activeJob}
      <div class="mt-6">
        <p class="font-mono text-sm text-stone-500">{$activeJob.job_id}</p>
        <p class="mt-2 text-4xl font-black">{$activeJob.status}</p>
        <div class="mt-5 h-5 overflow-hidden rounded-full bg-stone-200">
          <div class="h-full bg-amber-500 transition-all" style={`width: ${progress}%`}></div>
        </div>
        <p class="mt-3 font-bold">{framesCompleted} / {framesTotal} frames</p>
        {#if $activeJob.last_position}
          <p class="text-stone-600">Last position: {$activeJob.last_position.pan_deg.toFixed(2)} deg pan, {$activeJob.last_position.tilt_deg.toFixed(2)} deg tilt</p>
        {/if}
        <button class="mt-6 rounded-full bg-red-600 px-5 py-3 font-black text-white" on:click={stop}>Stop</button>
      </div>
    {:else}
      <p class="mt-6 text-stone-600">No active job.</p>
    {/if}
  </div>

  <aside class="rounded-3xl bg-white p-6 shadow-sm">
    <h3 class="text-xl font-black">Hardware</h3>
    <dl class="mt-4 grid gap-3 text-sm">
      <div class="rounded-2xl bg-stone-100 p-3">
        <dt class="font-bold">Camera</dt>
        <dd>{$hardwareStatus?.camera.state ?? "unknown"} {$hardwareStatus?.camera.model ?? ""}</dd>
      </div>
      <div class="rounded-2xl bg-stone-100 p-3">
        <dt class="font-bold">Tripod</dt>
        <dd>{$hardwareStatus?.tripod.state ?? "unknown"} {$hardwareStatus?.tripod.firmware_version ?? ""}</dd>
      </div>
      <div class="rounded-2xl bg-stone-100 p-3">
        <dt class="font-bold">Position</dt>
        <dd>{$hardwareStatus?.tripod.position_pan_deg ?? 0} pan / {$hardwareStatus?.tripod.position_tilt_deg ?? 0} tilt</dd>
      </div>
    </dl>
    <p class="mt-4 text-sm text-stone-500">{message}</p>
  </aside>
</section>
