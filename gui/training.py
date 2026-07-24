import tkinter as tk
import threading
import time

def fmt_time(secs):
    secs = max(0, int(secs))
    h = secs // 3600
    m = (secs % 3600) // 60
    s = secs % 60
    return f"{h:02d}:{m:02d}:{s:02d}"

class TrainingWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("TREINO CRONOMETRADO")
        self.root.configure(bg="#000")
        self.root.geometry("800x400")
        self.root.resizable(True, True)
        self._training_time    = 0
        self._training_running = False
        self._count_up         = False
        self._build()
        self._tick()

    def _build(self):
        tk.Label(self.root, text="TREINO CRONOMETRADO",
                 font=("Courier New",13,"bold"),
                 bg="#000", fg="#333").pack(pady=(18,0))
        self.lbl_time = tk.Label(self.root, text="00:00:00",
                                  font=("Courier New",96,"bold"),
                                  bg="#000", fg="#ffffff")
        self.lbl_time.pack(expand=True)
        set_row = tk.Frame(self.root, bg="#000")
        set_row.pack(pady=(0,8))
        tk.Label(set_row, text="H", font=("Courier New",10),
                 bg="#000", fg="#444").grid(row=0, column=0, padx=(10,2))
        self.var_h = tk.StringVar(value="0")
        tk.Spinbox(set_row, from_=0, to=23, width=3,
                   textvariable=self.var_h,
                   font=("Courier New",12,"bold"),
                   bg="#111", fg="#fff", buttonbackground="#222",
                   relief="flat").grid(row=0, column=1, padx=2)
        tk.Label(set_row, text="M", font=("Courier New",10),
                 bg="#000", fg="#444").grid(row=0, column=2, padx=(8,2))
        self.var_m = tk.StringVar(value="20")
        tk.Spinbox(set_row, from_=0, to=59, width=3,
                   textvariable=self.var_m,
                   font=("Courier New",12,"bold"),
                   bg="#111", fg="#fff", buttonbackground="#222",
                   relief="flat").grid(row=0, column=3, padx=2)
        tk.Label(set_row, text="S", font=("Courier New",10),
                 bg="#000", fg="#444").grid(row=0, column=4, padx=(8,2))
        self.var_s = tk.StringVar(value="0")
        tk.Spinbox(set_row, from_=0, to=59, width=3,
                   textvariable=self.var_s,
                   font=("Courier New",12,"bold"),
                   bg="#111", fg="#fff", buttonbackground="#222",
                   relief="flat").grid(row=0, column=5, padx=2)
        self.var_mode = tk.StringVar(value="down")
        mode_row = tk.Frame(self.root, bg="#000")
        mode_row.pack(pady=(0,10))
        tk.Radiobutton(mode_row, text="Decrescente", variable=self.var_mode,
                       value="down", font=("Courier New",10),
                       bg="#000", fg="#888", selectcolor="#111",
                       activebackground="#000",
                       command=self._mode_changed).pack(side="left", padx=10)
        tk.Radiobutton(mode_row, text="Crescente", variable=self.var_mode,
                       value="up", font=("Courier New",10),
                       bg="#000", fg="#888", selectcolor="#111",
                       activebackground="#000",
                       command=self._mode_changed).pack(side="left", padx=10)
        btn_row = tk.Frame(self.root, bg="#000")
        btn_row.pack(pady=(0,20))
        def btn(text, cmd, bg, fg):
            return tk.Button(btn_row, text=text, command=cmd,
                             font=("Courier New",11,"bold"),
                             bg=bg, fg=fg, relief="flat", bd=0,
                             padx=14, pady=6, cursor="hand2")
        btn("INICIAR", self._start, "#004400", "#00ff88").pack(side="left", padx=6)
        btn("PARAR",   self._stop,  "#333",    "#aaa").pack(side="left", padx=6)
        btn("FECHAR",  self._reset, "#330000", "#ff6666").pack(side="left", padx=6)
        self.lbl_status = tk.Label(self.root, text="PRONTO",
                                    font=("Courier New",10,"bold"),
                                    bg="#000", fg="#333")
        self.lbl_status.pack(pady=(0,10))

    def _mode_changed(self):
        self._count_up = (self.var_mode.get() == "up")

    def _get_secs(self):
        try:
            return (int(self.var_h.get())*3600 +
                    int(self.var_m.get())*60 +
                    int(self.var_s.get()))
        except:
            return 0

    def _start(self):
        if self._training_running: return
        if self._training_time == 0:
            self._training_time = self._get_secs()
        self._training_running = True
        self._count_up = (self.var_mode.get() == "up")
        threading.Thread(target=self._run, daemon=True).start()
        self.lbl_status.config(text="A CORRER", fg="#00cc44")

    def _run(self):
        while self._training_running:
            time.sleep(1)
            if not self._training_running: break
            if self._count_up:
                self._training_time += 1
            else:
                self._training_time = max(0, self._training_time - 1)
                if self._training_time == 0:
                    self._training_running = False
                    self.root.after(0, lambda: self.lbl_status.config(
                        text="TEMPO ESGOTADO!", fg="#ff2200"))
                    self.root.after(0, lambda: self.lbl_time.config(fg="#ff2200"))
                    break

    def _stop(self):
        self._training_running = False
        self.lbl_status.config(text="PAUSADO", fg="#ffaa00")

    def _reset(self):
        self._training_running = False
        self._training_time    = 0
        self.lbl_time.config(text="00:00:00", fg="#ffffff")
        self.lbl_status.config(text="PRONTO", fg="#333")

    def _tick(self):
        self.lbl_time.config(text=fmt_time(self._training_time))
        self.root.after(200, self._tick)
