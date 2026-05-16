import { describe, it, expect, beforeEach, vi } from 'vitest';
import { createStore } from 'vuex';
import { authStore } from './authStore';
import { uiStore } from './uiStore';
import { timeStore } from './timeStore';
import { dataStore } from './dataStore';
import axiosInstance from '../api/axios';

vi.mock('../api/axios', () => {
  const mockAxios = {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
    patch: vi.fn(),
    defaults: {
      headers: {
        common: {}
      }
    },
    interceptors: {
      response: {
        use: vi.fn()
      }
    }
  };
  return {
    default: mockAxios,
    setupInterceptors: vi.fn(),
  };
});

const createVuexStore = () => createStore({
  modules: {
    auth: { ...authStore, state: authStore.state() },
    ui: { ...uiStore, state: uiStore.state() },
    time: { ...timeStore, state: timeStore.state() },
    data: { ...dataStore, state: dataStore.state() },
  }
});


describe('Vuex Store', () => {
  const setItemMock = vi.fn();
  const getItemMock = vi.fn();
  const removeItemMock = vi.fn();

  beforeEach(() => {
    vi.resetAllMocks();

    // Stub the global localStorage object with our mock functions.
    vi.stubGlobal('localStorage', {
      setItem: setItemMock,
      getItem: getItemMock,
      removeItem: removeItemMock,
    });
    axiosInstance.get.mockReset();
    axiosInstance.post.mockReset();
    axiosInstance.put.mockReset();
    axiosInstance.delete.mockReset();
    axiosInstance.patch.mockReset();
  });

  describe('authStore', () => {
    let store;
    beforeEach(() => { store = createVuexStore(); });

    it('should have correct initial state', () => {
      expect(store.state.auth.accessToken).toBe(null);
      expect(store.state.auth.user).toBe(null);
      expect(store.getters['auth/isAuthenticated']).toBe(false);
    });

    it('login action success', async () => {
      const tokens = { access: 'fake_access', refresh: 'fake_refresh' };
      const user = { id: 1, username: 'testuser' };
      const credentials = { username: 'test', password: 'password123' };

      axiosInstance.post.mockResolvedValueOnce({ data: tokens });
      axiosInstance.get.mockResolvedValueOnce({ data: user });

      await store.dispatch('auth/login', credentials);

      expect(axiosInstance.post).toHaveBeenCalledWith('/token/', credentials);
      expect(axiosInstance.get).toHaveBeenCalledWith('/users/me/');

      expect(store.state.auth.accessToken).toBe(tokens.access);
      expect(store.state.auth.user).toEqual(user);
      expect(store.getters['auth/isAuthenticated']).toBe(true);

      expect(axiosInstance.defaults.headers.common['Authorization'])
        .toBe(`Bearer ${tokens.access}`);
    });

    it('login action failure', async () => {
      const error = new Error('Invalid credentials');
      axiosInstance.post.mockRejectedValue(error);

      await expect(
        store.dispatch('auth/login', { user: 'test', password: 'bad' })
      ).rejects.toThrow(error);

      expect(store.state.auth.status).toBe('error');
      expect(store.getters['auth/isAuthenticated']).toBe(false);
      expect(setItemMock).not.toHaveBeenCalled();

      expect(removeItemMock).toHaveBeenCalledWith('authTokens');
    });

    it('logout action clears state and localStorage', async () => {
      store.commit('auth/SET_TOKENS', { access: 'abc', refresh: 'def' });

      await store.dispatch('auth/logout');

      expect(store.state.auth.accessToken).toBe(null);
      expect(store.state.auth.user).toBe(null);
      expect(removeItemMock).toHaveBeenCalledWith('authTokens');
      expect(axiosInstance.defaults.headers.common['Authorization']).toBeUndefined();
    });

    it('loadTokens action correctly loads from localStorage', () => {
      const tokens = { access: 'stored_access', refresh: 'stored_refresh' };
      getItemMock.mockReturnValue(JSON.stringify(tokens));

      store.dispatch('auth/loadTokens');

      expect(getItemMock).toHaveBeenCalledWith('authTokens');
      expect(store.state.auth.accessToken).toBe(tokens.access);
      expect(store.state.auth.refreshToken).toBe(tokens.refresh);
    });
  });

  describe('uiStore', () => {
    let store;

    beforeEach(() => {
      store = createVuexStore();
    });

    it('setDate action updates the current date', () => {
      const newDate = new Date('2025-09-20');
      store.dispatch('ui/setDate', { newDate });
      expect(store.state.ui.currentDate).toEqual(newDate);
    });

    it('setViewType action updates the view type', () => {
      store.dispatch('ui/setViewType', { type: 'week' });
      expect(store.state.ui.viewType).toBe('week');
    });

    it('getDateRange returns correct start/end for Day view', () => {
      const testDate = new Date('2025-09-18T12:00:00Z');
      store.state.ui.currentDate = testDate;
      store.state.ui.viewType = 'day';

      const range = store.getters['ui/getDateRange'];

      // Expected: 00:00:00 to 23:59:59 of the same day
      const expectedStart = new Date(testDate);
      expectedStart.setHours(0, 0, 0, 0);
      const expectedEnd = new Date(testDate);
      expectedEnd.setHours(23, 59, 59, 999);

      expect(range.startDate).toEqual(expectedStart);
      expect(range.endDate).toEqual(expectedEnd);
    });

    it('getDateRange returns correct start/end for Week view (Sunday start)', () => {
      // Week should be Sunday Sept 14 to Saturday Sept 20
      const testDate = new Date('2025-09-17T12:00:00');
      store.state.ui.currentDate = testDate;
      store.state.ui.viewType = 'week';

      const range = store.getters['ui/getDateRange'];

      const expectedStart = new Date('2025-09-14T12:00:00'); // Sunday
      expectedStart.setHours(0, 0, 0, 0);

      const expectedEnd = new Date('2025-09-20T12:00:00'); // Saturday
      expectedEnd.setHours(23, 59, 59, 999);

      expect(range.startDate.toDateString()).toBe(expectedStart.toDateString());
      expect(range.endDate.toDateString()).toBe(expectedEnd.toDateString());
    });

    it('getWeek returns 7 days starting from Sunday', () => {
      const testDate = new Date('2025-09-17T12:00:00');
      store.state.ui.currentDate = testDate;

      const week = store.getters['ui/getWeek'];

      expect(week).toHaveLength(7);
      // First day should be Sunday Sept 14
      expect(week[0].getDate()).toBe(14);
      expect(week[0].getDay()).toBe(0); // Sunday

      // Last day should be Saturday Sept 20
      expect(week[6].getDate()).toBe(20);
      expect(week[6].getDay()).toBe(6); // Saturday
    });
  });

  describe('timeStore', () => {
    let store;
    beforeEach(() => { store = createVuexStore(); });

    it('fetchProjects action success', async () => {
      const projects = [{ id: 1, title: 'Project A' }];
      axiosInstance.get.mockResolvedValue({ data: projects });

      await store.dispatch('time/fetchProjects');

      expect(axiosInstance.get).toHaveBeenCalledWith('/projects/');
      expect(store.state.time.projects[1]).toEqual(projects[0]);
      expect(store.state.time.status.projects).toBe('success');
    });

    it('fetchProjects action failure', async () => {
      axiosInstance.get.mockRejectedValue(new Error('Server Error'));

      await store.dispatch('time/fetchProjects');

      expect(store.state.time.status.projects).toBe('error');
      expect(store.state.time.projects).toEqual({});
    });

    it('ensureTimeEntry returns existing entry from state', async () => {
      const existingEntry = { id: 10, name: 'Test', project: 1 };
      store.commit('time/UPSERT_TIME_ENTRIES', [existingEntry]);

      const result = await store.dispatch('time/ensureTimeEntry', {
        name: 'Test',
        project: 1
      });

      expect(result).toEqual(existingEntry);
      expect(axiosInstance.post).not.toHaveBeenCalled();
    });

    it('ensureTimeEntry creates new entry if missing', async () => {
      const newEntry = { id: 11, name: 'New', project: 2 };
      axiosInstance.post.mockResolvedValue({ data: newEntry });

      const result = await store.dispatch('time/ensureTimeEntry', {
        name: 'New',
        project: 2
      });

      expect(axiosInstance.post).toHaveBeenCalledWith('/time-entries/', {
        name: 'New',
        project: 2
      });
      expect(result).toEqual(newEntry);
      expect(store.state.time.timeEntries[11]).toEqual(newEntry);
    });

    it('startNewLiveTrack creates entry and track', async () => {
      const timeEntry = { id: 50, name: 'Live Task', project: 5 };
      const track = { id: 100, time_entry: 50, start_time: '2025-01-01' };

      axiosInstance.post.mockResolvedValueOnce({ data: timeEntry });
      axiosInstance.post.mockResolvedValueOnce({ data: track });

      await store.dispatch('time/startNewLiveTrack', {
        name: 'Live Task',
        project: 5
      });

      expect(store.state.time.liveTrackId).toBe(100);
      expect(store.state.time.timeTracks[100]).toEqual(track);
    });
    it('createTrack action success', async () => {
      const timeEntry = { id: 1, name: 'Task', project: 1 };
      const newTrack = { id: 10, time_entry: 1, start_time: '2023-01-01', end_time: '2023-01-02' };
      axiosInstance.post.mockResolvedValueOnce({ data: timeEntry });
      axiosInstance.post.mockResolvedValueOnce({ data: newTrack });

      await store.dispatch('time/createTrack', {
        trackData: { name: 'Task', project: 1, start_time: '2023-01-01', end_time: '2023-01-02' }
      });

      expect(store.state.time.timeTracks[10]).toEqual(newTrack);
    });

    it('updateTrack action success', async () => {
      const initialEntry = { id: 1, name: 'Old Name', project: 1 };
      const initialTrack = {
        id: 1,
        time_entry: 1,
        start_time: '2023-01-01',
        end_time: '2023-01-02'
      };

      store.commit('time/UPSERT_TIME_ENTRIES', [initialEntry]);
      store.commit('time/UPSERT_TIME_TRACKS', [initialTrack]);

      const updatedTrackInput = {
        id: 1,
        name: 'New Name', // Name changed
        project: 1,
        start_time: '2023-01-02',
        end_time: '2023-01-05'
      };

      // Mock the POST call triggered by ensureTimeEntry for 'New Name'
      const newEntry = { id: 2, name: 'New Name', project: 1 };
      axiosInstance.post.mockResolvedValueOnce({ data: newEntry });

      // The backend should return the track linked to the NEW entry (id: 2)
      const updatedTrackResponse = {
        id: 1,
        time_entry: 2,
        start_time: '2023-01-02',
        end_time: '2023-01-05'
      };
      axiosInstance.put.mockResolvedValueOnce({ data: updatedTrackResponse });

      await store.dispatch('time/updateTrack', { trackData: updatedTrackInput });

      expect(axiosInstance.post).toHaveBeenCalledWith('/time-entries/', {
        name: 'New Name',
        project: 1
      });

      expect(axiosInstance.put).toHaveBeenCalledWith(
        `/time-tracks/${updatedTrackInput.id}/`,
        {
          id: 1,
          time_entry: 2,
          start_time: '2023-01-02',
          end_time: '2023-01-05'
        }
      );

      expect(store.state.time.timeTracks[1]).toEqual(updatedTrackResponse);
    });

    it('deleteTrack action success', async () => {
      const trackToDelete = { id: 5, name: 'To be deleted' };
      store.commit('time/UPSERT_TIME_TRACKS', [trackToDelete]);
      axiosInstance.delete.mockResolvedValue({ status: 204 });

      await store.dispatch('time/deleteTrack', { trackId: 5 });

      expect(axiosInstance.delete).toHaveBeenCalledWith(`/time-tracks/${trackToDelete.id}/`);
      expect(store.state.time.timeTracks[5]).toBeUndefined();
    });

    it('getLiveTrack getter returns hydrated track', () => {
      const startTime = new Date().toISOString();
      const track = { id: 99, start_time: startTime, time_entry: 10 };
      const entry = { id: 10, name: 'My Entry', project: 5 };
      const project = { id: 5, title: 'My Project', color: '#000' };

      store.commit('time/UPSERT_PROJECTS', [project]);
      store.commit('time/UPSERT_TIME_ENTRIES', [entry]);
      store.commit('time/UPSERT_TIME_TRACKS', [track]);
      store.commit('time/SET_LIVE_TRACK_ID', 99);

      const liveTrack = store.getters['time/getLiveTrack'];

      expect(liveTrack).not.toBeNull();
      expect(liveTrack.name).toBe('My Entry');
      expect(liveTrack.project_title).toBe('My Project');
    });

    it('fetchProjectDurations action success', async () => {
      const durations = { 1: 3600, 2: 7200 };
      axiosInstance.get.mockResolvedValue({ data: durations });

      await store.dispatch('time/fetchProjectDurations');

      expect(axiosInstance.get).toHaveBeenCalledWith('/projects/durations/');
      expect(store.state.time.projectDurations).toEqual(durations);
    });

    it('updateProject action success', async () => {
      const projectData = { id: 1, title: 'Updated Project', color: 'ff0000' };
      axiosInstance.put.mockResolvedValue({ data: projectData });

      const result = await store.dispatch('time/updateProject', projectData);

      expect(axiosInstance.put).toHaveBeenCalledWith(`/projects/${projectData.id}/`, projectData);
      expect(store.state.time.projects[1]).toEqual(projectData);
      expect(result).toEqual(projectData);
    });
  });

  describe('dataStore', () => {
    let store;
    beforeEach(() => { store = createVuexStore(); });

    it('importData action success and re-fetches data', async () => {
      const file = new File(['{}'], 'data.json', { type: 'application/json' });

      axiosInstance.post.mockResolvedValue({ status: 200 });
      // Mock the subsequent GET requests that refresh the app's data
      axiosInstance.get.mockResolvedValue({ data: [] });

      await store.dispatch('data/importData', { files: [file] });


      expect(axiosInstance.post).toHaveBeenCalledWith(
        '/data/import-data/',
        expect.any(FormData),
        expect.objectContaining({ headers: { 'Content-Type': 'multipart/form-data' } })
      );
      expect(store.state.data.importStatus).toBe('success');
      // A successful import should trigger a refresh of application data
      expect(axiosInstance.get).toHaveBeenCalledWith('/projects/');
    });

    it('importData action failure', async () => {
      const file = new File(['{}'], 'data.json');
      const error = { response: { data: { message: 'Invalid file' } } };
      axiosInstance.post.mockRejectedValue(error);

      await store.dispatch('data/importData', { files: [file] });

      expect(store.state.data.importStatus).toBe('error');
      expect(store.state.data.importError).toBe('Invalid file');
    });

    it('syncUpload action success: updates status to syncing, success, then idle', async () => {
      vi.useFakeTimers();
      axiosInstance.post.mockResolvedValue({ data: { status: 'synced' } });

      const actionPromise = store.dispatch('data/syncUpload');

      await actionPromise;

      expect(axiosInstance.post).toHaveBeenCalledWith('/sync/trigger_upload/');
      expect(store.state.data.syncStatus).toBe('success');

      vi.runAllTimers();

      expect(store.state.data.syncStatus).toBe('idle');

      vi.useRealTimers();
    });

    it('syncUpload action failure: sets error status and message', async () => {
      const errorMsg = 'Network Error';
      const error = { response: { data: { message: errorMsg } } };
      axiosInstance.post.mockRejectedValue(error);

      // Spy on console.error to suppress expected error logs in test output
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => { });

      await store.dispatch('data/syncUpload');

      expect(axiosInstance.post).toHaveBeenCalledWith('/sync/trigger_upload/');
      expect(store.state.data.syncStatus).toBe('error');
      expect(store.state.data.importError).toBe(errorMsg);

      consoleSpy.mockRestore();
    });

    it('checkStartupSync action: triggers data refresh when status is "downloaded"', async () => {
      axiosInstance.post.mockResolvedValueOnce({ data: { status: 'downloaded' } });

      axiosInstance.get.mockResolvedValue({ data: [] });

      await store.dispatch('data/checkStartupSync');

      expect(axiosInstance.post).toHaveBeenCalledWith('/sync/startup_check/');

      const requestedUrls = axiosInstance.get.mock.calls.map(call => call[0]);

      expect(requestedUrls).toContain('/projects/');
      expect(requestedUrls).toContain('/time-entries/');
      expect(requestedUrls.some(url => url.includes('/time-entries/recent/'))).toBe(true);
    });

    it('checkStartupSync action: does nothing when status is "up_to_date"', async () => {
      axiosInstance.post.mockResolvedValueOnce({ data: { status: 'up_to_date' } });

      await store.dispatch('data/checkStartupSync');

      expect(axiosInstance.post).toHaveBeenCalledWith('/sync/startup_check/');

      expect(axiosInstance.get).not.toHaveBeenCalled();
    });

    it('checkStartupSync action failure: handles error gracefully', async () => {
      const error = new Error('Server unavailable');
      axiosInstance.post.mockRejectedValue(error);
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => { });

      // Should not throw
      await store.dispatch('data/checkStartupSync');

      expect(axiosInstance.post).toHaveBeenCalledWith('/sync/startup_check/');
      expect(consoleSpy).toHaveBeenCalled();

      consoleSpy.mockRestore();
    });
  });
});
