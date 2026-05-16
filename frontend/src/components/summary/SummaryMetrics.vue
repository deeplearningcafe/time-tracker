<template>
  <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
    <!-- Total Hours -->
    <div class="bg-gray-900 p-4 rounded-lg border border-gray-800">
      <div class="text-sm text-gray-400 mb-1">Total Hours</div>
      <div class="text-3xl font-bold text-white">{{ formatDuration(totalSeconds) }}</div>
    </div>

    <!-- Average Daily -->
    <div class="bg-gray-900 p-4 rounded-lg border border-gray-800">
      <div class="text-sm text-gray-400 mb-1">Average Daily Hours</div>
      <div class="text-3xl font-bold text-white">{{ formatDuration(dailyAverage) }} <span
          class="text-sm font-normal text-gray-500">Hours</span></div>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  totalSeconds: { type: Number, default: 0 },
  dailyAverage: { type: Number, default: 0 }
});

const formatDuration = (seconds) => {
  if (!seconds) return '0:00:00';
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
};
</script>
