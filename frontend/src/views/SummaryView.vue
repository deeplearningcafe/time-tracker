<template>
  <div class="flex flex-col h-full w-full bg-black text-gray-200 overflow-y-auto">
    <!-- Header / Navigation -->
    <DateRangeNavigator :date-range="dateRange" @range-change="handleRangeChange" @filter-change="handleFilterChange"
      @set-range="handleSetRange" />

    <!-- Loading State -->
    <div v-if="isLoading" class="flex-grow flex items-center justify-center">
      <div class="flex flex-col items-center space-y-2">
        <div class="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
        <div class="text-gray-400 text-sm">Loading summary...</div>
      </div>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="flex-grow flex items-center justify-center">
      <div class="text-red-500 bg-red-900/20 p-4 rounded border border-red-800">
        {{ error }}
      </div>
    </div>

    <!-- Dashboard Content -->
    <div v-else class="p-6 space-y-6 max-w-7xl mx-auto w-full">
      <!-- Metrics Cards -->
      <SummaryMetrics :total-seconds="processedData.metrics.totalSeconds"
        :daily-average="processedData.metrics.dailyAverage" />

      <!-- Charts Row -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <!-- Bar Chart: Duration by Day -->
        <div class="lg:col-span-2 bg-gray-900 rounded-lg p-4 border border-gray-800 shadow-sm">
          <h3 class="text-sm font-semibold mb-4 text-gray-400 uppercase tracking-wider">Duration by day</h3>
          <div class="h-64 relative">
            <DurationBarChart :data="processedData.barChart" />
          </div>
        </div>

        <!-- Pie Chart: Project Distribution -->
        <div class="bg-gray-900 rounded-lg p-4 border border-gray-800 shadow-sm">
          <h3 class="text-sm font-semibold mb-4 text-gray-400 uppercase tracking-wider">Project distribution</h3>
          <div class="h-64 flex items-center justify-center relative">
            <ProjectPieChart :data="processedData.pieChart" />
          </div>
        </div>
      </div>

      <!-- Breakdown List -->
      <div class="bg-gray-900 rounded-lg border border-gray-800 shadow-sm">
        <div class="p-4 border-b border-gray-800">
          <h3 class="text-sm font-semibold text-gray-400 uppercase tracking-wider">Project and description breakdown
          </h3>
        </div>
        <ProjectBreakdownList :breakdown-data="processedData.breakdown" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, watch, ref } from 'vue';
import { useStore } from 'vuex';
import DateRangeNavigator from '../components/summary/DateRangeNavigator.vue';
import SummaryMetrics from '../components/summary/SummaryMetrics.vue';
import DurationBarChart from '../components/summary/DurationBarChart.vue';
import ProjectPieChart from '../components/summary/ProjectPieChart.vue';
import ProjectBreakdownList from '../components/summary/ProjectBreakdownList.vue';

const store = useStore();

const filterText = ref('');
const filterProject = ref(null);

// --- Store Access ---
const isLoading = computed(() => store.state.time.status.summary === 'loading');
const error = computed(() => store.state.time.status.summary === 'error' ? 'Failed to load summary data.' : null);
const rawSummaryData = computed(() => store.state.time.summaryData || []);

const dateRange = ref(store.getters['ui/getShortcutRange']('thisWeek'));

