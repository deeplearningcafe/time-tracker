import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import { createStore } from 'vuex';
import TimerView from './TimerView.vue';

const pushMock = vi.fn();
vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: pushMock
  })
}));

vi.mock('../components/timer/LiveTimer.vue', () => ({
  default: {
    name: 'LiveTimer',
    template: '<div></div>',
    emits: ['request-start-live-timer', 'request-stop-live-timer']
  },
}));
vi.mock('../components/timer/CalendarToolbar.vue', () => ({
  default: { name: 'CalendarToolbar', template: '<div></div>' },
}));
vi.mock('../components/CalendarView.vue', () => ({
  default: {
    name: 'CalendarView',
    props: ['tracks', 'currentDate', 'viewType'],
    template: '<div data-testid="calendar-view-mock"></div>',
    emits: ['request-create-track', 'select-track']
  },
}));
vi.mock('../components/modals/EditEntryModal.vue', () => ({
  default: {
    name: 'EditEntryModal',
    props: ['isVisible', 'track', 'initialTimes'],
    template: '<div v-if="isVisible" data-testid="edit-modal-mock"></div>',
    emits: ['save', 'delete', 'close']
  },
}));



describe('TimerView.vue', () => {
  let store;
  let actions;
  let uiActions;

  const mockDate = new Date('2025-09-18T12:00:00');

  const createVuexStore = (isAuthenticated = true) => {
    actions = {
      fetchRangeData: vi.fn(),
      fetchProjects: vi.fn(),
      fetchRecentTimeEntries: vi.fn(),
      fetchLiveTrack: vi.fn(),
      createTrack: vi.fn(),
      updateTrack: vi.fn(),
      deleteTrack: vi.fn(),
      startNewLiveTrack: vi.fn(),
      stopTimer: vi.fn(),
    };

    uiActions = {
      setGlobalError: vi.fn(),
    };

    return createStore({
      modules: {
        auth: {
          namespaced: true,
          getters: { isAuthenticated: () => isAuthenticated },
        },
        ui: {
          namespaced: true,
          state: {
            currentDate: mockDate,
            viewType: 'day'
          },
          getters: {
            getCurrentDate: (state) => state.currentDate,
            getViewType: (state) => state.viewType,
            getDateRange: (state) => {
              const start = new Date(state.currentDate);
              start.setHours(0, 0, 0, 0);
              const end = new Date(state.currentDate);
              end.setHours(23, 59, 59, 999);
              return { startDate: start, endDate: end };
            },
            getWeek: (state) => {
              const week = [];
              const start = new Date(state.currentDate);
              const diff = start.getDate() - start.getDay();
              const sunday = new Date(start.setDate(diff));
              for (let i = 0; i < 7; i++) {
                const d = new Date(sunday);
                d.setDate(sunday.getDate() + i);
                week.push(d);
              }
              return week;
            },
            getHourHeight: () => 60,
          },
          actions: uiActions,
        },
        time: {
          namespaced: true,
          state: { timeTracks: [] },
          getters: {
            tracksForView: (state) => state.timeTracks,
            dailyTotalDuration: () => () => 3600,
          },
          actions: actions,
        },
      },
    });
  };

  beforeEach(() => {
    pushMock.mockClear();
    vi.useFakeTimers();
    vi.setSystemTime(mockDate);
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  const mountComponent = (customStore) => {
    return mount(TimerView, {
      global: { plugins: [customStore] },
    });
  };

  describe('Data Fetching & Lifecycle', () => {
    it('dispatches initial data fetch actions on mount', async () => {
      store = createVuexStore();
      mountComponent(store);

      expect(actions.fetchProjects).toHaveBeenCalled();
      expect(actions.fetchRecentTimeEntries).toHaveBeenCalled();
      expect(actions.fetchLiveTrack).toHaveBeenCalled();

      // always fetchs whole week despite view type
      const dayOfWeek = mockDate.getDay();
      // Start the week on Monday (day 0)
      const diff = mockDate.getDate() - dayOfWeek;
      const expectedStart = new Date(mockDate.setDate(diff));
      expectedStart.setHours(0, 0, 0, 0);
      const expectedEnd = new Date(expectedStart);
      expectedEnd.setDate(expectedStart.getDate() + 6);

      expectedEnd.setHours(23, 59, 59, 999);

      expect(actions.fetchRangeData).toHaveBeenCalledWith(
        expect.anything(), // context
        { startDate: expectedStart.toISOString(), endDate: expectedEnd.toISOString() }
      );
    });

    it('redirects to login if not authenticated', async () => {
      store = createVuexStore(false); // Not authenticated
      mountComponent(store);

      await flushPromises();

      expect(pushMock).toHaveBeenCalledWith({ name: 'logger' });
    });

    it('re-fetches tracks when the currentDate in the store changes', async () => {
      store = createVuexStore();
      const wrapper = mountComponent(store);

      actions.fetchRangeData.mockClear();

      const newDate = new Date('2025-09-10T12:00:00');
      store.state.ui.currentDate = newDate;

      await wrapper.vm.$nextTick();
      await flushPromises();

      const dayOfWeek = newDate.getDay();
      const diff = newDate.getDate() - dayOfWeek;
      const expectedStart = new Date(newDate.setDate(diff));
      expectedStart.setHours(0, 0, 0, 0);
      const expectedEnd = new Date(expectedStart);
      expectedEnd.setDate(expectedStart.getDate() + 6);

      expectedEnd.setHours(23, 59, 59, 999);

      expect(actions.fetchRangeData).toHaveBeenCalledWith(
        expect.anything(),
        { startDate: expectedStart.toISOString(), endDate: expectedEnd.toISOString() }
      );
    });
  });

  describe('Modal Interactions & State Management', () => {
    it('opens modal in create mode on request-create-track event', async () => {
      store = createVuexStore();
      const wrapper = mountComponent(store);
      const calendarView = wrapper.findComponent({ name: 'CalendarView' });

      const newTrackTimes = {
        start_time: new Date('2025-09-18T10:00:00'),
        end_time: new Date('2025-09-18T11:00:00'),
      };

      await calendarView.vm.$emit('request-create-track', newTrackTimes);

      expect(wrapper.vm.isModalVisible).toBe(true);
      expect(wrapper.vm.selectedTrack).toBeNull();
      expect(wrapper.vm.newTrackTimes).toEqual(newTrackTimes);
    });

    it('opens modal in edit mode on select-track event', async () => {
      store = createVuexStore();
      const wrapper = mountComponent(store);
      const calendarView = wrapper.findComponent({ name: 'CalendarView' });
      const trackToEdit = { id: 1, name: 'Existing Task' };

      await calendarView.vm.$emit('select-track', trackToEdit);

      expect(wrapper.vm.isModalVisible).toBe(true);
      expect(wrapper.vm.selectedTrack).toEqual(trackToEdit);
    });

    it('dispatches createTrack and closes modal on save for new track', async () => {
      store = createVuexStore();
      const wrapper = mountComponent(store);

      // Simulate Create Mode
      await wrapper.findComponent({ name: 'CalendarView' }).vm.$emit('request-create-track', {});

      const newTrackData = { name: 'New Task', project: 1 };
      await wrapper.findComponent({ name: 'EditEntryModal' }).vm.$emit('save', newTrackData);

      await flushPromises();

      expect(actions.createTrack).toHaveBeenCalledWith(
        expect.anything(),
        { trackData: newTrackData }
      );
      expect(wrapper.vm.isModalVisible).toBe(false);
    });

    it('dispatches updateTrack and closes modal on save for existing track', async () => {
      store = createVuexStore();
      const wrapper = mountComponent(store);

      // Simulate Edit Mode
      const track = { id: 5, name: 'Old Name' };
      await wrapper.findComponent({ name: 'CalendarView' }).vm.$emit('select-track', track);

      const updatedData = { id: 5, name: 'Updated Name' };
      await wrapper.findComponent({ name: 'EditEntryModal' }).vm.$emit('save', updatedData);

      await flushPromises();

      expect(actions.updateTrack).toHaveBeenCalledWith(
        expect.anything(),
        { trackData: updatedData }
      );
      expect(wrapper.vm.isModalVisible).toBe(false);
    });

    it('dispatches deleteTrack and closes modal on delete', async () => {
      store = createVuexStore();
      const wrapper = mountComponent(store);

      await wrapper.findComponent({ name: 'CalendarView' }).vm.$emit('select-track', { id: 10 });
      await wrapper.findComponent({ name: 'EditEntryModal' }).vm.$emit('delete', 10);

      await flushPromises();

      expect(actions.deleteTrack).toHaveBeenCalledWith(
        expect.anything(),
        { trackId: 10 }
      );
      expect(wrapper.vm.isModalVisible).toBe(false);
    });

    it('resets state on @close event without dispatching actions', async () => {
      store = createVuexStore();
      const wrapper = mountComponent(store);

      await wrapper.findComponent({ name: 'CalendarView' }).vm.$emit('select-track', { id: 10 });
      await wrapper.findComponent({ name: 'EditEntryModal' }).vm.$emit('close');

      expect(wrapper.vm.isModalVisible).toBe(false);
      expect(wrapper.vm.selectedTrack).toBeNull();
    });

    it('keeps modal open and state intact if a save action fails', async () => {
      store = createVuexStore();
      const wrapper = mountComponent(store);

      await wrapper.findComponent({ name: 'CalendarView' }).vm.$emit(
        'request-create-track', {}
      );
      await wrapper.findComponent({ name: 'EditEntryModal' }).vm.$emit(
        'save', { name: '' }
      );

      expect(wrapper.vm.isModalVisible).toBe(true);
    });
  });

  describe('Live Timer Interactions', () => {
    it('dispatches startNewLiveTrack when LiveTimer requests start', async () => {
      store = createVuexStore();
      const wrapper = mountComponent(store);
      const liveTimer = wrapper.findComponent({ name: 'LiveTimer' });

      const payload = { name: 'Live Task', project: 2 };
      await liveTimer.vm.$emit('request-start-live-timer', payload);

      expect(actions.startNewLiveTrack).toHaveBeenCalledWith(
        expect.anything(),
        { name: payload.name, project: payload.project }
      );
    });

    it('dispatches stopTimer when LiveTimer requests stop', async () => {
      store = createVuexStore();
      const wrapper = mountComponent(store);
      const liveTimer = wrapper.findComponent({ name: 'LiveTimer' });

      const trackPayload = { value: { id: 99 } };
      await liveTimer.vm.$emit('request-stop-live-timer', { track: trackPayload });

      expect(actions.stopTimer).toHaveBeenCalledWith(
        expect.anything(),
        { track: trackPayload.value }
      );
    });
  });

  describe('Error Handling', () => {
    it('dispatches ui/setGlobalError when fetch fails', async () => {
      store = createVuexStore();
      actions.fetchRangeData.mockRejectedValueOnce(new Error('Network Error'));

      mountComponent(store);
      await flushPromises();

      expect(uiActions.setGlobalError).toHaveBeenCalledWith(
        expect.anything(),
        { message: expect.stringContaining('Failed to fetch time data') }
      );
    });

    it('keeps modal open and shows error when save fails', async () => {
      store = createVuexStore();
      const wrapper = mountComponent(store);

      actions.createTrack.mockRejectedValueOnce(new Error('Validation Failed'));

      await wrapper.findComponent({ name: 'CalendarView' }).vm.$emit('request-create-track', {});
      await wrapper.findComponent({ name: 'EditEntryModal' }).vm.$emit('save', { name: 'Bad Data' });

      await flushPromises();

      expect(uiActions.setGlobalError).toHaveBeenCalledWith(
        expect.anything(),
        { message: expect.stringContaining('Failed to save track') }
      );
      expect(wrapper.vm.isModalVisible).toBe(true); // Modal stays open
    });
  });

});
