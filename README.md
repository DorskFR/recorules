# RecoRules

A TUI planning tool for Recoru time tracking, adapted to your workplace rules.

## Features

- 📅 Automatic Japanese holiday calendar
- 📊 Real-time balance tracking
- 🏢 Office/WFH quota management
- 📝 Future planning with live projections
- 🎨 Clean, elegant terminal UI

## Installation

```bash
make setup
```

## Configuration

```bash
make run
# Or: rye run python -m recorules
```

On first run, you'll be prompted to configure your Recoru credentials:
- Contract ID
- Auth ID
- Password

## Usage

```bash
make run
```

## Workplace Rules

- 8 hours required per working day
- 1 hour WFH quota per working day
- Mandatory 1 hour break for 6+ hours worked
- Office hours = Total hours - WFH quota

## Development

```bash
make setup     # Install dependencies
make test      # Run tests
make lint      # Check code quality
make lint/fix  # Auto-fix linting issues
make clean     # Clean cache files
```