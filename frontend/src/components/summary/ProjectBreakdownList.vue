<template>
  <div class="flex flex-col w-full">
    <!-- Header -->
    <div
      class="flex items-center text-xs text-gray-500 px-4 py-2 border-b border-gray-800 uppercase tracking-wider font-semibold">
      <div class="flex-1">Project | Description</div>
      <div class="w-24 text-right">Duration</div>
      <div class="w-20 text-right">%</div>
    </div>

    <!-- List Items -->
    <div v-for="project in breakdownData" :key="project.project" class="border-b border-gray-800 last:border-0">
      <!-- Project Row (Click to toggle) -->
      <div class="flex items-center px-4 py-3 hover:bg-gray-800/50 cursor-pointer transition-colors group"
        @click="toggleProject(project.project)">
        <div class="flex-1 flex items-center min-w-0">
          <!-- Arrow Icon -->
          <span class="transform transition-transform duration-200 mr-3 text-gray-500 group-hover:text-gray-300"
            :class="{ 'rotate-90': expandedProjects.has(project.project) }">
            <svg class="w-3 h-3 fill-current" viewBox="0 0 20 20">
              <path d="M6 6L14 10L6 14V6Z" />
            </svg>
          </span>

          <!-- Color Dot -->
          <span class="w-2.5 h-2.5 rounded-full mr-3 flex-shrink-0"
            :style="{ backgroundColor: `#${project.color}` }"></span>

          <!-- Project Name -->
          <span class="text-gray-200 font-medium truncate">{{ project.project }}</span>
          <span class="ml-2 text-gray-500 text-xs">({{ project.entries.length }})</span>
        </div>

        <!-- Duration -->
        <div class="w-24 text-right font-mono text-gray-300 text-sm">
          {{ formatDuration(project.total_seconds) }}
        </div>

        <!-- Percentage -->
        <div class="w-20 text-right text-gray-500 text-sm">
          {{ calculatePercentage(project.total_seconds) }}%
        </div>
      </div>

      <!-- Entries List (Expanded) -->
      <div v-if="expandedProjects.has(project.project)" class="bg-gray-900/50 border-t border-gray-800/50">
        <div v-for="(entry, index) in project.entries" :key="index"
          class="flex items-center px-4 py-2 pl-12 hover:bg-gray-800/30 transition-colors">
          <div class="flex-1 text-gray-400 text-sm truncate">{{ entry.name }}</div>
          <div class="w-24 text-right font-mono text-gray-500 text-xs">
            {{ formatDuration(entry.duration) }}
          </div>
          <div class="w-20 text-right text-gray-500 text-xs">
            {{ calculatePercentage(entry.duration) }}%
          </div>
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <div v-if="breakdownData.length === 0" class="p-12 text-center">
      <div class="text-gray-500">No activity found for this period.</div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';

const props = defineProps({
  breakdownData: { type: Array, required: true }
});

const expandedProjects = ref(new Set());

const totalDurationAll = computed(() => {
  return props.breakdownData.reduce((acc, p) => acc + p.total_seconds, 0);
});

const toggleProject = (projectName) => {
  const newSet = new Set(expandedProjects.value);
  if (newSet.has(projectName)) {
    newSet.delete(projectName);
  } else {
    newSet.add(projectName);
  }
  expandedProjects.value = newSet;
};

const formatDuration = (seconds) => {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
};

const calculatePercentage = (seconds) => {
  if (!totalDurationAll.value) return '0.0';
  return ((seconds / totalDurationAll.value) * 100).toFixed(1);
};
</script>
