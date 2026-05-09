<script lang="ts">
  import { api, ApiError } from "../lib/api/client";
  import type { Configuration } from "../lib/api/types";
  import { activeJob, calibration, plannerConfiguration, refreshStatus } from "../lib/stores";

  type PlannerMode = "timelapse" | "video_pan";

  let mode: PlannerMode = "timelapse";
  let name = "Mock timelapse";
  let iso = 400;
  let shutter = "1/125";
  let aperture = 5.6;
  let outputDir = "./output/web-run";
  let totalFrames = 24;
  let intervalS = 5;
  let settleS = 0.5;
  let durationS = 30;
  let startPan = 0;
  let startTilt = 0;
  let targetPan = 30;
  let targetTilt = 10;
  let tiltMin = -45;
  let tiltMax = 45;
  let assembleVideo = true;
  let videoFps = 25;
  let status = "";
  let busy = false;

  $: tiltValid =
    startTilt >= tiltMin && startTilt <= tiltMax && targetTilt >= tiltMin && targetTilt <= tiltMax;

  $: if ($plannerConfiguration) {
    applyConfiguration($plannerConfiguration);
    plannerConfiguration.set(null);
  }

  function applyConfiguration(value: Configuration): void {
    name = value.metadata.name;
    outputDir = value.output.output_dir;
    tiltMin = value.safety.tilt_min_deg;
    tiltMax = value.safety.tilt_max_deg;
    startPan = value.sequence.start.pan_deg;
    startTilt = value.sequence.start.tilt_deg;
    targetPan = value.sequence.target.pan_deg;
    targetTilt = value.sequence.target.tilt_deg;
    if (value.camera.settings) {
      const settings = value.camera.settings;
      if (typeof settings["main.imgsettings.iso"] === "number") iso = settings["main.imgsettings.iso"];
      if (typeof settings["main.capturesettings.shutterspeed"] === "string") {
        shutter = settings["main.capturesettings.shutterspeed"];
      }
      if (typeof settings["main.capturesettings.aperture"] === "number") {
        aperture = settings["main.capturesettings.aperture"];
      }
    }
    if (value.sequence.kind === "timelapse") {
      mode = "timelapse";
      totalFrames = value.sequence.total_frames;
      intervalS = value.sequence.interval_s;
      settleS = value.sequence.settle_time_s;
      assembleVideo = value.output.video?.assemble ?? true;
      videoFps = value.output.video?.fps ?? 25;
    } else {
      mode = "video_pan";
      durationS = value.sequence.duration_s;
    }
    status = "Loaded configuration from session library.";
  }

  function config(): Configuration {
    return {
      metadata: { name },
      camera: {
        image_format: "camera-default",
        settings: {
          "main.imgsettings.iso": iso,
          "main.capturesettings.shutterspeed": shutter,
          "main.capturesettings.aperture": aperture,
        },
      },
      tripod: {
        serial: {
          port: "socket://127.0.0.1:9999",
          baudrate: 9600,
          timeout: 1,
          write_timeout: 1,
          reconnect_interval: 2,
          max_retries: 5,
        },
        microstep: 16,
        expected_protocol_major: 1,
      },
      safety: {
        tilt_min_deg: tiltMin,
        tilt_max_deg: tiltMax,
        move_timeout_margin_s: 2,
        disk_min_free_bytes: 0,
        disk_avg_frame_bytes: 1,
      },
      output: {
        output_dir: outputDir,
        frame_filename_template: "frame_{index:04d}{ext}",
        metadata_strategy: "auto",
        video: { assemble: assembleVideo, fps: videoFps, format: "mp4-h264" },
      },
      sequence:
        mode === "timelapse"
          ? {
              kind: "timelapse",
              total_frames: totalFrames,
              interval_s: intervalS,
              settle_time_s: settleS,
              start: { pan_deg: startPan, tilt_deg: startTilt },
              target: { pan_deg: targetPan, tilt_deg: targetTilt },
            }
          : {
              kind: "video_pan",
              duration_s: durationS,
              start: { pan_deg: startPan, tilt_deg: startTilt },
              target: { pan_deg: targetPan, tilt_deg: targetTilt },
            },
    };
  }

  async function setHome(): Promise<void> {
    busy = true;
    try {
      await api.homeTripod();
      await refreshStatus();
      status = "Calibration set to homed.";
    } catch (error) {
      status = error instanceof Error ? error.message : "Failed to home tripod";
    } finally {
      busy = false;
    }
  }

  async function launch(): Promise<void> {
    busy = true;
    try {
      const job =
        mode === "timelapse" ? await api.startTimelapse(config()) : await api.startVideoPan(config());
      activeJob.set(job);
      status = `Launched ${job.job_id}`;
    } catch (error) {
      status = error instanceof ApiError ? `${error.payload.error}: ${error.message}` : "Launch failed";
    } finally {
      busy = false;
    }
  }
</script>

