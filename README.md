# Windows 11 Planner Application

A broad, all-in-one desktop planner for Windows-style workflows, built with Python + Tkinter.

## Features

- **Dashboard** with real-time metrics (total tasks, due today, overdue, completed)
- **Task Manager** with:
  - title, due date, priority, status, category, estimate hours
  - filter by status
  - mark done / delete
- **Calendar** month view with task/event markers
- **Events** with date and time scheduling
- **Notes** panel with save + export
- **Goals Tracker** with target dates and progress %
- **Focus (Pomodoro) Timer** for deep work sessions
- **Auto-save** to JSON
- **CSV Export** for tasks

## Requirements

- Python 3.10+
- Tkinter (typically included with standard Python installers)

## Run

```bash
python3 planner_app.py
```

## Data storage

The app stores data in:

- `planner_data.json`

This file is created automatically in the project root when data is saved.

## Date format

Use `YYYY-MM-DD` for all date entries.
