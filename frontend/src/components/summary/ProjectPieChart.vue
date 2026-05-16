<template>
  <div class="relative w-full h-full">
    <Doughnut v-if="hasData" :data="chartData" :options="chartOptions" />
    <div v-else class="flex items-center justify-center h-full text-gray-500 text-sm">
      No data
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from 'chart.js';
import { Doughnut } from 'vue-chartjs';

ChartJS.register(ArcElement, Tooltip, Legend);

const props = defineProps({
  data: { type: Array, required: true } // Array of { name, color, total_seconds }
});

const hasData = computed(() => props.data.length > 0 && props.data.some(d => d.total_seconds > 0));

const chartData = computed(() => {
  return {
    labels: props.data.map(d => d.name),
    datasets: [{
      data: props.data.map(d => d.total_seconds),
      backgroundColor: props.data.map(d => `#${d.color}` || '#6B7280'),
      borderColor: '#111827',
      borderWidth: 0,
      hoverOffset: 4
    }]
  };
});

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  cutout: '70%',
  plugins: {
    legend: {
      position: 'right',
      labels: {
        color: '#D1D5DB',
        boxWidth: 12,
        padding: 15,
        font: { size: 11 }
      }
    },
    tooltip: {
      backgroundColor: '#1F2937',
      bodyColor: '#D1D5DB',
      callbacks: {
        label: (context) => {
          const val = context.raw;
          const h = Math.floor(val / 3600);
          const m = Math.round((val % 3600) / 60);
          return ` ${context.label}: ${h}h ${m}m`;
        }
      }
    }
  }
};
</script>
