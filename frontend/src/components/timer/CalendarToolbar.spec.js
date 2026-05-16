import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { mount } from '@vue/test-utils';
import { createStore } from 'vuex';

import CalendarToolbar from './CalendarToolbar.vue';

vi.mock('../common/TimePicker.vue', () => ({
  default: {
    name: 'TimePicker',
    template: '<div data-testid="time-picker-mock"></div>'
  }
}));

const INITIAL_DATE = new Date('2025-09-18T12:00:00Z');
const MIN_ZOOM = 0;
const MAX_ZOOM = 7;

const createMockStore = (viewType = 'day', zoomLevel = 3) => {
  return createStore({
    modules: {
      ui: {
        namespaced: true,
        state: {
          currentDate: INITIAL_DATE,
          viewType: viewType,
          zoomLevel: zoomLevel,
        },
        getters: {
          getCurrentDate: (state) => state.currentDate,
          getViewType: (state) => state.viewType,
          getZoomLevel: (state) => state.zoomLevel,
          getMaxZoomLevel: () => MAX_ZOOM,
          getWeek: () => [new Date(), new Date(), new Date(), new Date(), new Date(), new Date(), new Date()],
        },
        actions: {
          setDate: vi.fn(),
          setViewType: vi.fn(),
          changeZoom: vi.fn(),
        }
      },
      time: {
        namespaced: true,
        getters: {
          weeklyTotalDuration: () => () => 3600,
          dailyProjectDistribution: () => () => [],
        }
      }
    },
  });
};

// Store original methods to be restored later.
const originalToLocaleString = Date.prototype.toLocaleString;
const originalToLocaleTimeString = Date.prototype.toLocaleTimeString;
const originalToLocaleDateString = Date.prototype.toLocaleDateString;

