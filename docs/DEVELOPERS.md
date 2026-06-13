# Developer Guide

This guide outlines the architecture, main components, and business rules of the Time Tracker application. It is designed to help developers understand the codebase, customize features, and contribute effectively.

## 1. Architecture Overview

The application follows a decoupled client-server architecture:

- **Frontend**: A Single Page Application (SPA) built with Vue 3 (Composition API) and styled with Tailwind CSS. State is managed centrally via Vuex. Prefer Javascript over Typescript.
- **Backend**: A JSON API built with Django REST Framework (DRF). Uses SQLite by default for lightweight, local-first deployment.
- **Data Sync**: A local-first synchronization mechanism (`SyncManager`) encrypts user data and syncs it to a local folder (e.g., a mounted cloud drive) to allow cross-machine usage without relying on a centralized cloud database. It uses `rclone` for allowing different storage providers.

## 2. Core Business Rules

To ensure data integrity and a consistent user experience, the application enforces the following rules:

- **Single Running Timer Invariant**: A user can only have one active `TimeTrack` (where `end_time` is null) at any given time. However, users can manually create or edit completed past tracks while a live timer is running.
- **Time Interval Validity**: For completed tracks, `end_time` must be chronologically after `start_time`. This is enforced upon manual creation and updates.
- **Duration Calculation**: The duration of a time entry is calculated dynamically. For completed tracks, it is `end_time - start_time`. For live tracks, it is `current_time - start_time`.
- **Unique Entities**: `Project` titles must be unique per user. `TimeEntry` names are unique per project. If a user tracks a new entry using an existing name/project combination, the system reuses the existing database object instead of creating a duplicate.
- **Week Starts at Sunday**: The weekly calendar and all week-based aggregations must start on Sunday, ignoring the user's local locale settings.
- **Automatic Data Synchronization**: The app syncs encrypted data to a local folder (designed to be mapped to a cloud drive via Rclone) using Fernet encryption. To optimize read/write operations, it first reads a `meta.json` file containing the `machine_id` and timestamp. It skips downloading and merging local data if the last update was made by the exact same machine.
- **Timezone and Date Handling**: All timestamps are stored in **UTC** in the backend. API communication uses **ISO 8601** strings. Aggregation endpoints (like `/api/summary/`) require the user's **IANA timezone string** to correctly truncate UTC timestamps to local day boundaries. The frontend is responsible for converting UTC to local time for display and generating local date keys (e.g., `YYYY-MM-DD`).
- **Multi-day Tracks**: Time tracks that span across midnight (e.g., 22:00 to 06:00) are stored as a single continuous record in the backend. When filtering by date, the backend includes any overlapping entries. The frontend dynamically splits these tracks into daily segments for accurate rendering on the calendar and statistical reporting.
- **Live Time Tracks Editability**: Live tracks can be edited by the user without stopping the timer. Because the `end_time` is null, any duration or date changes applied to a live track (via the modal, calendar, or live timer input) modify its `start_time` to reflect the new duration relative to the current time.
- **Updating Time Entry**: If a time entry is updated by using the `EditEntryModal` clicking on a time track, only time track is updated, not the time entry. That is if the project is changed then the time track uses the newly generated time entry, while all the previous time tracks of the old time entry are kept without changes.
- **Synchronization Logic**: Instead of the naive delete-then-insert original logic the app uses the Last-Write-Wins such that it handles several machines used at the same time. The cloud storage always uploads the projects and time entries, and only the time tracks of the modified year. Local records are only updated if they exist in the remote with newer `updated_at`, otherwise the remote data is merged into the local database.
- **Soft Deleting**: To avoid conflicts with several machines, records are not removed from the database instead the `deleted_at` timestamp is updated to a non null value.
- **Data Import**: The backend treats all incoming data (CSV from toggl track or JSON from the app itself) as a "Delta", it uses LWW merge logic such that the data is merged instead of deleting and creating all.

## 3. Backend Subsystem

The backend is a monolithic Django app (`api`) exposing RESTful endpoints.

### Data Model

All dataset entities expect users have an `UUIDField`, `updated_at` and `deleted_at` fields.

- **`User`**: Standard Django auth user.
- **`Project`**: Categorizes time entries (includes `title`, `color`). The `color` is the hexadecimal representation without the `#` symbol which must be included in the frontend.
- **`TimeEntry`**: A specific task/description within a project.
- **`TimeTrack`**: A specific time block (`start_time`, `end_time`) linked to a `TimeEntry` and `User`.
- **`SyncState`**: Tracks when the database was synchronized with the cloud storage. It stores only the user and the synchronization time.

