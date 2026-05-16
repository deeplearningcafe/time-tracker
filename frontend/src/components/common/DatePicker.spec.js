import { describe, it, expect, vi, afterEach, beforeAll, afterAll } from 'vitest';
import { mount } from '@vue/test-utils';
import { createStore } from 'vuex';
import DatePicker from './DatePicker.vue';

const TestWrapper = {
  template: `
        <div>
            <DatePicker v-bind="$attrs" />
            <div data-testid="outside-area"></div>
        </div>
    `,
  components: { DatePicker },
};

// Helper to create a mock Vuex store.
const createMockStore = (liveTrackState = null) => {
  return createStore({
    modules: {
      time: {
        namespaced: true,
        getters: {
          getLiveTrack: () => liveTrackState,
        },
      },
    },
  });
};

const originalToLocaleString = Date.prototype.toLocaleString;
const originalToLocaleTimeString = Date.prototype.toLocaleTimeString;

describe('DatePicker.vue', () => {
  // Force 'en-US' locale and UTC timezone for deterministic date formatting in tests.
  beforeAll(() => {
    const mockOptions = { timeZone: 'UTC' };

    Date.prototype.toLocaleString = function (locale, options) {
      return originalToLocaleString.call(
        this, 'en-US', { ...options, ...mockOptions }
      );
    };
    Date.prototype.toLocaleTimeString = function (locale, options) {
      return originalToLocaleTimeString.call(
        this, 'en-US', { ...options, ...mockOptions }
      );
    };
  });

  afterAll(() => {
    Date.prototype.toLocaleString = originalToLocaleString;
    Date.prototype.toLocaleTimeString = originalToLocaleTimeString;
  });

  const mountComponent = (props = {}, liveTrackState = null, isWrapper = false) => {
    const store = createMockStore(liveTrackState);
    const componentToMount = isWrapper ? TestWrapper : DatePicker;

    return mount(componentToMount, {
      props: {
        modelValue: new Date('2025-09-15T12:00:00Z'),
        ...props,
      },
      global: {
        plugins: [store],
      },
      attachTo: document.body,
    });
  };

  // Clean up the component from the document body after each test.
  afterEach(() => {
    vi.useRealTimers();
    document.body.innerHTML = '';
  });

  describe('Rendering and Initial State', () => {
    it('displays the correct month and year in the header', () => {
      const wrapper = mountComponent();
      const header = wrapper.find('[data-testid="month-year-header"]');
      expect(header.text()).toBe('September 2025');
    });

    it('highlights the currently selected date via aria-selected', () => {
      const wrapper = mountComponent();
      const selectedCell = wrapper.find('[aria-selected="true"]');
      expect(selectedCell.exists()).toBe(true);
      expect(selectedCell.text()).toBe('15');
    });

    it('defaults to the current month if modelValue is not provided', () => {
      vi.useFakeTimers();
      const mockNow = new Date('2025-10-20T12:00:00Z');
      vi.setSystemTime(mockNow);

      const wrapper = mountComponent({ modelValue: undefined });
      const header = wrapper.find('[data-testid="month-year-header"]');
      expect(header.text()).toBe('October 2025');
    });
  });

  describe('Calendar Logic', () => {
    it('renders the correct number of days for a non-leap year February', () => {
      const wrapper = mountComponent({
        modelValue: new Date('2025-02-10T12:00:00Z'),
      });
      // Find cells by a generic test ID, not one per day.
      const dayCells = wrapper.findAll('[data-testid="day-cell"]');
      expect(dayCells.length).toBe(28);
    });

    it('renders the correct number of days for a leap year February', () => {
      const wrapper = mountComponent({
        modelValue: new Date('2024-02-10T12:00:00Z'),
      });
      const dayCells = wrapper.findAll('[data-testid="day-cell"]');
      expect(dayCells.length).toBe(29);
    });
  });

  describe('Store Reactivity and Time Display', () => {
    it('displays empty time fields when there is no live track', () => {
      const wrapper = mountComponent({}, null);
      const inputs = wrapper.findAll('input[type="text"]');
      expect(inputs[0].element.value).toBe('');
      expect(inputs[1].element.value).toBe('');
    });

    it('displays static start and end times for a completed track', () => {
      const completedTrack = {
        start_time: new Date('2025-09-15T09:00:00Z'),
        end_time: new Date('2025-09-15T10:30:00Z'),
      };
      const wrapper = mountComponent({}, completedTrack);
      const inputs = wrapper.findAll('input[type="text"]');
      expect(inputs[0].element.value).toBe('9:00 AM');
      expect(inputs[1].element.value).toBe('10:30 AM');
    });

    it('displays a dynamically updating end time for a running track', async () => {
      vi.useFakeTimers();
      const startTime = new Date('2025-09-15T14:00:00Z');
      vi.setSystemTime(startTime);

      const runningTrack = {
        start_time: startTime,
        end_time: null,
      };

      const wrapper = mountComponent({}, runningTrack);
      const inputs = wrapper.findAll('input[type="text"]');
      const endTimeInput = inputs[1];

      // Initial state should show the same start and end time
      expect(inputs[0].element.value).toContain('2:00 PM');
      expect(endTimeInput.element.value).toContain('2:00 PM');

      // Advance time by 1 minute and 10 seconds
      await vi.advanceTimersByTimeAsync(70000);
      await wrapper.vm.$nextTick();

      expect(endTimeInput.element.value).toBe('2:01 PM');
    });
  });

  describe('User Interactions', () => {
    it('navigates to the next month on button click', async () => {
      const wrapper = mountComponent();
      await wrapper.find('[data-testid="next-month-btn"]').trigger('click');
      const header = wrapper.find('[data-testid="month-year-header"]');
      expect(header.text()).toBe('October 2025');
    });

    it('navigates to the previous month on button click', async () => {
      const wrapper = mountComponent();
      await wrapper.find('[data-testid="prev-month-btn"]').trigger('click');
      const header = wrapper.find('[data-testid="month-year-header"]');
      expect(header.text()).toBe('August 2025');
    });

    it('navigates to the previous year when going back from January', async () => {
      const wrapper = mountComponent({
        modelValue: new Date('2026-01-15T12:00:00Z'),
      });
      await wrapper.find('[data-testid="prev-month-btn"]').trigger('click');
      const header = wrapper.find('[data-testid="month-year-header"]');
      expect(header.text()).toBe('December 2025');
    });

    it('emits @date-selected with correct date when a day is clicked', async () => {
      const wrapper = mountComponent();
      const dayCells = wrapper.findAll('[data-testid="day-cell"]');
      const targetCell = dayCells.find(cell => cell.text() === '22');
      await targetCell.trigger('click');

      const emittedEvent = wrapper.emitted('date-selected');
      expect(emittedEvent).toHaveLength(1);

      const selectedDate = emittedEvent[0][0];
      const expectedDate = new Date('2025-09-22T12:00:00Z');

      expect(selectedDate.toDateString()).toBe(expectedDate.toDateString());
    });

    it('emits a @close event when a click occurs outside the component', async () => {
      const wrapper = mountComponent({ modelValue: new Date() }, null, true);

      const datePicker = wrapper.findComponent(DatePicker);

      // Simulate a click on the element outside the date picker.
      await wrapper.find('[data-testid="outside-area"]').trigger('mousedown');

      expect(datePicker.emitted('close')).toHaveLength(1);
    });
  });
});