describe('CalendarToolbar.vue', () => {
  let mockStore;

  beforeEach(() => {
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
    Date.prototype.toLocaleDateString = function (locale, options) {
      return originalToLocaleDateString.call(
        this, 'en-US', { ...options, ...mockOptions }
      );
    };

    mockStore = createMockStore();
  });

  afterEach(() => {
    Date.prototype.toLocaleString = originalToLocaleString;
    Date.prototype.toLocaleTimeString = originalToLocaleTimeString;
    vi.useRealTimers();
  });

  const mountComponent = (store = mockStore) => {
    return mount(CalendarToolbar, {
      global: {
        plugins: [store],
      },
    });
  };

  describe('Rendering and State Display', () => {
    it('displays the key date components for the day view', () => {
      const wrapper = mountComponent();
      const dateDisplay = wrapper.find('[data-testid="date-display"]');
      expect(dateDisplay.text()).toContain('Sep');
      expect(dateDisplay.text()).toContain('18');
      expect(dateDisplay.text()).toContain('2025');
    });

    it('displays the key date components for the week view', () => {
      mockStore = createMockStore('week');
      const wrapper = mountComponent(mockStore);
      const dateDisplay = wrapper.find('[data-testid="date-display"]');
      // For a week view, we just check for the month and year.
      expect(dateDisplay.text()).toContain('Sep');
      expect(dateDisplay.text()).toContain('2025');
    });

    it('applies an active class and aria-pressed to the correct view button', () => {
      const wrapper = mountComponent(createMockStore('week'));
      const dayButton = wrapper.find('[data-testid="day-view-button"]');
      const weekButton = wrapper.find('[data-testid="week-view-button"]');

      // Check Visual State (Tailwind classes)
      expect(weekButton.classes()).toContain('bg-blue-600');
      expect(weekButton.classes()).toContain('text-white');
      expect(dayButton.classes()).not.toContain('bg-blue-600');

      expect(weekButton.attributes('aria-pressed')).toBe('true');
      expect(dayButton.attributes('aria-pressed')).toBe('false');
    });
  });

  describe('Date Navigation', () => {
    it('dispatches setDate with the previous day on "prev" click in day view', async () => {
      const dispatchSpy = vi.spyOn(mockStore, 'dispatch');
      const wrapper = mountComponent();
      await wrapper.find('[data-testid="prev-button"]').trigger('click');

      const expectedDate = new Date('2025-09-17T12:00:00.000Z');
      expect(dispatchSpy).toHaveBeenCalledWith('ui/setDate', {
        newDate: expectedDate,
      });
    });

    it('dispatches setDate with the next day on "next" click in day view', async () => {
      const dispatchSpy = vi.spyOn(mockStore, 'dispatch');
      const wrapper = mountComponent();
      await wrapper.find('[data-testid="next-button"]').trigger('click');

      const expectedDate = new Date('2025-09-19T12:00:00.000Z');
      expect(dispatchSpy).toHaveBeenCalledWith('ui/setDate', {
        newDate: expectedDate,
      });
    });

    it('dispatches setDate with the previous week on "prev" click in week view', async () => {
      const weekStore = createMockStore('week');
      const dispatchSpy = vi.spyOn(weekStore, 'dispatch');
      const wrapper = mountComponent(weekStore);

      await wrapper.find('[data-testid="prev-button"]').trigger('click');

      const expectedDate = new Date('2025-09-11T12:00:00.000Z');
      expect(dispatchSpy).toHaveBeenCalledWith('ui/setDate', {
        newDate: expectedDate,
      });
    });

    it('dispatches setDate with the next week on "next" click in week view', async () => {
      const weekStore = createMockStore('week');
      const dispatchSpy = vi.spyOn(weekStore, 'dispatch');
      const wrapper = mountComponent(weekStore);

      await wrapper.find('[data-testid="next-button"]').trigger('click');

      const expectedDate = new Date('2025-09-25T12:00:00.000Z');
      expect(dispatchSpy).toHaveBeenCalledWith('ui/setDate', {
        newDate: expectedDate,
      });
    });

    it('toggles the time picker on "Today" (date display) click', async () => {
      const wrapper = mountComponent();

      expect(wrapper.findComponent({ name: 'TimePicker' }).exists()).toBe(false);

      await wrapper.find('[data-testid="timepicker-button"]').trigger('click');

      expect(wrapper.findComponent({ name: 'TimePicker' }).exists()).toBe(true);
    });

    it('dispatches setDate and setViewType when TimePicker emits set-date', async () => {
      const wrapper = mountComponent();
      const dispatchSpy = vi.spyOn(mockStore, 'dispatch');

      // Open TimePicker
      await wrapper.find('[data-testid="timepicker-button"]').trigger('click');
      const timePicker = wrapper.findComponent({ name: 'TimePicker' });

      const newDate = new Date('2025-09-20T12:00:00.000Z');
      timePicker.vm.$emit('set-date', { date: newDate, viewType: 'week' });

      expect(dispatchSpy).toHaveBeenCalledWith('ui/setDate', { newDate });
      expect(dispatchSpy).toHaveBeenCalledWith('ui/setViewType', { type: 'week' });
    });

    it('does not dispatch setViewType if newViewType matches current viewType', async () => {
      const localStore = createMockStore('day');
      const wrapper = mountComponent(localStore);
      const dispatchSpy = vi.spyOn(localStore, 'dispatch');

      await wrapper.find('[data-testid="timepicker-button"]').trigger('click');
      const timePicker = wrapper.findComponent({ name: 'TimePicker' });

      const newDate = new Date('2025-09-20T12:00:00.000Z');
      timePicker.vm.$emit('set-date', { date: newDate, viewType: 'day' });

      expect(dispatchSpy).toHaveBeenCalledWith('ui/setDate', { newDate });
      // We check that setViewType was not called
      const setViewTypeCalls = dispatchSpy.mock.calls.filter(
        call => call[0] === 'ui/setViewType'
      );
      expect(setViewTypeCalls.length).toBe(0);
    });
  });

  describe('Zoom Controls', () => {
    it('dispatches changeZoom with -1 when "-" button is clicked', async () => {
      const dispatchSpy = vi.spyOn(mockStore, 'dispatch');
      const wrapper = mountComponent();

      const zoomOutBtn = wrapper.find('button[aria-label="Zoom out"]');
      await zoomOutBtn.trigger('click');

      expect(dispatchSpy).toHaveBeenCalledWith('ui/changeZoom', -1);
    });

    it('dispatches changeZoom with 1 when "+" button is clicked', async () => {
      const dispatchSpy = vi.spyOn(mockStore, 'dispatch');
      const wrapper = mountComponent();

      const zoomInBtn = wrapper.find('button[aria-label="Zoom in"]');
      await zoomInBtn.trigger('click');

      expect(dispatchSpy).toHaveBeenCalledWith('ui/changeZoom', 1);
    });

    it('disables zoom-out button when zoom level is at minimum', () => {
      const minZoomStore = createMockStore('day', MIN_ZOOM);
      const wrapper = mountComponent(minZoomStore);

      const zoomOutBtn = wrapper.find('button[aria-label="Zoom out"]');

      expect(zoomOutBtn.element.disabled).toBe(true);
      expect(zoomOutBtn.classes()).toContain('cursor-not-allowed');
    });

    it('disables zoom-in button when zoom level is at maximum', () => {
      const maxZoomStore = createMockStore('day', MAX_ZOOM);
      const wrapper = mountComponent(maxZoomStore);

      const zoomInBtn = wrapper.find('button[aria-label="Zoom in"]');

      expect(zoomInBtn.element.disabled).toBe(true);
      expect(zoomInBtn.classes()).toContain('cursor-not-allowed');
    });
  });

  describe('View Switching', () => {
    it.each([
      {
        startView: 'week',
        buttonToClick: 'day-view-button',
        expectedType: 'day',
      },
      {
        startView: 'day',
        buttonToClick: 'week-view-button',
        expectedType: 'week',
      },
    ])(
      'dispatches setViewType with "$expectedType" when switching from "$startView"',
      async ({ startView, buttonToClick, expectedType }) => {
        const localStore = createMockStore(startView);
        const dispatchSpy = vi.spyOn(localStore, 'dispatch');
        const wrapper = mountComponent(localStore);

        await wrapper.find(`[data-testid="${buttonToClick}"]`).trigger(
          'click'
        );

        expect(dispatchSpy).toHaveBeenCalledWith(
          'ui/setViewType',
          { type: expectedType }
        );
      }
    );

    it('does not dispatch setViewType if the view is already active', async () => {
      const dayStore = createMockStore('day');
      const dispatchSpy = vi.spyOn(dayStore, 'dispatch');
      const wrapper = mountComponent(dayStore);

      // Click the "Day" button while the view is already 'day'
      await wrapper.find('[data-testid="day-view-button"]').trigger(
        'click'
      );

      expect(dispatchSpy).not.toHaveBeenCalled();
    });
  });
});