### API Endpoints

- **CRUD Operations**: Handled via DRF ViewSets (`/api/projects/`, `/api/time-entries/`, `/api/time-tracks/`).
- **Summary API (`/api/summary/`)**: Aggregates time tracks by date, project, and entry for reporting. It handles timezone-aware truncation and correctly splits multi-day tracks.
- **Data Portability (`/api/data/`)**:
  - `GET /export/`: Serializes all user data into a JSON file.
  - `POST /import-data/`: **Merges** the user's existing data with the uploaded JSON/CSV file inside an atomic transaction.
- **Synchronization (`/api/sync/`)**:
  - `POST /trigger_upload/`: Encrypts the user's data using Fernet and writes it to the local sync directory.
  - `POST /startup_check/`: Checks `meta.json` in the sync directory. If the `machine_id` differs, it decrypts and imports the newer data.

## 4. Frontend Subsystem

The Vue 3 frontend is organized into Views, Components, and Vuex Stores.

### State Management (Vuex)

- **`authStore`**: Manages JWT tokens, login/logout logic, and user sessions.
- **`timeStore`**: The central repository for business data (`projects`, `timeEntries`, `timeTracks`). Handles CRUD API interactions, live timer state, and summary data fetching.
- **`uiStore`**: Manages global UI state, including the current date, view type (day/week), zoom level, and date range calculations (including shortcuts like "This Week", "Last Month").
- **`dataStore`**: Manages import/export processes and sync statuses.

### Key Views & Components

- **`TimerView` (`/timer`)**: The main dashboard.
  - **`LiveTimer`**: Controls the active running track. Includes an autocomplete input for recent entries and a project selector.
  - **`CalendarToolbar`**: Controls date navigation, view switching (Day/Week), and zoom levels.
  - **`CalendarView`**: Renders time tracks on a time grid. Supports drag-to-create, drag-to-move, and drag-to-resize. It handles multi-day tracks by splitting them into segments for rendering.
  - **`EditEntryModal`**: Form for editing or manually creating tracks.
- **`SummaryView` (`/summary`)**: The reporting dashboard.
  - **`DateRangeNavigator`**: Selects reporting periods and filters by text/project.
  - **Dynamic Binning**: The view dynamically adjusts chart bins (days, weeks, months) based on the selected date range.
  - **`DurationBarChart` & `ProjectPieChart`**: Visualizes aggregated data using Chart.js.
  - **`ProjectBreakdownList`**: Hierarchical view of time spent per project and task.
- **`ProjectsView` (`/projects`)**: Table view for managing projects and viewing total time spent per project.
- **`SettingsView` (`/settings`)**: Interface for manual JSON data import/export.

### Error Handling & Interceptors

All API communication is handled via an Axios instance configured in `src/api/axios.js`.

- **Token Refresh**: An interceptor automatically catches `401 Unauthorized` responses, attempts to refresh the JWT token, and retries the original request with exponential backoff.
- **Global Errors**: Non-recoverable errors (e.g., `500 Server Error`) are dispatched to the `uiStore` to display a global toast notification.

## 5. Data Flow Example: Live Tracking

To understand how the frontend and backend interact, here is the flow for starting a live timer:

1. The user types a description in the `LiveTimer` component and clicks "Start".
2. The frontend dispatches the `time/startNewLiveTrack` Vuex action.
3. Vuex calls `ensureTimeEntry` to find an existing `TimeEntry` in the local state. If it doesn't exist, it POSTs to `/api/time-entries/` to create it.
4. Vuex POSTs to `/api/time-tracks/` with the `time_entry` ID and `end_time: null`.
5. The backend creates the track, enforces the "Single Running Timer" rule, and returns the object.
6. Vuex updates `liveTrackId`.
7. The `CalendarView` reactively renders the growing time block using a local `setInterval` to update the current time and calculate the block's height dynamically.

## 6. Testing Strategy

- **Backend**: Uses `pytest` and `pytest-django`. Tests focus heavily on API integration (`APITestCase`), ensuring endpoints enforce business rules, validate data correctly, and isolate user data.
- **Frontend**: Uses `vitest` and `Vue Test Utils`. Tests focus on component rendering, user interactions (e.g., verifying that dragging emits the correct events with snapped times), and Vuex store logic (mocking Axios requests).
