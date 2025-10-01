# RecoRules Quick Start Guide

## Installation

```bash
cd /Users/dorsk/Documents/Dev/M1/recorules
make setup
```

## First Run

```bash
make run
```

You'll be prompted to enter your Recoru credentials:
- **Contract ID**: Found in Recoru settings
- **Auth ID**: Your login ID
- **Password**: Your Recoru password

These are stored securely in `~/.config/recorules/config.ini`

## Daily Workflow

### 1. Check Your Balance

Launch the app:
```bash
make run
```

The stats panel at the top shows:
- **Working Days**: Total working days in current month
- **Required**: Total hours required (8h × working days)
- **Balance**: Your current overtime/undertime balance
- **WFH Stats**: Used vs quota, with warnings if over
- **Office Stats**: Worked vs required in-office hours

### 2. Review Calendar

The table shows each day with:
- **Date**: Day of month and day of week
- **Office**: Minutes worked in office
- **Remote**: Minutes worked from home
- **Expected**: Required minutes for that day (480 for working days)
- **Balance**: Running balance throughout the month
- **Note**: Any notes or special statuses

Color coding:
- 🟡 **Yellow** = Today
- ⚪ **Dim** = Future (not yet worked)
- 🔵 **Blue** = Weekend
- 🔴 **Red** = Public holiday
- 🔵 **Cyan** = Paid leave

### 3. Plan Future Days

1. Use **arrow keys** ↑↓ to select a future date
2. Press **`p`** to open the planning dialog
3. Enter your plan:
   - Office hours (e.g., `8` for 8 hours)
   - WFH hours (e.g., `8` for full WFH day)
   - Note (optional, e.g., "Client meeting")
   - Mark as paid leave if taking PTO
4. Press **Save** to save or **Delete** to remove a plan

### 4. Refresh Data

Press **`r`** to refresh data from Recoru at any time.

### 5. Get Help

Press **`?`** to see keyboard shortcuts and workplace rules.

### 6. Quit

Press **`q`** to quit.

## Common Scenarios

### Scenario 1: Check if I can take a WFH day
1. Look at "WFH Left" in stats panel
2. If positive, you have WFH quota remaining
3. Select future date and press `p`
4. Enter `8` for WFH hours
5. Save and see updated stats

### Scenario 2: Plan a vacation day
1. Select the date
2. Press `p`
3. Toggle "Paid leave" to "Yes"
4. Save
5. The day will count towards required hours but won't show work time

### Scenario 3: Check month-end projection
1. Plan all remaining days in the month
2. Stats panel shows projected end-of-month balance
3. Adjust plans if needed to meet quotas

### Scenario 4: Mixed office/WFH day
1. Select future date
2. Press `p`
3. Enter `4` for office hours
4. Enter `4` for WFH hours
5. Save - both will count towards your totals

## Understanding Your Stats

### WFH Quota Rules
- You get **1 hour of WFH per working day**
- Example: 20 working days = 20 hours WFH quota
- If you work 30 hours WFH, you're 10 hours over
- **Over-quota WFH hours are uncompensated**

### Office Hours Rules
- Required office hours = Total required - WFH quota
- Example: 160h required - 20h WFH quota = **140h office required**
- You **must** meet this office requirement
- WFH over-quota doesn't reduce office requirement

### Balance
- **Positive balance** = You've worked extra hours
- **Negative balance** = You're behind on hours
- Aim for 0 or slightly positive by month-end

## Tips

1. **Plan ahead**: Enter your WFH days at the start of the month
2. **Check daily**: Quick `make run` to see your balance
3. **Watch the stats**: Red warnings mean you need to adjust
4. **Use notes**: Add context to your planned days
5. **Refresh after changes**: Press `r` after clocking in/out on Recoru

## Troubleshooting

### "No configuration found"
Run: `rye run python -m recorules config`

### "Failed to fetch data from Recoru"
- Check your internet connection
- Verify credentials: `rye run python -m recorules config`
- Make sure you can log into Recoru website

### Stats seem wrong
- Press `r` to refresh from Recoru
- Check if public holidays are correctly detected
- Verify your planned days in the calendar

### Can't plan a date
- Make sure the date is in the future (can't plan past)
- Use arrow keys to select the date first
- The date should be highlighted before pressing `p`

## Advanced

### Reconfigure
```bash
rye run python -m recorules config
```

### Run tests
```bash
make test
```

### Check code quality
```bash
make lint
```

### View planning database
```bash
sqlite3 ~/.config/recorules/planning.db
SELECT * FROM planned_days;
.quit
```

## Excel Migration

Your old Excel workflow:
1. Manually copy data from Recoru ❌
2. Update formulas ❌
3. Calculate balance by hand ❌
4. Track WFH quota separately ❌

New RecoRules workflow:
1. `make run` ✅
2. Everything auto-calculates ✅
3. Plan future with `p` ✅
4. Get instant feedback ✅