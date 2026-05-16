# TODO & Known Issues

This document tracks planned features, known bugs, and technical debt for the Time Tracker application.

## 🐛 Bugs

- **Live Timer Project Change**: Changing the project of a live time track is currently disabled (`isTimerRunning`). Enabling this requires updating the logic to create a new `TimeEntry` (forking) rather than overwriting the previous one.
- **Live Timer Start Time Edit**: Changing the start time of a live track via the calendar widget is bugged; currently, it only works via the manual `HH:MM:SS` text input.
- **Calendar View Current Time Line**: The current time indicator fails to adapt its position correctly when switching between Day and Week views, or when navigating back from the Summary view.
- **Calendar View Gap**: There is a visual gap between the current time indicator line and the live track block. The timer updates in real-time, but the time block height doesn't react smoothly.
- **Calendar View Week Mode Layout**: The days' name layout in the header is bugged when in week mode.
- **DatePicker Month Boundaries**: The `DatePicker` doesn't display trailing/leading days from adjacent months, causing incomplete weeks to be shown at the beginning or end of a month.
- **Auth Sync Check**: The frontend might not be calling the `sync/startup_check` reliably immediately upon login.
- **Live Timer Suggestions**: Autocomplete recommendations in the Live Timer are not strictly ordered by the most recently tracked entries.
- **Time Blocks Reactivity**: Time block durations in `CalendarView` are not fully reactive and require a watch/interval to update smoothly in real-time without a full re-render.
- **Date Picker selected range**: In the `SummaryView` the calendar doesn't show a the selected range in highlighted colors, it only plots the start and end dates.
- **Suggestions Reactivity**: When creating a new time entry, the suggerstions dropdown does not include it until the whole page is refreshed.
- **Avg Daily Hours do not include future dates**: In the `SummaryView` the avg daily hours should only compute current and past days not the future.

## 🎨 UI/UX Improvements

- **DateRangeNavigator Project Filter**: Replace the simple text box for project filtering in the Summary view with a proper dropdown `ProjectSelector`.
- **Sync Status UI**: Add a toast/popup notification to display the status of data synchronization (uploading/downloading) to keep the user informed.
- **Double-Click to Now**: Allow double-clicking the time picker to auto-scroll and focus the `CalendarView` exactly on the current time.

## ✨ Features

- **Summary View Periods**: Expand the `SummaryView` to fully support Month, Year, and Custom period selections natively.
- **User Action Logging**: Implement comprehensive logging and tracking of user actions for better observability and debugging.
- **Locale Update**: Change all hardcoded `en-US` locales to `ja-JP` across the application.
- **Export Report**: Allow users to export the time range report (including graphs) to a PDF file.
- **Archive/Delete projects**: In the `ProjectView` allow users to archive or delete projects.

## 🛠 Refactoring & Tech Debt

- **CalendarView Tracks Getter**: Update `CalendarView` to utilize the `tracksForDate` Vuex getter for cleaner data retrieval.
- **CalendarToolbar Date Formatting**: Refactor `CalendarToolbar` to use the `uiStore` for date formatting instead of manual inline formatting.
- **Date Math Utility**: Extract all date manipulation and math logic into a centralized `utils/date.js` utility file.
- **Database Purge**: Implement a mechanism/command to periodically purge `TimeEntry` records that have no associated `TimeTrack`s.
- **Sync Optimization (Metadata vs Data)**: Optimize `rclone` sync by separating `meta` and `data` into different folders. Download `meta` first to evaluate if the full `data` folder needs to be downloaded.
- **Encryption Caching**: Implement caching for the encryption process to only re-encrypt modified data, optimizing the sync upload (as older time entries rarely change).
- **Remove Duplicated Code**: Many date manipulation logic is repeated across files.

## 🧪 Testing

- **Shortcut Functionality**: Update and expand frontend tests to cover the new date range shortcut functionality and recent component changes.
- **Mixed Week start and locale**: Some tests like `SummaryView` ones expect week to start on Monday while the whole logic is based on Sunday start.
