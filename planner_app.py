#!/usr/bin/env python3
"""
Windows 11 Planner Application
A broad, all-in-one personal planning desktop app built with Tkinter.
"""

from __future__ import annotations

import calendar as calmod
import csv
import json
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, date, timedelta
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

APP_TITLE = "Windows 11 Planner"
DATA_FILE = Path("planner_data.json")
DATE_FMT = "%Y-%m-%d"


@dataclass
class Task:
    id: str
    title: str
    due: str
    priority: str
    status: str
    category: str
    estimate_hours: float


@dataclass
class Goal:
    id: str
    title: str
    target_date: str
    progress: int


@dataclass
class Event:
    id: str
    title: str
    event_date: str
    time: str


class PlannerData:
    def __init__(self) -> None:
        self.tasks: list[Task] = []
        self.notes: str = ""
        self.goals: list[Goal] = []
        self.events: list[Event] = []

    def load(self, path: Path = DATA_FILE) -> None:
        if not path.exists():
            return
        with path.open("r", encoding="utf-8") as fh:
            raw = json.load(fh)
        self.tasks = [Task(**item) for item in raw.get("tasks", [])]
        self.notes = raw.get("notes", "")
        self.goals = [Goal(**item) for item in raw.get("goals", [])]
        self.events = [Event(**item) for item in raw.get("events", [])]

    def save(self, path: Path = DATA_FILE) -> None:
        payload = {
            "tasks": [asdict(t) for t in self.tasks],
            "notes": self.notes,
            "goals": [asdict(g) for g in self.goals],
            "events": [asdict(e) for e in self.events],
            "saved_at": datetime.now().isoformat(timespec="seconds"),
        }
        with path.open("w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)


class PlannerApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1360x860")
        self.minsize(1200, 760)

        self.data = PlannerData()
        self.data.load()

        self.current_calendar = date.today().replace(day=1)
        self.pomodoro_seconds_left = 25 * 60
        self.pomodoro_running = False
        self.pomodoro_job: str | None = None

        self._setup_style()
        self._build_ui()
        self.refresh_all_views()

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def _setup_style(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        self.configure(bg="#F6F8FC")
        default_font = ("Segoe UI", 10)

        self.option_add("*Font", default_font)
        style.configure("TNotebook", background="#F6F8FC", borderwidth=0)
        style.configure("TNotebook.Tab", padding=(12, 8), font=("Segoe UI", 10, "bold"))
        style.map("TNotebook.Tab", background=[("selected", "#FFFFFF")])

        style.configure("Card.TFrame", background="#FFFFFF", relief="flat")
        style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"), padding=8)

    def _build_ui(self) -> None:
        header = ttk.Frame(self, padding=16)
        header.pack(fill="x")
        ttk.Label(header, text=APP_TITLE, font=("Segoe UI", 20, "bold")).pack(side="left")
        ttk.Button(header, text="Save Now", command=self.save_data).pack(side="right", padx=4)
        ttk.Button(header, text="Export Tasks CSV", command=self.export_tasks_csv).pack(side="right", padx=4)

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        self.dashboard_tab = ttk.Frame(notebook, style="Card.TFrame", padding=16)
        self.tasks_tab = ttk.Frame(notebook, style="Card.TFrame", padding=16)
        self.calendar_tab = ttk.Frame(notebook, style="Card.TFrame", padding=16)
        self.notes_tab = ttk.Frame(notebook, style="Card.TFrame", padding=16)
        self.goals_tab = ttk.Frame(notebook, style="Card.TFrame", padding=16)
        self.focus_tab = ttk.Frame(notebook, style="Card.TFrame", padding=16)

        notebook.add(self.dashboard_tab, text="Dashboard")
        notebook.add(self.tasks_tab, text="Tasks")
        notebook.add(self.calendar_tab, text="Calendar")
        notebook.add(self.notes_tab, text="Notes")
        notebook.add(self.goals_tab, text="Goals")
        notebook.add(self.focus_tab, text="Focus")

        self._build_dashboard()
        self._build_tasks()
        self._build_calendar()
        self._build_notes()
        self._build_goals()
        self._build_focus()

    def _build_dashboard(self) -> None:
        row = ttk.Frame(self.dashboard_tab)
        row.pack(fill="x")

        self.summary_labels: dict[str, ttk.Label] = {}
        for key, title in [
            ("total", "Total Tasks"),
            ("today", "Due Today"),
            ("overdue", "Overdue"),
            ("done", "Completed"),
        ]:
            card = ttk.Frame(row, style="Card.TFrame", padding=16)
            card.pack(side="left", fill="both", expand=True, padx=8, pady=8)
            ttk.Label(card, text=title, foreground="#666").pack(anchor="w")
            value = ttk.Label(card, text="0", font=("Segoe UI", 24, "bold"))
            value.pack(anchor="w", pady=(4, 0))
            self.summary_labels[key] = value

        ttk.Label(self.dashboard_tab, text="Next 7 Days", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(16, 4))
        self.upcoming_list = tk.Listbox(self.dashboard_tab, height=14, borderwidth=0, highlightthickness=1)
        self.upcoming_list.pack(fill="both", expand=True)

    def _build_tasks(self) -> None:
        form = ttk.Frame(self.tasks_tab)
        form.pack(fill="x", pady=(0, 10))

        self.task_title = tk.StringVar()
        self.task_due = tk.StringVar(value=date.today().strftime(DATE_FMT))
        self.task_priority = tk.StringVar(value="Medium")
        self.task_status = tk.StringVar(value="Todo")
        self.task_category = tk.StringVar(value="General")
        self.task_estimate = tk.StringVar(value="1")
        self.task_filter = tk.StringVar(value="All")

        fields = [
            ("Title", ttk.Entry(form, textvariable=self.task_title, width=28)),
            ("Due", ttk.Entry(form, textvariable=self.task_due, width=12)),
            ("Priority", ttk.Combobox(form, textvariable=self.task_priority, values=["Low", "Medium", "High"], width=10, state="readonly")),
            ("Status", ttk.Combobox(form, textvariable=self.task_status, values=["Todo", "In Progress", "Done"], width=12, state="readonly")),
            ("Category", ttk.Entry(form, textvariable=self.task_category, width=16)),
            ("Est. Hours", ttk.Entry(form, textvariable=self.task_estimate, width=10)),
        ]

        for idx, (label, widget) in enumerate(fields):
            ttk.Label(form, text=label).grid(row=0, column=idx * 2, padx=4, sticky="w")
            widget.grid(row=0, column=idx * 2 + 1, padx=(0, 10))

        ttk.Button(form, text="Add Task", command=self.add_task).grid(row=0, column=len(fields) * 2, padx=4)
        ttk.Button(form, text="Mark Done", command=self.mark_selected_task_done).grid(row=0, column=len(fields) * 2 + 1, padx=4)
        ttk.Button(form, text="Delete Task", command=self.delete_selected_task).grid(row=0, column=len(fields) * 2 + 2, padx=4)

        filter_row = ttk.Frame(self.tasks_tab)
        filter_row.pack(fill="x", pady=(0, 8))
        ttk.Label(filter_row, text="View:").pack(side="left")
        cmb = ttk.Combobox(filter_row, textvariable=self.task_filter, values=["All", "Todo", "In Progress", "Done"], state="readonly", width=16)
        cmb.pack(side="left", padx=6)
        cmb.bind("<<ComboboxSelected>>", lambda _: self.refresh_task_tree())

        columns = ("title", "due", "priority", "status", "category", "estimate")
        self.task_tree = ttk.Treeview(self.tasks_tab, columns=columns, show="headings", height=18)
        self.task_tree.pack(fill="both", expand=True)
        headings = {
            "title": "Title",
            "due": "Due",
            "priority": "Priority",
            "status": "Status",
            "category": "Category",
            "estimate": "Est. Hours",
        }
        for col, txt in headings.items():
            self.task_tree.heading(col, text=txt)
            self.task_tree.column(col, anchor="w", width=140 if col != "title" else 300)

    def _build_calendar(self) -> None:
        top = ttk.Frame(self.calendar_tab)
        top.pack(fill="x")
        ttk.Button(top, text="<", command=lambda: self.shift_month(-1)).pack(side="left")
        ttk.Button(top, text=">", command=lambda: self.shift_month(1)).pack(side="left", padx=4)
        self.month_label = ttk.Label(top, text="", font=("Segoe UI", 13, "bold"))
        self.month_label.pack(side="left", padx=8)

        event_frame = ttk.Frame(top)
        event_frame.pack(side="right")
        self.event_title = tk.StringVar()
        self.event_date = tk.StringVar(value=date.today().strftime(DATE_FMT))
        self.event_time = tk.StringVar(value="09:00")
        ttk.Entry(event_frame, textvariable=self.event_title, width=24).pack(side="left", padx=2)
        ttk.Entry(event_frame, textvariable=self.event_date, width=12).pack(side="left", padx=2)
        ttk.Entry(event_frame, textvariable=self.event_time, width=8).pack(side="left", padx=2)
        ttk.Button(event_frame, text="Add Event", command=self.add_event).pack(side="left", padx=2)

        self.calendar_text = tk.Text(self.calendar_tab, height=18, wrap="none", borderwidth=0, highlightthickness=1)
        self.calendar_text.pack(fill="both", expand=True, pady=8)

        ttk.Label(self.calendar_tab, text="Upcoming Events", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        self.event_list = tk.Listbox(self.calendar_tab, height=8)
        self.event_list.pack(fill="x")

    def _build_notes(self) -> None:
        bar = ttk.Frame(self.notes_tab)
        bar.pack(fill="x", pady=(0, 8))
        ttk.Button(bar, text="Save Notes", command=self.save_notes).pack(side="left")
        ttk.Button(bar, text="Export Notes", command=self.export_notes).pack(side="left", padx=6)

        self.notes_text = tk.Text(self.notes_tab, wrap="word")
        self.notes_text.pack(fill="both", expand=True)

    def _build_goals(self) -> None:
        row = ttk.Frame(self.goals_tab)
        row.pack(fill="x", pady=(0, 8))

        self.goal_title = tk.StringVar()
        self.goal_target = tk.StringVar(value=(date.today() + timedelta(days=90)).strftime(DATE_FMT))
        self.goal_progress = tk.StringVar(value="0")

        ttk.Entry(row, textvariable=self.goal_title, width=30).pack(side="left", padx=3)
        ttk.Entry(row, textvariable=self.goal_target, width=12).pack(side="left", padx=3)
        ttk.Entry(row, textvariable=self.goal_progress, width=6).pack(side="left", padx=3)
        ttk.Button(row, text="Add Goal", command=self.add_goal).pack(side="left", padx=3)
        ttk.Button(row, text="Update Selected", command=self.update_goal_progress).pack(side="left", padx=3)
        ttk.Button(row, text="Delete Selected", command=self.delete_goal).pack(side="left", padx=3)

        self.goal_tree = ttk.Treeview(self.goals_tab, columns=("title", "target", "progress"), show="headings", height=18)
        self.goal_tree.pack(fill="both", expand=True)
        self.goal_tree.heading("title", text="Goal")
        self.goal_tree.heading("target", text="Target Date")
        self.goal_tree.heading("progress", text="Progress %")
        self.goal_tree.column("title", width=400)
        self.goal_tree.column("target", width=160)
        self.goal_tree.column("progress", width=120)

    def _build_focus(self) -> None:
        pane = ttk.Frame(self.focus_tab)
        pane.pack(fill="both", expand=True)

        ttk.Label(pane, text="Pomodoro Focus Timer", font=("Segoe UI", 14, "bold")).pack(anchor="w", pady=(0, 8))
        self.timer_label = ttk.Label(pane, text="25:00", font=("Segoe UI", 36, "bold"))
        self.timer_label.pack(anchor="center", pady=8)

        controls = ttk.Frame(pane)
        controls.pack(anchor="center")
        ttk.Button(controls, text="Start", command=self.start_pomodoro).pack(side="left", padx=4)
        ttk.Button(controls, text="Pause", command=self.pause_pomodoro).pack(side="left", padx=4)
        ttk.Button(controls, text="Reset", command=self.reset_pomodoro).pack(side="left", padx=4)

        ttk.Label(pane, text="Use this tab for deep work sessions (25min focus + 5min break).", foreground="#555").pack(anchor="center", pady=8)

    def add_task(self) -> None:
        title = self.task_title.get().strip()
        if not title:
            messagebox.showwarning("Missing title", "Task title is required.")
            return
        try:
            datetime.strptime(self.task_due.get().strip(), DATE_FMT)
            estimate = float(self.task_estimate.get().strip())
        except ValueError:
            messagebox.showerror("Invalid data", "Due must be YYYY-MM-DD and estimate must be numeric.")
            return

        self.data.tasks.append(
            Task(
                id=str(uuid.uuid4()),
                title=title,
                due=self.task_due.get().strip(),
                priority=self.task_priority.get().strip(),
                status=self.task_status.get().strip(),
                category=self.task_category.get().strip() or "General",
                estimate_hours=estimate,
            )
        )
        self.task_title.set("")
        self.task_estimate.set("1")
        self.refresh_all_views()
        self.save_data()

    def mark_selected_task_done(self) -> None:
        sel = self.task_tree.selection()
        if not sel:
            return
        task_id = sel[0]
        for t in self.data.tasks:
            if t.id == task_id:
                t.status = "Done"
                break
        self.refresh_all_views()
        self.save_data()

    def delete_selected_task(self) -> None:
        sel = self.task_tree.selection()
        if not sel:
            return
        task_id = sel[0]
        self.data.tasks = [t for t in self.data.tasks if t.id != task_id]
        self.refresh_all_views()
        self.save_data()

    def add_event(self) -> None:
        title = self.event_title.get().strip()
        if not title:
            return
        try:
            datetime.strptime(self.event_date.get().strip(), DATE_FMT)
        except ValueError:
            messagebox.showerror("Invalid date", "Use YYYY-MM-DD for event date.")
            return

        self.data.events.append(
            Event(
                id=str(uuid.uuid4()),
                title=title,
                event_date=self.event_date.get().strip(),
                time=self.event_time.get().strip() or "09:00",
            )
        )
        self.event_title.set("")
        self.refresh_calendar()
        self.save_data()

    def save_notes(self) -> None:
        self.data.notes = self.notes_text.get("1.0", "end").strip()
        self.save_data()
        messagebox.showinfo("Saved", "Notes saved.")

    def add_goal(self) -> None:
        title = self.goal_title.get().strip()
        if not title:
            return
        try:
            datetime.strptime(self.goal_target.get().strip(), DATE_FMT)
            progress = max(0, min(100, int(self.goal_progress.get().strip())))
        except ValueError:
            messagebox.showerror("Invalid input", "Target must be YYYY-MM-DD and progress must be 0..100.")
            return

        self.data.goals.append(
            Goal(id=str(uuid.uuid4()), title=title, target_date=self.goal_target.get().strip(), progress=progress)
        )
        self.goal_title.set("")
        self.goal_progress.set("0")
        self.refresh_goals()
        self.save_data()

    def update_goal_progress(self) -> None:
        sel = self.goal_tree.selection()
        if not sel:
            return
        goal_id = sel[0]
        try:
            new_progress = max(0, min(100, int(self.goal_progress.get().strip())))
        except ValueError:
            return
        for g in self.data.goals:
            if g.id == goal_id:
                g.progress = new_progress
                break
        self.refresh_goals()
        self.save_data()

    def delete_goal(self) -> None:
        sel = self.goal_tree.selection()
        if not sel:
            return
        goal_id = sel[0]
        self.data.goals = [g for g in self.data.goals if g.id != goal_id]
        self.refresh_goals()
        self.save_data()

    def shift_month(self, offset: int) -> None:
        y = self.current_calendar.year
        m = self.current_calendar.month + offset
        while m < 1:
            m += 12
            y -= 1
        while m > 12:
            m -= 12
            y += 1
        self.current_calendar = date(y, m, 1)
        self.refresh_calendar()

    def refresh_task_tree(self) -> None:
        for iid in self.task_tree.get_children():
            self.task_tree.delete(iid)
        active_filter = self.task_filter.get()
        for t in sorted(self.data.tasks, key=lambda x: x.due):
            if active_filter != "All" and t.status != active_filter:
                continue
            self.task_tree.insert("", "end", iid=t.id, values=(t.title, t.due, t.priority, t.status, t.category, t.estimate_hours))

    def refresh_dashboard(self) -> None:
        today = date.today()
        total = len(self.data.tasks)
        due_today = 0
        overdue = 0
        done = 0

        upcoming: list[tuple[date, str]] = []
        for t in self.data.tasks:
            d = datetime.strptime(t.due, DATE_FMT).date()
            if t.status == "Done":
                done += 1
            if d == today and t.status != "Done":
                due_today += 1
            if d < today and t.status != "Done":
                overdue += 1
            if today <= d <= (today + timedelta(days=7)):
                upcoming.append((d, f"{d.isoformat()}  •  [{t.status}] {t.title} ({t.priority})"))

        self.summary_labels["total"].configure(text=str(total))
        self.summary_labels["today"].configure(text=str(due_today))
        self.summary_labels["overdue"].configure(text=str(overdue))
        self.summary_labels["done"].configure(text=str(done))

        self.upcoming_list.delete(0, "end")
        for _, line in sorted(upcoming, key=lambda x: x[0]):
            self.upcoming_list.insert("end", line)

    def refresh_calendar(self) -> None:
        year, month = self.current_calendar.year, self.current_calendar.month
        self.month_label.configure(text=self.current_calendar.strftime("%B %Y"))

        task_counts: dict[str, int] = {}
        for t in self.data.tasks:
            task_counts[t.due] = task_counts.get(t.due, 0) + 1
        event_counts: dict[str, int] = {}
        for e in self.data.events:
            event_counts[e.event_date] = event_counts.get(e.event_date, 0) + 1

        cal = calmod.monthcalendar(year, month)
        lines = ["Mo   Tu   We   Th   Fr   Sa   Su"]
        for week in cal:
            cells = []
            for d in week:
                if d == 0:
                    cells.append("    ")
                    continue
                day_str = date(year, month, d).strftime(DATE_FMT)
                marker = ""
                if task_counts.get(day_str, 0):
                    marker += "T"
                if event_counts.get(day_str, 0):
                    marker += "E"
                if not marker:
                    marker = "-"
                cells.append(f"{d:02d}{marker}")
            lines.append("  ".join(cells))

        legend = "\n\nLegend: T=Tasks, E=Events, -=None"
        self.calendar_text.delete("1.0", "end")
        self.calendar_text.insert("1.0", "\n".join(lines) + legend)

        self.event_list.delete(0, "end")
        for ev in sorted(self.data.events, key=lambda x: (x.event_date, x.time))[:100]:
            self.event_list.insert("end", f"{ev.event_date} {ev.time}  •  {ev.title}")

    def refresh_goals(self) -> None:
        for iid in self.goal_tree.get_children():
            self.goal_tree.delete(iid)
        for g in sorted(self.data.goals, key=lambda x: x.target_date):
            self.goal_tree.insert("", "end", iid=g.id, values=(g.title, g.target_date, g.progress))

    def refresh_notes(self) -> None:
        self.notes_text.delete("1.0", "end")
        self.notes_text.insert("1.0", self.data.notes)

    def refresh_all_views(self) -> None:
        self.refresh_task_tree()
        self.refresh_dashboard()
        self.refresh_calendar()
        self.refresh_goals()
        self.refresh_notes()

    def export_tasks_csv(self) -> None:
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(["id", "title", "due", "priority", "status", "category", "estimate_hours"])
            for t in self.data.tasks:
                writer.writerow([t.id, t.title, t.due, t.priority, t.status, t.category, t.estimate_hours])
        messagebox.showinfo("Export complete", f"Tasks exported to {path}")

    def export_notes(self) -> None:
        path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text", "*.txt")])
        if not path:
            return
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(self.notes_text.get("1.0", "end").strip())
        messagebox.showinfo("Export complete", f"Notes exported to {path}")

    def start_pomodoro(self) -> None:
        if self.pomodoro_running:
            return
        self.pomodoro_running = True
        self._tick_pomodoro()

    def pause_pomodoro(self) -> None:
        self.pomodoro_running = False
        if self.pomodoro_job:
            self.after_cancel(self.pomodoro_job)
            self.pomodoro_job = None

    def reset_pomodoro(self) -> None:
        self.pause_pomodoro()
        self.pomodoro_seconds_left = 25 * 60
        self.update_timer_label()

    def _tick_pomodoro(self) -> None:
        if not self.pomodoro_running:
            return
        self.pomodoro_seconds_left -= 1
        if self.pomodoro_seconds_left <= 0:
            self.pause_pomodoro()
            self.pomodoro_seconds_left = 25 * 60
            self.update_timer_label()
            messagebox.showinfo("Pomodoro", "Session complete! Take a short break.")
            return
        self.update_timer_label()
        self.pomodoro_job = self.after(1000, self._tick_pomodoro)

    def update_timer_label(self) -> None:
        mins, secs = divmod(max(0, self.pomodoro_seconds_left), 60)
        self.timer_label.configure(text=f"{mins:02d}:{secs:02d}")

    def save_data(self) -> None:
        self.data.notes = self.notes_text.get("1.0", "end").strip()
        self.data.save()

    def on_close(self) -> None:
        self.save_data()
        self.destroy()


if __name__ == "__main__":
    app = PlannerApp()
    app.mainloop()
