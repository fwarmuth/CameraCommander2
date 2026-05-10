<script lang="ts">
  interface Props {
    src: string;
    onClose: () => void;
  }

  let { src, onClose }: Props = $props();

  let zoom = $state(1);
  let x = $state(0);
  let y = $state(0);
  let dragging = $state(false);

  function handleWheel(e: WheelEvent) {
    e.preventDefault();
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    zoom = Math.min(Math.max(0.5, zoom * delta), 10);
  }

  function handleMouseDown() {
    dragging = true;
  }

  function handleMouseMove(e: MouseEvent) {
    if (!dragging) return;
    x += e.movementX;
    y += e.movementY;
  }

  function handleMouseUp() {
    dragging = false;
  }

  function reset() {
    zoom = 1;
    x = 0;
    y = 0;
  }

  function zoom100() {
    zoom = 4; // Assuming 4x is roughly 100% depending on container
    x = 0;
    y = 0;
  }
</script>

<div 
  class="fixed inset-0 z-50 flex flex-col bg-black/95 backdrop-blur-md"
  onwheel={handleWheel}
>
  <header class="flex items-center justify-between p-4 text-white border-b border-white/10">
    <div class="flex items-center gap-4">
      <h3 class="font-black uppercase tracking-widest text-sm">Image Inspector</h3>
      <span class="text-xs text-stone-500 font-mono">{Math.round(zoom * 100)}%</span>
    </div>
    <div class="flex gap-2">
      <button class="px-4 py-2 text-xs font-bold bg-white/10 rounded-full hover:bg-white/20 transition" onclick={reset}>Fit</button>
      <button class="px-4 py-2 text-xs font-bold bg-white/10 rounded-full hover:bg-white/20 transition" onclick={zoom100}>100%</button>
      <button class="px-4 py-2 text-xs font-bold bg-amber-500 text-black rounded-full hover:bg-amber-400 transition" onclick={onClose}>Close</button>
    </div>
  </header>

  <div 
    class="relative flex-grow overflow-hidden cursor-move select-none"
    onmousedown={handleMouseDown}
    onmousemove={handleMouseMove}
    onmouseup={handleMouseUp}
    onmouseleave={handleMouseUp}
  >
    <div 
      class="absolute inset-0 flex items-center justify-center transition-transform duration-75 ease-out"
      style:transform="translate(${x}px, ${y}px) scale(${zoom})"
    >
      <img {src} alt="Captured asset" class="max-w-full max-h-full shadow-2xl" draggable="false" />
    </div>
  </div>
  
  <footer class="p-4 text-[10px] text-stone-500 text-center uppercase tracking-[0.2em]">
    Use Mouse Wheel to Zoom • Drag to Pan
  </footer>
</div>