<section class="grid gap-6 lg:grid-cols-[1.25fr_0.75fr]">
  <form class="grid gap-5 rounded-3xl bg-white p-5 shadow-sm" on:submit|preventDefault={launch}>
    <div>
      <p class="text-xs font-bold uppercase tracking-[0.35em] text-amber-700">Planner</p>
      <h2 class="text-2xl font-black">{mode === "timelapse" ? "Timelapse job" : "Video pan job"}</h2>
    </div>

    <div class="flex flex-wrap gap-2 rounded-2xl bg-stone-100 p-2">
      <button
        class={`rounded-full px-4 py-2 font-black ${mode === "timelapse" ? "bg-stone-900 text-white" : "bg-white text-stone-700"}`}
        type="button"
        on:click={() => (mode = "timelapse")}
      >
        Timelapse
      </button>
      <button
        class={`rounded-full px-4 py-2 font-black ${mode === "video_pan" ? "bg-stone-900 text-white" : "bg-white text-stone-700"}`}
        type="button"
        on:click={() => (mode = "video_pan")}
      >
        Video Pan
      </button>
    </div>

    <label class="grid gap-1">
      <span class="font-bold">Plan name</span>
      <input class="rounded-xl border p-3" bind:value={name} />
    </label>

    <div class="grid gap-4 md:grid-cols-3">
      <label class="grid gap-1"><span class="font-bold">ISO</span><input class="rounded-xl border p-3" type="number" bind:value={iso} /></label>
      <label class="grid gap-1"><span class="font-bold">Shutter</span><input class="rounded-xl border p-3" bind:value={shutter} /></label>
      <label class="grid gap-1"><span class="font-bold">Aperture</span><input class="rounded-xl border p-3" type="number" step="0.1" bind:value={aperture} /></label>
    </div>

    {#if mode === "timelapse"}
      <div class="grid gap-4 md:grid-cols-3">
        <label class="grid gap-1"><span class="font-bold">Frames</span><input class="rounded-xl border p-3" type="number" min="2" bind:value={totalFrames} /></label>
        <label class="grid gap-1"><span class="font-bold">Interval s</span><input class="rounded-xl border p-3" type="number" step="0.1" bind:value={intervalS} /></label>
        <label class="grid gap-1"><span class="font-bold">Settle s</span><input class="rounded-xl border p-3" type="number" step="0.1" bind:value={settleS} /></label>
      </div>
    {:else}
      <label class="grid gap-1 md:max-w-xs">
        <span class="font-bold">Duration s</span>
        <input class="rounded-xl border p-3" type="number" min="0.1" step="0.1" bind:value={durationS} />
      </label>
    {/if}

    <div class="grid gap-4 md:grid-cols-4">
      <label class="grid gap-1"><span class="font-bold">Start pan</span><input class="rounded-xl border p-3" type="number" bind:value={startPan} /></label>
      <label class="grid gap-1"><span class="font-bold">Start tilt</span><input class="rounded-xl border p-3" type="number" bind:value={startTilt} /></label>
      <label class="grid gap-1"><span class="font-bold">Target pan</span><input class="rounded-xl border p-3" type="number" bind:value={targetPan} /></label>
      <label class="grid gap-1"><span class="font-bold">Target tilt</span><input class="rounded-xl border p-3" type="number" bind:value={targetTilt} /></label>
    </div>

    <div class="grid gap-4 md:grid-cols-3">
      <label class="grid gap-1"><span class="font-bold">Tilt min</span><input class="rounded-xl border p-3" type="number" bind:value={tiltMin} /></label>
      <label class="grid gap-1"><span class="font-bold">Tilt max</span><input class="rounded-xl border p-3" type="number" bind:value={tiltMax} /></label>
      <label class="grid gap-1"><span class="font-bold">Output dir</span><input class="rounded-xl border p-3" bind:value={outputDir} /></label>
    </div>

    {#if mode === "timelapse"}
      <div class="flex flex-wrap items-center gap-4">
        <label class="flex items-center gap-2 font-bold"><input type="checkbox" bind:checked={assembleVideo} /> Assemble video</label>
        <label class="flex items-center gap-2 font-bold">FPS <input class="w-24 rounded-xl border p-2" type="number" min="1" bind:value={videoFps} /></label>
      </div>
    {/if}

    <div class="flex flex-wrap gap-3">
      <button class="rounded-full bg-stone-900 px-5 py-3 font-black text-white disabled:opacity-50" type="button" disabled={busy} on:click={setHome}>Set as home</button>
      <button class="rounded-full bg-amber-500 px-5 py-3 font-black text-stone-950 disabled:opacity-50" disabled={busy || !tiltValid || $calibration !== "homed"}>
        Launch {mode === "timelapse" ? "timelapse" : "video pan"}
      </button>
    </div>
  </form>

  <aside class="rounded-3xl bg-[#17211f] p-5 text-[#f8f1e5]">
    <h3 class="text-xl font-black">Preflight</h3>
    <p class="mt-4">Calibration: <strong>{$calibration}</strong></p>
    <p>Tilt window: <strong class={tiltValid ? "text-green-300" : "text-red-300"}>{tiltValid ? "valid" : "out of range"}</strong></p>
    <p class="mt-4 whitespace-pre-wrap text-sm text-stone-300">{status || "Ready."}</p>
  </aside>
</section>
