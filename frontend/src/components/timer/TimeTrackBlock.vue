<template>
  <!--
      Displays a single time track entry.
      Positioning is controlled by top/height/left/width props.
    -->
  <div class="absolute p-1 rounded overflow-hidden flex flex-col justify-center
            transition-all duration-200 ease-in-out select-none" :class="[
              isMoving ? 'cursor-grabbing z-20 shadow-xl ring-2 ring-blue-500/50 opacity-90' : 'cursor-grab z-10',
              !isMoving && !isResizable ? 'hover:brightness-110' : ''
            ]" :style="blockStyle" @mousedown.stop.prevent="$emit('track-mousedown', $event, track)">
    <div v-if="isResizable"
      class="absolute top-0 left-0 right-0 h-1.5 cursor-ns-resize z-40 hover:bg-white/20 transition-colors"
      @mousedown.stop.prevent="$emit('resize-mousedown', $event, track, 'start')"></div>
    <div v-if="showName" class="font-bold text-sm truncate">
      {{ props.track?.name }}
    </div>
    <div v-if="showDetails" class="text-xs text-gray-200 truncate">
      {{ props.track?.project_title }}
    </div>
    <div v-if="showTime" class="text-xs text-gray-300 truncate">
      {{ formattedDetails.duration }} {{ formattedDetails.range }}
    </div>
    <!-- Resize Handle (Bottom) -->
    <div v-if="isResizable"
      class="absolute bottom-0 left-0 right-0 h-1.5 cursor-ns-resize z-40 hover:bg-white/20 transition-colors"
      @mousedown.stop.prevent="$emit('resize-mousedown', $event, track, 'end')"></div>
  </div>
</template>

<script setup>
import { computed } from 'vue';

const FALLBACK_PROJECT_COLOR = '#000000'; // Indigo

const props = defineProps({
  track: { type: Object, required: true },
  top: { type: Number, required: true },
  height: { type: Number, required: true },
  left: { type: String, default: '0%' },
  width: { type: String, default: '100%' },
  isMoving: { type: Boolean, default: false },
});

const blockStyle = computed(() => ({
  top: `${props.top}px`,
  height: `${props.height}px`,
  left: props.left,
  width: props.width,
  backgroundColor: `#${props.track?.project_color}` || FALLBACK_PROJECT_COLOR,
  borderColor: `#${props.track?.project_color}` || FALLBACK_PROJECT_COLOR,
  borderWidth: '1px',
}));

const isResizable = computed(() => props.height >= 24);

const showName = computed(() => props.height >= 18);
const showDetails = computed(() => props.height >= 35);
const showTime = computed(() => props.height >= 50);

const formatTrackDetails = (startStr, endStr) => {
  const formatTime = (date) => date.toLocaleTimeString('en-US', {
    hour: 'numeric', minute: '2-digit', hour12: true
  }).replace(' ', '');

  const start = new Date(startStr);
  const end = endStr ? new Date(endStr) : new Date();

  const diffSeconds = Math.floor((end - start) / 1000);
  const h = Math.floor(diffSeconds / 3600);
  const m = Math.floor((diffSeconds % 3600) / 60);
  const s = diffSeconds % 60;

  return {
    duration: `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`,
    range: `(${formatTime(start)} - ${formatTime(end)})`,
  };
};

const formattedDetails = computed(() => {
  return formatTrackDetails(props.track.start_time, props.track.end_time);
});
</script>
