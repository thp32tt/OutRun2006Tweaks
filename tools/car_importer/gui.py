"""Windows Tk GUI. All game modifications intentionally disabled until native QA."""
from __future__ import annotations
import json
from pathlib import Path
import queue
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# Support direct invocation and PyInstaller with --paths tools.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from car_importer.cli import stage_model, build_sidecar
from car_importer.game import make_backup, restore_backup, verify_game
from car_importer.glb import inspect_glb
from car_importer.profiles import PROFILES


class ImporterApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("OutRun Car Importer + OVC2 Sidecar F50 test")
        root.geometry("900x710")
        root.minsize(780, 620)
        self.glb = tk.StringVar()
        self.blender = tk.StringVar()
        self.game_root = tk.StringVar()
        self.ref_blend = tk.StringVar()
        self.output = tk.StringVar()
        self.sidecar_folder = tk.StringVar()
        self.profile = tk.StringVar(value="f50")
        self.legal = tk.BooleanVar(value=False)
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.busy = False
        outer = ttk.Frame(root, padding=18)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="OutRun 2006 Car Importer", font=("Segoe UI", 20, "bold")).pack(anchor="w")
        ttk.Label(outer, text="외부 GLB 검사 → Blender 정렬/시제품 생성 → 독립 QA   |   게임 적용 기능은 아직 비활성화",
                  foreground="#8B4A10").pack(anchor="w", pady=(0, 14))
        form = ttk.Frame(outer)
        form.pack(fill="x")
        self.path_row(form, 0, "외부 모델 (.glb)", self.glb, lambda: self.choose_file(self.glb, [("GLB", "*.glb")]))
        self.path_row(form, 1, "Blender 실행 파일", self.blender, lambda: self.choose_file(self.blender, [("Blender", "blender.exe"), ("All", "*")]))
        self.path_row(form, 2, "원본 .blend (선택)", self.ref_blend, lambda: self.choose_file(self.ref_blend, [("Blender project", "*.blend")]))
        self.path_row(form, 3, "게임 설치 폴더", self.game_root, lambda: self.choose_dir(self.game_root))
        self.path_row(form, 4, "Blender 시제품 폴더", self.output, lambda: self.choose_dir(self.output))
        self.path_row(form, 5, "별도 OVC2 모델 폴더", self.sidecar_folder, lambda: self.choose_dir(self.sidecar_folder))
        ttk.Label(form, text="차량 프로필").grid(row=6, column=0, sticky="w", pady=8)
        dropdown = ttk.Combobox(form, textvariable=self.profile, values=list(PROFILES), state="readonly", width=18)
        dropdown.grid(row=6, column=1, sticky="w", pady=8)
        ttk.Label(form, text="F50 전용 테스트").grid(row=6, column=2, sticky="w", padx=6)
        form.columnconfigure(1, weight=1)
        ttk.Checkbutton(outer, variable=self.legal,
                        text="선택한 외부 모델을 개인적으로 사용·변환할 권한이 있음을 직접 확인했습니다.").pack(anchor="w", pady=(13, 9))
        tools = ttk.Frame(outer)
        tools.pack(fill="x", pady=6)
        self.add_btn(tools, "1. GLB 검사", self.inspect, 0)
        self.add_btn(tools, "2. Blender 시제품 생성", self.stage, 1)
        self.add_btn(tools, "3. F50 OVC2 출력", self.sidecar, 2)
        self.add_btn(tools, "원본 게임 검증", self.verify, 3)
        self.add_btn(tools, "원본 백업", self.backup, 4)
        self.add_btn(tools, "백업 검증", self.restore, 5)
        ttk.Button(tools, text="게임 설치 (검증 전)", state="disabled").grid(row=1, column=0, columnspan=6, sticky="ew", pady=(9, 0))
        for c in range(6):
            tools.columnconfigure(c, weight=1)
        ttk.Label(outer, text="작업 결과", font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(10, 3))
        self.output_text = tk.Text(outer, font=("Consolas", 10), wrap="word", height=15)
        self.output_text.pack(fill="both", expand=True)
        self.output_text.insert("end", "모델 바이너리는 자체 배포하지 않습니다. 게임 원본 파일은 변경하지 않습니다.\n")
        self.output_text.configure(state="disabled")
        root.after(120, self.flush_events)

    @staticmethod
    def path_row(parent, row, label, var, command):
        ttk.Label(parent, text=label, width=20).grid(row=row, column=0, sticky="w", pady=5)
        ttk.Entry(parent, textvariable=var).grid(row=row, column=1, sticky="ew", padx=7, pady=5)
        ttk.Button(parent, text="찾아보기", command=command).grid(row=row, column=2, sticky="ew", pady=5)

    @staticmethod
    def choose_file(var, types):
        value = filedialog.askopenfilename(filetypes=types)
        if value:
            var.set(value)

    @staticmethod
    def choose_dir(var):
        value = filedialog.askdirectory()
        if value:
            var.set(value)

    @staticmethod
    def add_btn(frame, label, callback, column):
        ttk.Button(frame, text=label, command=callback).grid(row=0, column=column, padx=3, sticky="ew")

    def log(self, line):
        self.output_text.configure(state="normal")
        self.output_text.insert("end", str(line) + "\n")
        self.output_text.see("end")
        self.output_text.configure(state="disabled")

    def flush_events(self):
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == "result":
                    self.log(json.dumps(value, indent=2, ensure_ascii=False))
                elif kind == "error":
                    self.log("차단: " + str(value))
                    messagebox.showerror("작업 실패 / 안전 차단", str(value))
                elif kind == "done":
                    self.busy = False
        except queue.Empty:
            pass
        self.root.after(120, self.flush_events)

    def run(self, callback):
        if self.busy:
            messagebox.showinfo("실행 중", "현재 작업이 끝난 뒤 다시 실행하세요.")
            return
        self.busy = True
        def background():
            try:
                self.events.put(("result", callback()))
            except Exception as exc:
                self.events.put(("error", exc))
            finally:
                self.events.put(("done", None))
        threading.Thread(target=background, daemon=True).start()

    def inspect(self):
        glb = self.glb.get()
        self.run(lambda: inspect_glb(glb))

    def stage(self):
        if not self.legal.get():
            messagebox.showwarning("권한 확인 필요", "외부 모델의 이용·변환 권한을 직접 확인해 주세요.")
            return
        values = (self.glb.get(), self.blender.get(), self.output.get(), self.profile.get(), self.ref_blend.get() or None)
        self.log("Blender 시제품 제작 시작. 게임 파일은 변경하지 않습니다.")
        self.run(lambda: stage_model(values[0], values[1], values[2], values[3], True, values[4]))

    def sidecar(self):
        if not self.legal.get():
            messagebox.showwarning("권한 확인 필요", "외부 모델 변환 권한을 확인하세요.")
            return
        args = (self.output.get(), self.blender.get(), self.sidecar_folder.get())
        self.log("F50 OVC2 생성: 원본 PMT는 그대로 유지됩니다.")
        self.run(lambda: build_sidecar(*args, rights_confirmed=True))

    def verify(self):
        self.run(lambda: verify_game(self.game_root.get(), self.profile.get()))

    def backup(self):
        if not self.game_root.get() or not self.output.get():
            messagebox.showwarning("경로 필요", "게임 폴더와 백업 출력 폴더를 선택하세요.")
            return
        self.run(lambda: make_backup(self.game_root.get(), self.output.get(), self.profile.get()))

    def restore(self):
        receipt = filedialog.askopenfilename(title="기존 백업의 receipt.json 선택", filetypes=[("JSON receipt", "receipt.json")])
        if receipt:
            self.run(lambda: restore_backup(self.game_root.get(), receipt))


def main():
    root = tk.Tk()
    ImporterApp(root)
    root.mainloop()


def packaged_self_test() -> int:
    """Headless EXE smoke test of files used by the separate Blender interpreter."""
    from car_importer import cli
    helper_dir = Path(cli.__file__).resolve().parent
    return 0 if all((helper_dir / name).is_file() for name in
                    ("blender_worker.py", "profiles.py", "sidecar_worker.py")) else 3


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        raise SystemExit(packaged_self_test())
    main()