# RecoRules Implementation Summary

## Overview

RecoRules is a TUI (Terminal User Interface) planning tool for Recoru time tracking, specifically designed to handle your workplace rules and make monthly planning easier.

## Architecture

### Core Components

1. **recorules/recoru/** - Recoru API integration (adapted from recolul)
   - `recoru_session.py` - Authentication and data fetching
   - `attendance_chart.py` - Data structures for parsing HTML

2. **recorules/calculator.py** - Business logic for workplace rules
   - Calculates monthly statistics
   - Applies break rules (1h break for 6+ hours worked)
   - Tracks office vs WFH quotas
   - Merges actual and planned data

3. **recorules/database.py** - SQLite persistence for planned future days
   - CRUD operations for planned days
   - Month-based queries

4. **recorules/holidays.py** - Japanese holiday calendar
   - Uses `jpholiday` library
   - Determines working vs non-working days

5. **recorules/widgets/** - Textual TUI components
   - `stats_panel.py` - Monthly statistics display
   - `calendar_table.py` - Daily calendar table
   - `plan_dialog.py` - Dialog for planning future days

6. **recorules/app.py** - Main application
   - Integrates all components
   - Handles user interactions
   - Manages data refresh

## Workplace Rules Implementation

The calculator implements these rules:

1. **8 hours required per working day**
   - Automatically counts working days excluding weekends and Japanese holidays
   - Total required = working_days × 8 hours

2. **1 hour WFH quota per working day**
   - WFH quota = working_days × 1 hour
   - Tracks WFH over-quota in red

3. **Mandatory in-office hours**
   - Office required = total_required - WFH_quota
   - Warns if office hours deficit exists

4. **Automatic 1h break for 6+ hours worked**
   - Applied automatically in duration calculations
   - Consistent with Recoru's behavior

## Data Flow

```
Recoru API
    ↓
AttendanceChart (HTML parsing)
    ↓
DayRecord objects (parsed data)
    ↓
merge with PlannedDay (from SQLite)
    ↓
MonthStats calculation
    ↓
Display in TUI
```

## Features Implemented

### ✅ Phase 1: Core TUI + Data Fetch
- Textual app with header/footer
- Basic table display
- Recoru authentication
- Data fetching
- Japanese holiday detection

### ✅ Phase 2: Business Logic
- Workplace rules calculator
- Stats panel with quotas
- Running balance column
- Color-coded table rows:
  - Yellow = Today
  - Dim = Future
  - Blue = Weekend
  - Red = Holiday
  - Cyan = Paid leave

### ✅ Phase 3: Planning Features
- SQLite database
- Edit mode for future dates (press `p`)
- Live recalculation
- Validation warnings

### ✅ Phase 4: Polish
- Keyboard shortcuts (q/r/p/?)
- Help screen
- 22 comprehensive tests (all passing)
- Ruff/mypy linting

## Usage

### First Run
```bash
make setup
make run
# Follow prompts to configure Recoru credentials
```

### Daily Use
```bash
make run
```

### Keyboard Shortcuts
- `q` - Quit
- `r` - Refresh data from Recoru
- `p` - Plan future day (select date first with arrow keys)
- `?` - Help

### Planning Future Days
1. Use arrow keys to select a future date
2. Press `p` to open planning dialog
3. Enter office hours, WFH hours, notes
4. Mark as paid leave if needed
5. Save or Delete

## Testing

```bash
make test       # Run all tests
make lint       # Check code quality
make lint/fix   # Auto-fix issues
make clean      # Clean cache files
```

## Configuration

Config stored at: `~/.config/recorules/config.ini`
Database stored at: `~/.config/recorules/planning.db`

To reconfigure:
```bash
rye run python -m recorules config
```

## Comparison with Excel Sheet

### Before (Excel)
- Manual data entry
- Static formulas
- No auto-sync with Recoru
- No holiday awareness
- Manual balance tracking

### Now (RecoRules)
- Auto-fetch from Recoru
- Dynamic calculations
- Japanese holiday calendar
- Real-time projections
- Interactive planning
- Color-coded display
- Persistent future planning

## Example Month View

```
┌─ RecoRules - 2025/09 ────────────────────────────────────┐
│ Working Days: 20  │  Required: 160h  │  Balance: +29.7h  │
│ WFH Used: 49.7h   │  WFH Quota: 20h  │  WFH Over: 29.7h⚠│
│ Office: 132h      │  Required: 140h  │  Surplus: 8h ✓    │
├───────────────────────────────────────────────────────────┤
│ Date      Office  Remote  Expected  Balance  Note         │
│ 09/01(Mon) 10:07  --     08:00     +02:07                 │
│ 09/02(Tue) 08:08  02:28  08:00     +04:43                 │
│ 09/03(Wed) --     11:20  08:00     +08:03   WFH          │
│ ...                                                        │
└───────────────────────────────────────────────────────────┘
```

## Future Enhancements (Not Implemented Yet)

- Month navigation (previous/next month)
- CSV export
- Multi-month view
- Charts/graphs
- Desktop notifications
- Mobile responsive design
- Multiple workplace locations

## Dependencies

Core:
- textual - TUI framework
- requests - HTTP client
- beautifulsoup4 - HTML parsing
- jpholiday - Japanese holidays

Dev:
- pytest - Testing
- ruff - Linting/formatting
- mypy - Type checking
- vulture - Dead code detection

## Credits

Based on the `recolul` project by your colleague for core Recoru integration logic.