from __future__ import annotations
from pathlib import Path
from tkinter import ttk, filedialog, messagebox
import tkinter as tk

from ..core import ProcessService, Options, list_files

APP_TITLE = "Nas File Organizer"

class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("820x560")

        self.folder = tk.StringVar()
        self.outdir = tk.StringVar()
        self.recursive = tk.BooleanVar(value=True)
        self.add_suffix = tk.BooleanVar(value=True)
        self.suffix_text = tk.StringVar(value="_processed")

        self._build_header()
        self._build_options()

        self.log = tk.Text(self, height=16, wrap="none")
        self.log.pack(fill="both", expand=True, padx=10, pady=(4, 10))

    def _build_header(self) -> None:
        row = ttk.Frame(self); row.pack(fill="x", padx=10, pady=(10, 6))
        ttk.Label(row, text="Folder:").pack(side="left")
        ttk.Entry(row, textvariable=self.folder, width=60).pack(side="left", padx=6)
        ttk.Button(row, text="Browse", command=self._choose_folder).pack(side="left")

        ttk.Label(row, text=" Output:").pack(side="left", padx=(12, 0))
        ttk.Entry(row, textvariable=self.outdir, width=40).pack(side="left", padx=6)
        ttk.Button(row, text="Select", command=self._choose_outdir).pack(side="left")

    def _build_options(self) -> None:
        box = ttk.LabelFrame(self, text="Options"); box.pack(fill="x", padx=10, pady=6)
        ttk.Checkbutton(box, text="Recursive", variable=self.recursive).pack(side="left", padx=10, pady=8)
        ttk.Checkbutton(box, text="Append suffix", variable=self.add_suffix).pack(side="left", padx=10, pady=8)
        ttk.Label(box, text="Suffix:").pack(side="left")
        ttk.Entry(box, textvariable=self.suffix_text, width=14).pack(side="left", padx=6)
        ttk.Button(box, text="Preview", command=self.preview).pack(side="right", padx=6)
        ttk.Button(box, text="Run", command=self.run).pack(side="right")

    def _choose_folder(self) -> None:
        d = filedialog.askdirectory(title="Select source folder")
        if d:
            self.folder.set(d)
            count = sum(1 for _ in list_files(Path(d), recursive=True))
            self._append(f"Loaded: {count} files")

    def _choose_outdir(self) -> None:
        d = filedialog.askdirectory(title="Select output folder")
        if d:
            self.outdir.set(d)
            self._append(f"Output set to: {d}")

    def preview(self) -> None:
        src = self._src()
        out = self._out()
        if not src or not out: return
        svc = ProcessService()
        files = list(list_files(src, self.recursive.get()))
        opts = Options(recursive=self.recursive.get(), add_suffix=self.add_suffix.get(), suffix_text=self.suffix_text.get())
        plan = svc.preview(files, out, opts)
        self.log.delete("1.0", "end")
        self._append(f"Preview: {len(plan)} files")
        for r in plan[:40]:
            self._append(f"{r.src.name} -> {r.dst.name}")
        if len(plan) > 40:
            self._append(f"... and {len(plan) - 40} more")

    def run(self) -> None:
        src = self._src()
        out = self._out()
        if not src or not out: return
        svc = ProcessService()
        files = list(list_files(src, self.recursive.get()))
        opts = Options(recursive=self.recursive.get(), add_suffix=self.add_suffix.get(), suffix_text=self.suffix_text.get())

        done = 0
        def progress(i: int, total: int): pass
        def log(msg: str): self._append(msg)

        for res in svc.execute(files, out, opts, progress=progress, log=log):
            done += 1
        self._append(f"Done. Processed {done} file(s). Output: {out}")

    def _src(self) -> Path | None:
        if not self.folder.get():
            messagebox.showwarning("Pick folder", "Select a source folder.")
            return None
        return Path(self.folder.get())

    def _out(self) -> Path | None:
        if self.outdir.get():
            return Path(self.outdir.get())
        # default output next to source
        p = Path(self.folder.get())
        return p / "output"

    def _append(self, msg: str) -> None:
        self.log.insert("end", msg + "\n"); self.log.see("end")

def main() -> None:
    App().mainloop()

if __name__ == "__main__":
    main()