// --- Data Processing ---
const processedData = computed(() => {
  const { startDate, endDate, type } = dateRange.value;
  let data = rawSummaryData.value;
  console.log("inside processedData", data)

  if (filterText.value) {
    const lower = filterText.value.toLowerCase();
    data = data.filter(item =>
      (item.time_entry && item.time_entry.toLowerCase().includes(lower)) ||
      (item.project && item.project.toLowerCase().includes(lower))
    );
  }
  if (filterProject.value) {
    const lowerProj = filterProject.value.toLowerCase();
    data = data.filter(item => item.project && item.project.toLowerCase().includes(lowerProj));
  }

  let binSize = 'day';
  const diffTime = endDate.getTime() - startDate.getTime();
  const diffDays = Math.round(diffTime / (1000 * 3600 * 24)) + 1;

  if (type === 'year') {
    binSize = 'month';
  } else if (type === 'quarter') {
    binSize = 'week';
  } else if (type === 'month' || type === 'week') {
    binSize = 'day';
  } else {
    if (diffDays <= 31) binSize = 'day';
    else if (diffDays <= 365) binSize = 'week';
    else binSize = 'month';
  }

  /**
   * Determines the grouping key for a given date based on bin size.
   * @param {Date} d - The date to be grouped.
   * @returns {string} The formatted key (e.g., YYYY-MM, YYYY-MM-DD).
   */
  const getBinKey = (d) => {
    if (binSize === 'month') {
      const y = d.getFullYear();
      const m = String(d.getMonth() + 1).padStart(2, '0');
      return `${y}-${m}`;

    } else if (binSize === 'week') {
      const day = d.getDay();
      const diff = d.getDate() - day;

      const startOfWeek = new Date(d);
      startOfWeek.setDate(diff);

      const y = startOfWeek.getFullYear();
      const m = String(startOfWeek.getMonth() + 1).padStart(2, '0');
      const date = String(startOfWeek.getDate()).padStart(2, '0');
      return `${y}-${m}-${date}`;

    } else {
      const y = d.getFullYear();
      const m = String(d.getMonth() + 1).padStart(2, '0');
      const date = String(d.getDate()).padStart(2, '0');
      return `${y}-${m}-${date}`;
    }
  };

  const barMap = new Map();
  // Pre-fill all days in range with 0 to ensure continuous x-axis
  const d = new Date(startDate);
  while (d <= endDate) {
    // Use local time components to construct YYYY-MM-DD string.
    const key = getBinKey(d);
    if (!barMap.has(key)) {
      barMap.set(key, 0);
    }
    d.setDate(d.getDate() + 1);
  }
  console.log("summary view barmap", barMap);

  const pieMap = new Map();
  const breakdownMap = new Map();
  let totalSeconds = 0;

  data.forEach(item => {
    const duration = item.duration_seconds || 0;
    totalSeconds += duration;

    // Bar Chart (By Date)
    const [y, m, day] = item.date.split('-');
    const itemDate = new Date(y, m - 1, day);
    const key = getBinKey(itemDate);
    if (barMap.has(key)) {
      barMap.set(key, barMap.get(key) + duration);
    }

    // Pie Chart (By Project)
    const projectName = item.project || 'No Project';
    const projectColor = item.project_color || '6B7280';

    if (!pieMap.has(projectName)) {
      pieMap.set(projectName, {
        name: projectName,
        color: projectColor,
        total_seconds: 0
      });
    }
    pieMap.get(projectName).total_seconds += duration;

    // Breakdown (Project -> Entries)
    if (!breakdownMap.has(projectName)) {
      breakdownMap.set(projectName, {
        project: projectName,
        color: projectColor,
        total_seconds: 0,
        entries: []
      });
    }
    const projGroup = breakdownMap.get(projectName);
    projGroup.total_seconds += duration;

    // Group entries within project
    const entryName = item.time_entry || '(No Description)';
    const existingEntry = projGroup.entries.find(e => e.name === entryName);
    if (existingEntry) {
      existingEntry.duration += duration;
    } else {
      projGroup.entries.push({
        name: entryName,
        duration: duration
      });
    }
    projGroup.entries.sort((a, b) => b.duration - a.duration);
  });

  const barChart = Array.from(barMap.entries()).map(([date, duration]) => ({
    date,
    duration_seconds: duration
  }));

  const pieChart = Array.from(pieMap.values())
    .sort((a, b) => b.total_seconds - a.total_seconds);

  const breakdown = Array.from(breakdownMap.values())
    .sort((a, b) => b.total_seconds - a.total_seconds);

  const today = new Date();
  today.setHours(23, 59, 59, 999);
  const effectiveEndDate = endDate > today ? today : endDate;

  // Calculate days difference for average (capping at today)
  const diffTimeAvg = Math.max(0, effectiveEndDate - startDate);
  const msPerDay = 1000 * 60 * 60 * 24;
  const diffDaysAvg = Math.ceil(diffTimeAvg / msPerDay);
  const dailyAverage = diffDays > 0 ? totalSeconds / diffDays : 0;

  return {
    barChart,
    pieChart,
    breakdown,
    metrics: { totalSeconds, dailyAverage }
  };
});

// --- Actions ---
const fetchSummary = () => {
  console.log("inside fetchSummary", dateRange.value);
  store.dispatch('time/fetchSummary', {
    startDate: dateRange.value.startDate.toISOString(),
    endDate: dateRange.value.endDate.toISOString()
  });
};

const handleRangeChange = (direction) => {
  dateRange.value = store.getters['ui/getAdjacentRange'](dateRange.value, direction);
  store.dispatch('ui/setDate', { newDate: dateRange.value.startDate });
};

const handleSetRange = (payload) => {
  dateRange.value = payload;
  console.log("inside handleSetRange", dateRange.value);
  store.dispatch('ui/setDate', { newDate: payload.startDate });
};

const handleFilterChange = ({ text, project }) => {
  filterText.value = text;
  filterProject.value = project;
};

// --- Lifecycle ---
let previousViewType = 'day';

onMounted(() => {
  previousViewType = store.getters['ui/getViewType'];
  // Ensure we are in Week view for summary by default, or respect user choice
  if (store.state.ui.viewType === 'day') {
    store.dispatch('ui/setViewType', { type: 'week' });
  }
  fetchSummary();
});

onUnmounted(() => {
  // Restore the viewType to what it was before visiting Summary
  if (previousViewType === 'day') {
    store.dispatch('ui/setViewType', { type: 'day' });
  }
});

watch(dateRange, fetchSummary, { deep: true });
</script>
