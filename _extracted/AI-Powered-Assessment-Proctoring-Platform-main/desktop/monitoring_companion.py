import threading
import time
import tkinter as tk
from tkinter import messagebox

import psutil
import requests
import win32gui
import win32process


POLL_SECONDS = 2
SESSION_CHECK_SECONDS = 20
APP_NAMES = {
    "explorer.exe": ("File Explorer", "FILE_EXPLORER_OPENED"),
    "powershell.exe": ("PowerShell", "TERMINAL_OPENED"),
    "pwsh.exe": ("PowerShell", "TERMINAL_OPENED"),
    "cmd.exe": ("Command Prompt", "TERMINAL_OPENED"),
    "windowsterminal.exe": ("Windows Terminal", "TERMINAL_OPENED"),
    "code.exe": ("VS Code", "IDE_OPENED"),
}
BROWSER_PROCESSES = {
    "chrome.exe", "msedge.exe", "firefox.exe", "brave.exe", "opera.exe",
}


class InterviewDesktopMonitor:
    def __init__(self, interview_id: int, token: str, api_url: str, on_status):
        self.interview_id = interview_id
        self.token = token
        self.api_url = api_url.rstrip("/")
        self.on_status = on_status
        self.stop_event = threading.Event()
        self.last_process = None
        self.last_session_check = 0.0
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})

    def request(self, method: str, path: str, **kwargs):
        return self.session.request(
            method,
            f"{self.api_url}{path}",
            timeout=8,
            **kwargs,
        )

    def active_application(self):
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return None
        _thread_id, process_id = win32process.GetWindowThreadProcessId(hwnd)
        try:
            process_name = psutil.Process(process_id).name().lower()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return None
        known = APP_NAMES.get(process_name)
        app_name = known[0] if known else process_name.removesuffix(".exe").replace("_", " ").title()
        return process_name, app_name, known[1] if known else None

    def send_event(self, event_type: str, details: str, process_name: str, app_name: str):
        response = self.request(
            "POST",
            f"/interviews/{self.interview_id}/desktop-events",
            json={
                "event_type": event_type,
                "details": details,
                "app_name": app_name,
                "process_name": process_name,
            },
        )
        if response.status_code >= 400:
            self.on_status(f"Event rejected by server ({response.status_code}).")

    def ensure_session_active(self):
        response = self.request("GET", f"/interviews/{self.interview_id}")
        if not response.ok:
            return False
        interview = response.json()
        return interview.get("status") in {"active", "in_progress"} and interview.get("candidate_consent") is True

    def register_device(self, connected: bool):
        self.request(
            "POST",
            f"/interviews/{self.interview_id}/device-status",
            json={"device_type": "desktop_companion", "connected": connected},
        )

    def run(self):
        try:
            self.register_device(True)
            self.on_status("Monitoring active. Only the foreground app and process name are checked.")
            while not self.stop_event.wait(POLL_SECONDS):
                now = time.monotonic()
                if now - self.last_session_check >= SESSION_CHECK_SECONDS:
                    self.last_session_check = now
                    if not self.ensure_session_active():
                        self.on_status("Interview ended or consent is no longer active; monitoring stopped.")
                        self.stop_event.set()
                        break

                app = self.active_application()
                if app is None:
                    continue
                process_name, app_name, specific_event = app
                if process_name == self.last_process:
                    continue
                previous_process = self.last_process
                self.last_process = process_name
                if previous_process is None:
                    continue

                self.send_event(
                    "APP_SWITCH",
                    "Foreground application changed during the interview.",
                    process_name,
                    app_name,
                )
                if previous_process in BROWSER_PROCESSES and process_name not in BROWSER_PROCESSES:
                    self.send_event(
                        "BROWSER_FOCUS_LOST",
                        "The browser lost foreground focus.",
                        process_name,
                        app_name,
                    )
                if specific_event:
                    details = f"{app_name} became the foreground application."
                    self.send_event(specific_event, details, process_name, app_name)
        except requests.RequestException as exc:
            self.on_status(f"Monitoring connection error: {exc}")
        finally:
            try:
                self.register_device(False)
            except requests.RequestException:
                pass
            self.on_status("Monitoring stopped.")

    def stop(self):
        self.stop_event.set()


class CompanionWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("ExtensionGuard Desktop Monitor")
        self.root.geometry("430x460")
        self.root.resizable(False, False)
        self.monitor = None
        self.monitor_thread = None
        self._build_ui()

    def _build_ui(self):
        frame = tk.Frame(self.root, padx=22, pady=20)
        frame.pack(fill="both", expand=True)
        tk.Label(frame, text="ExtensionGuard", font=("Segoe UI", 18, "bold")).pack(anchor="w")
        tk.Label(frame, text="Interview desktop monitor", font=("Segoe UI", 11)).pack(anchor="w", pady=(0, 12))

        disclosure = (
            "With your consent, this app checks which application is in the foreground and records "
            "application switches during the active interview. It does not record keystrokes, "
            "screenshots, window titles, file names, or file contents. Monitoring is visible and "
            "can be stopped at any time."
        )
        tk.Label(frame, text=disclosure, justify="left", wraplength=380, bg="#eef4ef", padx=12, pady=10).pack(fill="x")

        self.session_id = self._field(frame, "Interview session ID", "")
        self.token = self._field(frame, "Signed-in account token", "", show="*")
        self.api_url = self._field(frame, "Backend URL", "http://localhost:8000")
        self.consent = tk.BooleanVar(value=False)
        tk.Checkbutton(
            frame,
            text="I understand and consent to desktop monitoring for this interview.",
            variable=self.consent,
            wraplength=370,
            justify="left",
        ).pack(anchor="w", pady=10)

        self.start_button = tk.Button(frame, text="Verify session and start", command=self.start_monitoring)
        self.start_button.pack(fill="x", pady=(2, 8))
        self.stop_button = tk.Button(frame, text="Stop monitoring", command=self.stop_monitoring, state="disabled")
        self.stop_button.pack(fill="x")
        self.status = tk.StringVar(value="Not monitoring")
        tk.Label(frame, textvariable=self.status, wraplength=380, justify="left", pady=12).pack(anchor="w")

    def _field(self, parent, label, default, show=None):
        tk.Label(parent, text=label, font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(10, 3))
        entry = tk.Entry(parent, show=show)
        entry.insert(0, default)
        entry.pack(fill="x")
        return entry

    def set_status(self, text):
        self.root.after(0, self.status.set, text)

    def start_monitoring(self):
        if not self.consent.get():
            messagebox.showwarning("Consent required", "Review the disclosure and select the consent checkbox to start.")
            return
        try:
            interview_id = int(self.session_id.get())
            token = self.token.get().strip()
            api_url = self.api_url.get().strip().rstrip("/")
            if interview_id <= 0 or not token or not api_url:
                raise ValueError
        except ValueError:
            messagebox.showerror("Missing information", "Enter a valid session ID, token, and backend URL.")
            return

        self.start_button.config(state="disabled")
        self.set_status("Verifying interview session and recorded consent...")
        threading.Thread(
            target=self._verify_and_start,
            args=(interview_id, token, api_url),
            daemon=True,
        ).start()

    def _verify_and_start(self, interview_id, token, api_url):
        try:
            response = requests.get(
                f"{api_url}/interviews/{interview_id}",
                headers={"Authorization": f"Bearer {token}"},
                timeout=8,
            )
            response.raise_for_status()
            interview = response.json()
            if interview.get("status") not in {"active", "in_progress"} or interview.get("candidate_consent") is not True:
                raise ValueError("The interview must be active and candidate consent must already be recorded.")
            self.monitor = InterviewDesktopMonitor(interview_id, token, api_url, self.set_status)
            self.monitor_thread = threading.Thread(target=self.monitor.run, daemon=True)
            self.monitor_thread.start()
            self.root.after(0, self._set_running, True)
        except requests.RequestException as exc:
            self.set_status(f"Could not connect to the interview backend: {exc}")
            self.root.after(0, self.start_button.config, {"state": "normal"})
        except ValueError as exc:
            self.set_status(str(exc))
            self.root.after(0, self.start_button.config, {"state": "normal"})

    def _set_running(self, running):
        self.start_button.config(state="disabled" if running else "normal")
        self.stop_button.config(state="normal" if running else "disabled")

    def stop_monitoring(self):
        if self.monitor:
            self.monitor.stop()
        self.stop_button.config(state="disabled")
        self.set_status("Stopping monitor...")

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    CompanionWindow().run()