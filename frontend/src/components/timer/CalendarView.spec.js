import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount } from '@vue/test-utils';
import { createStore } from 'vuex';
import CalendarView from './CalendarView.vue';

vi.mock('./TimeTrackBlock.vue', () => ({
  default: {
    name: 'TimeTrackBlock',
    props: ['track', 'height', 'top'],
    template: `
            <div
                class="time-track-block-mock"
                :style="{ height: height + 'px', top: top + 'px' }"
                @mousedown.stop="$emit('track-mousedown', $event, track)">
            </div>
        `,
  },
}));

vi.mock('./CurrentTimeIndicator.vue', () => ({
  default: {
    name: 'CurrentTimeIndicator',
    template: '<div data-testid="time-indicator-mock"></div>',
  },
}));


describe('CalendarView.vue', () => {
  let store;
  let mockTracks;

  const mockDate = new Date('2025-09-22T10:00:00Z');

  const mockElementMetrics = {
    top: 0,
    height: 1440,
    left: 0,
    right: 1000,
    width: 1000,
    x: 0,
    y: 0,
    toJSON: () => { },
  };

  const timeToPixels = (hour, minute = 0) => (hour * 60 + minute);

  const createMockStore = ({ viewType = 'day', timeTracks = mockTracks, customWeek = null } = {}) => {
    return createStore({
      modules: {
        ui: {
          namespaced: true,
          getters: {
            getHourHeight: () => 60,
            getCurrentDate: () => mockDate,
            getViewType: () => viewType,
            getWeek: () => {
              if (customWeek) return customWeek;
              const week = [];
              const start = new Date(mockDate); // Monday
              const diff = start.getDate() - start.getDay();
              const sunday = new Date(start.setDate(diff));
              for (let i = 0; i < 7; i++) {
                const d = new Date(sunday);
                d.setDate(sunday.getDate() + i);
                week.push(d);
              }
              return week;
            },
          }
        },
        time: {
          namespaced: true,
          state: { timeTracks },
          getters: {
            hydrateTrack: () => (track) => ({
              ...track,
              name: track.name || 'Mock Entry',
              project_title: track.project_title || 'Mock Project'
            }),
            dailyTotalDuration: () => () => 3600,
          }
        }
      }
    });
  };

  beforeEach(() => {
    // 1. Mock System Time
    vi.useFakeTimers();
    vi.setSystemTime(mockDate);

    // 2. Mock DOM APIs
    vi.spyOn(Element.prototype, 'getBoundingClientRect')
      .mockImplementation(() => mockElementMetrics);

    // Mock clientWidth. Configurable so we can change it for Week View tests.
    Object.defineProperty(HTMLElement.prototype, 'clientWidth', {
      configurable: true,
      value: 1000,
    });

    // Mock CSS Variable for hour height (60px = 1px/min)
    vi.spyOn(window, 'getComputedStyle').mockImplementation(() => ({
      getPropertyValue: (prop) => {
        if (prop === '--hour-height') return '60px';
        return '';
      },
    }));

    mockTracks = {
      1: {
        id: 1,
        time_entry: 10,
        start_time: '2025-09-22T09:00:00Z',
        end_time: '2025-09-22T10:00:00Z'
      },
      2: {
        id: 2,
        time_entry: 11,
        start_time: '2025-09-22T09:30:00Z',
        end_time: null
      }
    };

    store = createMockStore();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  const createWrapper = (customStore) => {
    return mount(CalendarView, {
      global: {
        plugins: [customStore]
      }
    });
  };

  describe('Rendering & Logic', () => {
    it('renders TimeTrackBlocks for visible tracks', () => {
      const wrapper = createWrapper(store);
      const trackBlocks = wrapper.findAllComponents({ name: 'TimeTrackBlock' });
      expect(trackBlocks.length).toBe(2);
    });

    it('calculates correct height for a live track based on current time', async () => {
      const wrapper = createWrapper(store);

      // Track 2 starts at 09:30. Current time is 10:00.
      // Duration = 30 mins. At 1px/min, height should be 30px.
      const liveTrackBlock = wrapper.findAllComponents({ name: 'TimeTrackBlock' })[1];
      expect(liveTrackBlock.props('height')).toBe(30);

      vi.advanceTimersByTime(15 * 60 * 1000);
      await wrapper.vm.$nextTick();

      // New duration = 45 mins -> 45px height
      expect(liveTrackBlock.props('height')).toBe(45);
    });

    it('renders 7 columns in Week View', () => {
      const weekStore = createMockStore({ viewType: 'week', timeTracks: {} });

      const wrapper = createWrapper(weekStore);
      const columns = wrapper.findAll('.relative.flex-1.border-l');
      expect(columns.length).toBe(7);
    });

    it('parses correctly time tracks spanning multiple days', () => {
      const multiDayTrack = {
        id: 3,
        time_entry: 10,
        start_time: '2025-09-22T20:00:00Z',
        end_time: '2025-09-24T04:00:00Z'
      };

      const customWeek = [];
      for (let i = 0; i < 7; i++) {
        const d = new Date('2025-09-21T00:00:00Z');
        d.setDate(d.getDate() + i);
        customWeek.push(d);
      }

      const customStore = createMockStore({
        viewType: 'week',
        timeTracks: { 3: multiDayTrack },
        customWeek
      });

      const wrapper = createWrapper(customStore);
      const trackBlocks = wrapper.findAllComponents({ name: 'TimeTrackBlock' });

      expect(trackBlocks.length).toBe(3);
    });
  });

  describe('User Interactions', () => {
    it('emits @request-create-track on a valid drag gesture', async () => {
      const wrapper = createWrapper(store);
      const grid = wrapper.find('.relative.flex-grow');

      // 1. Start Drag at 11:00 AM (660px)
      // clientX 10 puts it in the first (and only) column
      await grid.trigger('mousedown', { clientX: 10, clientY: timeToPixels(11) });

      // 2. Move Mouse to 12:30 PM (750px)
      // Events are attached to window, so we dispatch there
      window.dispatchEvent(new MouseEvent('mousemove', {
        clientX: 10,
        clientY: timeToPixels(12, 30)
      }));

      window.dispatchEvent(new MouseEvent('mouseup', {
        clientX: 10,
        clientY: timeToPixels(12, 30)
      }));

      await wrapper.vm.$nextTick();

      const emitted = wrapper.emitted('request-create-track');
      expect(emitted).toBeTruthy();
      expect(emitted).toHaveLength(1);

      const payload = emitted[0][0];
      expect(payload.start_time.getHours()).toBe(11);
      expect(payload.start_time.getMinutes()).toBe(0);
      expect(payload.end_time.getHours()).toBe(12);
      expect(payload.end_time.getMinutes()).toBe(30);
    });

    it('emits correctly ordered times when dragging upwards (swap logic)', async () => {
      const wrapper = createWrapper(store);
      const grid = wrapper.find('.relative.flex-grow');

      // 1. Start Drag at 14:00
      await grid.trigger('mousedown', { clientX: 10, clientY: timeToPixels(14) });

      // 2. Release Mouse UP at 13:00
      window.dispatchEvent(new MouseEvent('mouseup', {
        clientX: 10,
        clientY: timeToPixels(13)
      }));

      await wrapper.vm.$nextTick();

      const emitted = wrapper.emitted('request-create-track');
      expect(emitted).toBeTruthy();
      const payload = emitted[0][0];

      // Should automatically swap start and end
      expect(payload.start_time.getHours()).toBe(13);
      expect(payload.end_time.getHours()).toBe(14);
    });

    it('emits @select-track when a TimeTrackBlock is clicked', async () => {
      const wrapper = createWrapper(store);
      const block = wrapper.find('.time-track-block-mock');

      await block.trigger('mousedown', { clientY: 100 });

      window.dispatchEvent(new MouseEvent('mouseup', { clientY: 100 }));

      await wrapper.vm.$nextTick();

      const emitted = wrapper.emitted('select-track');
      expect(emitted).toBeTruthy();
      expect(emitted[0][0].id).toBe(1);
    });

    it('does not emit @request-create-track on a simple click (no drag)', async () => {
      const wrapper = createWrapper(store);
      const grid = wrapper.find('.relative.flex-grow');

      // Click without moving
      await grid.trigger('mousedown', { clientX: 10, clientY: timeToPixels(10) });
      window.dispatchEvent(new MouseEvent('mouseup', {
        clientX: 10,
        clientY: timeToPixels(10)
      }));

      await wrapper.vm.$nextTick();

      expect(wrapper.emitted('request-create-track')).toBeUndefined();
    });
  });
});
