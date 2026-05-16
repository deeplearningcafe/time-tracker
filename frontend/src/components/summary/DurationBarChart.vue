<template>
  <Bar :data="chartData" :options="chartOptions" />
</template>

<script setup>
import { computed } from 'vue';
import {
  Chart as ChartJS,
  Title,
  Tooltip,
  Legend,
  BarElement,
  CategoryScale,
  LinearScale
} from 'chart.js';
import { Bar } from 'vue-chartjs';

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

const props = defineProps({
  data: { type: Array, required: true } // Array of { date, duration_seconds }
});

const chartData = computed(() => {
  const spansMultipleYears = props.data.length > 0 &&
    props.data[0].date.split('-')[0] !== props.data[props.data.length - 1].date.split('-')[0];

  const labels = props.data.map((d, i) => {
    const parts = d.date.split('-');
    if (parts.length === 2) {
      const date = new Date(parts[0], parts[1] - 1, 1);
      return date.toLocaleDateString(undefined, { month: 'short', year: 'numeric' });
    } else {
      const date = new Date(parts[0], parts[1] - 1, parts[2]);

      // Determine if this is a week bin (delta between labels is ~7 days)
      let isWeekBin = false;
      if (props.data.length > 1) {
        const next = props.data[i === 0 ? 1 : i - 1];
        const nextParts = next.date.split('-');
        if (nextParts.length === 3) {
          const nextDate = new Date(nextParts[0], nextParts[1] - 1, nextParts[2]);
          const diff = Math.abs(nextDate - date) / (1000 * 3600 * 24);
          // using utc implies that week could have 6/8 days
          if (diff >= 6 && diff <= 8) isWeekBin = true;
        }
      }

      if (isWeekBin) {
        // Calculate ISO week number dynamically for the chart's x-axis
        const d2 = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
        const dayNum = d2.getUTCDay() || 7;
        d2.setUTCDate(d2.getUTCDate() + 4 - dayNum);
        const yearStart = new Date(Date.UTC(d2.getUTCFullYear(), 0, 1));
        const weekNo = Math.ceil((((d2 - yearStart) / 86400000) + 1) / 7);
        return spansMultipleYears ? `W${weekNo} ${d2.getUTCFullYear()}` : `W${weekNo}`;
      }
      return date.toLocaleDateString(undefined, { weekday: 'short', day: 'numeric' });
    }
  });


  const values = props.data.map(d => d.duration_seconds / 3600); // Convert to hours

  return {
    labels,
    datasets: [{
      label: 'Hours',
      data: values,
      backgroundColor: '#60A5FA',
      hoverBackgroundColor: '#3B82F6',
      borderRadius: 4,
      barThickness: 'flex',
      maxBarThickness: 40,
    }]
  };
});

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: {
      backgroundColor: '#1F2937',
      titleColor: '#F3F4F6',
      bodyColor: '#D1D5DB',
      borderColor: '#374151',
      borderWidth: 1,
      callbacks: {
        label: (context) => {
          const val = context.raw;
          const h = Math.floor(val);
          const m = Math.round((val - h) * 60);
          return ` ${h}h ${m}m`;
        }
      }
    }
  },
  scales: {
    y: {
      beginAtZero: true,
      grid: { color: '#374151' },
      ticks: { color: '#9CA3AF' }
    },
    x: {
      grid: { display: false },
      ticks: { color: '#9CA3AF' }
    }
  }
};
</script>
