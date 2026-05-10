<script lang="ts">
  import type { CameraSettings } from "../lib/api/types";

  interface Props {
    settings: CameraSettings;
    pending: Record<string, string | number | boolean>;
    apply: (key: string, value: string | number | boolean) => void;
    busy?: boolean;
  }

  let { settings, pending, apply, busy = false }: Props = $props();

  const keys = [
    "main.imgsettings.iso",
    "main.capturesettings.shutterspeed",
    "main.capturesettings.aperture",
    "main.imgsettings.whitebalance",
  ];

  function getLabel(key: string): string {
    const parts = key.split(".");
    return parts[parts.length - 1].toUpperCase();
  }
</script>

<div class="grid grid-cols-2 sm:grid-cols-4 gap-4 bg-stone-950 p-4 rounded-2xl shadow-inner border border-white/5">
  {#each keys as key}
    {#if settings[key]}
      {@const descriptor = settings[key]}
      <div class="flex flex-col gap-1">
        <span class="text-[9px] font-black text-stone-500 tracking-widest">{getLabel(key)}</span>
        <select
          class="bg-transparent text-sm font-bold text-amber-400 border-none p-0 focus:ring-0 cursor-pointer hover:text-amber-300 transition-colors disabled:opacity-50"
          value={pending[key]}
          disabled={busy}
          onchange={(e) => apply(key, (e.target as HTMLSelectElement).value)}
        >
          {#each descriptor.choices || [] as choice}
            <option value={choice} class="bg-stone-900 text-white">{choice}</option>
          {/each}
        </select>
      </div>
    {/if}
  {/each}
</div>
