import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import { createStore } from 'vuex';
import SummaryView from './SummaryView.vue';

vi.mock('../components/summary/DateRangeNavigator.vue', () => ({
  default: {
    name: 'DateRangeNavigator',
    template: '<div data-testid="navigator"></div>'
  },
}));
vi.mock('../components/summary/SummaryMetrics.vue', () => ({
  default: {
    name: 'SummaryMetrics',
    props: ['totalSeconds', 'dailyAverage'],
    template: '<div data-testid="summary-metrics"></div>'
  },
}));
vi.mock('../components/summary/DurationBarChart.vue', () => ({
  default: {
    name: 'DurationBarChart',
    props: ['data'],
    template: '<div data-testid="bar-chart"></div>'
  },
}));
vi.mock('../components/summary/ProjectPieChart.vue', () => ({
  default: {
    name: 'ProjectPieChart',
    props: ['data'],
    template: '<div data-testid="pie-chart"></div>'
  },
}));
vi.mock('../components/summary/ProjectBreakdownList.vue', () => ({
  default: {
    name: 'ProjectBreakdownList',
    props: ['breakdownData'],
    template: '<div data-testid="breakdown-list"></div>'
  },
}));

describe('SummaryView.vue', () => {
  let store;
  let timeActions;
  let uiState;

  const mockDate = new Date('2025-09-18T12:00:00');

  const createVuexStore = (initialTimeState = {}) => {
    timeActions = {
      fetchSummary: vi.fn(),
    };

    uiState = {
      currentDate: mockDate,
      viewType: 'week',
    };

    return createStore({
      modules: {
        ui: {
          namespaced: true,
          state: uiState,
          getters: {
            getCurrentDate: (state) => state.currentDate,
            getViewType: (state) => state.viewType,
            getShortcutRange: () => () => {
              const start = new Date(mockDate);
              start.setHours(0, 0, 0, 0);
              const day = start.getDay(); // 0=Sun, 1=Mon...
              // Test expects Monday start.
              // If day is 0 (Sun), we want to go back to previous Monday (-6 days).
              // If day is 1 (Mon), we stay (0 days).
              const diff = day === 0 ? 6 : day - 1;
              start.setDate(start.getDate() - diff);

              const end = new Date(start);
              end.setDate(start.getDate() + 6);
              end.setHours(23, 59, 59, 999);

              return { startDate: start, endDate: end, type: 'week' };
            },
            getAdjacentRange: () => () => {
              return {
                startDate: new Date('2025-09-22T00:00:00.000Z'),
                endDate: new Date('2025-09-28T23:59:59.999Z'),
                type: 'week'
              };
            }

          },
        },
        time: {
          namespaced: true,
          state: {
            summaryData: [], // Default empty array
            status: { summary: 'idle' },
            ...initialTimeState
          },
          namespaced: true,
          actions: timeActions,
        },
      },
    });
  };

  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(mockDate);
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  const mountComponent = (customStore) => {
    return mount(SummaryView, {
      global: { plugins: [customStore] },
    });
  };

  describe('Lifecycle & Data Fetching', () => {
    it('dispatches fetchSummary with correct week range on mount', async () => {
      store = createVuexStore();
      mountComponent(store);

      // Week Start (Sunday) = Sept 14.
      // Week End (Sunday) = Sept 21.
      const expectedStart = '2025-09-14T22:00:00.000Z';
      const expectedEnd = '2025-09-21T21:59:59.999Z';

      expect(timeActions.fetchSummary).toHaveBeenCalledTimes(1);
      const payload = timeActions.fetchSummary.mock.calls[0][1];

      // Verify date strings match
      expect(payload.startDate.toString()).toBe(expectedStart);
      expect(payload.endDate.toString()).toBe(expectedEnd);
    });

    it('re-dispatches fetchSummary when DateRangeNavigator emits set-range', async () => {
      store = createVuexStore();
      const wrapper = mountComponent(store);
      timeActions.fetchSummary.mockClear();

      const navigator = wrapper.findComponent({ name: 'DateRangeNavigator' });

      const newStart = new Date('2025-09-22T00:00:00.000Z');
      const newEnd = new Date('2025-09-28T23:59:59.999Z');

      await navigator.vm.$emit('set-range', { startDate: newStart, endDate: newEnd, type: 'week' });

      await wrapper.vm.$nextTick();
      await flushPromises();

      expect(timeActions.fetchSummary).toHaveBeenCalledTimes(1);
      const payload = timeActions.fetchSummary.mock.calls[0][1];

      expect(payload.startDate).toBe(newStart.toISOString());
    });

    it('updates dateRange and re-dispatches fetchSummary when DateRangeNavigator emits range-change', async () => {
      store = createVuexStore();
      const wrapper = mountComponent(store);
      timeActions.fetchSummary.mockClear();

      const navigator = wrapper.findComponent({ name: 'DateRangeNavigator' });
      await navigator.vm.$emit('range-change', 1);

      await wrapper.vm.$nextTick();
      await flushPromises();

      expect(timeActions.fetchSummary).toHaveBeenCalledTimes(1);
      const payload = timeActions.fetchSummary.mock.calls[0][1];
      expect(payload.startDate).toBe(new Date('2025-09-22T00:00:00.000Z').toISOString());
    });

  });

  describe('State Handling (Loading & Error)', () => {
    it('renders loading state correctly', () => {
      store = createVuexStore({
        status: { summary: 'loading' }
      });
      const wrapper = mountComponent(store);

      expect(wrapper.findComponent({ name: 'DurationBarChart' }).exists()).toBe(false);
      // Check for loading text/spinner
      expect(wrapper.text()).toMatch(/loading/i);
    });

    it('renders error state correctly', () => {
      store = createVuexStore({
        status: { summary: 'error' }
      });
      const wrapper = mountComponent(store);

      expect(wrapper.text()).toMatch(/failed/i);
    });
  });

  describe('Data Transformation & Prop Passing', () => {
    const mockBackendData = [
      {
        date: '2025-09-15', // Monday
        project: 'Project A',
        project_color: '#FF0000',
        time_entry: 'Task 1',
        duration_seconds: 3600
      },
      {
        date: '2025-09-15',
        project: 'Project B',
        project_color: '#00FF00',
        time_entry: 'Task 2',
        duration_seconds: 1800
      },
      {
        date: '2025-09-16',
        project: 'Project A',
        project_color: '#FF0000',
        time_entry: 'Task 3',
        duration_seconds: 7200
      }
    ];

    beforeEach(() => {
      store = createVuexStore({
        summaryData: mockBackendData,
        status: { summary: 'success' }
      });
    });

    it('computes and passes correct data to DurationBarChart', () => {
      const wrapper = mountComponent(store);
      const chart = wrapper.findComponent({ name: 'DurationBarChart' });

      expect(chart.exists()).toBe(true);
      const data = chart.props('data');

      // The component pre-fills all days in the range (7 days for a week).
      expect(data).toHaveLength(7);

      const day1 = data.find(d => d.date === '2025-09-15');
      expect(day1.duration_seconds).toBe(5400);

      const day2 = data.find(d => d.date === '2025-09-16');
      expect(day2.duration_seconds).toBe(7200);
    });

    it('computes and passes correct data to ProjectPieChart', () => {
      const wrapper = mountComponent(store);
      const chart = wrapper.findComponent({ name: 'ProjectPieChart' });

      const data = chart.props('data');

      // Expect aggregation by project
      // Project A: 3600 + 7200 = 10800
      // Project B: 1800
      expect(data).toHaveLength(2);

      const projA = data.find(p => p.name === 'Project A');
      expect(projA.total_seconds).toBe(10800);
      expect(projA.color).toBe('#FF0000');

      const projB = data.find(p => p.name === 'Project B');
      expect(projB.total_seconds).toBe(1800);
    });

    it('computes and passes correct metrics to SummaryMetrics', () => {
      const wrapper = mountComponent(store);
      const metrics = wrapper.findComponent({ name: 'SummaryMetrics' });

      // Total Seconds: 3600 + 1800 + 7200 = 12600
      expect(metrics.props('totalSeconds')).toBe(12600);

      // Daily Average: 12600 / 7 days (standard week view) = 1800
      const avg = metrics.props('dailyAverage');
      expect(avg).toBeGreaterThan(0);
      expect(avg).toBe(1800);
    });

    it('computes and passes correct breakdown to ProjectBreakdownList', () => {
      const wrapper = mountComponent(store);
      const list = wrapper.findComponent({ name: 'ProjectBreakdownList' });

      const breakdown = list.props('breakdownData');

      // Should be grouped by Project -> Entries
      const projA = breakdown.find(p => p.project === 'Project A');
      expect(projA).toBeTruthy();
      expect(projA.total_seconds).toBe(10800);

      expect(projA.entries).toHaveLength(2);
      expect(projA.entries.find(e => e.name === 'Task 1').duration).toBe(3600);
      expect(projA.entries.find(e => e.name === 'Task 3').duration).toBe(7200);
    });
  });
});
