import tkinter as tk
import threading
import time
import random

# ═══════════════════════════════════════════════════════
#  ESTADO PARTILHADO
# ═══════════════════════════════════════════════════════
class SharedState:
    def __init__(self):
        self.lock = threading.Lock()

        # Semáforo
        self.sema_mode    = "none"      # none | auto | manual | grelha
        self.sema_lights  = [False]*5
        self.sema_green   = False
        self.sema_running = False

        # Fase do display principal
        self.phase = "semaforo"         # "semaforo" | "race"

        # Bandeira / sector
        self.bandeira = "none"
        self.sector   = "none"

        # Tempo de sessao (segundos, conta decrescente)
        self.session_time    = 0
        self.session_set     = 0        # valor definido no controlo
        self.session_running = False

        # Pilotos
        self.pilots = [
            {"pos": i+1, "nome": f"Piloto {i+1}",
             "tempo": "--:--.---", "melhor": "--:--.---",
             "volta": 0, "diferenca": "--"}
            for i in range(5)
        ]

        # Callbacks
        self.display_callbacks  = []
        self.training_callbacks = []   # janela de treino cronometrado

    def notify(self):
        for cb in self.display_callbacks + self.training_callbacks:
            try: cb()
            except: pass

STATE = SharedState()

# utilitário de formatação
def fmt_time(secs):
    secs = max(0, int(secs))
    h = secs // 3600
    m = (secs % 3600) // 60
    s = secs % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


# ═══════════════════════════════════════════════════════
#  JANELA DISPLAY  (ecrã grande de corrida)
# ═══════════════════════════════════════════════════════
class DisplayWindow:
    LIGHT_D = 110

    def __init__(self, root):
        self.root = root
        self.root.title("RACE DISPLAY")
        self.root.configure(bg="#0a0a0a")
        self.root.geometry("1280x720")
        self.root.resizable(True, True)

        self._build_semaforo_screen()
        self._build_race_screen()

        STATE.display_callbacks.append(self._refresh)
        self._show_phase()
        self._tick()

    # ── ecrã 1: só semáforo ─────────────────────────────
    def _build_semaforo_screen(self):
        self.frame_sema = tk.Frame(self.root, bg="#0a0a0a")

        tk.Label(self.frame_sema, text="S E M A F O R O",
                 font=("Courier New", 16, "bold"),
                 bg="#0a0a0a", fg="#222").pack(pady=(40, 0))

        lights_row = tk.Frame(self.frame_sema, bg="#0a0a0a")
        lights_row.pack(expand=True)

        self.big_canvases = []
        for i in range(5):
            c = tk.Canvas(lights_row,
                          width=self.LIGHT_D + 20,
                          height=self.LIGHT_D + 20,
                          bg="#0a0a0a", highlightthickness=0)
            c.pack(side="left", padx=14)
            self.big_canvases.append(c)

        self.lbl_sema_big = tk.Label(self.frame_sema, text="",
                                      font=("Courier New", 20, "bold"),
                                      bg="#0a0a0a", fg="#555")
        self.lbl_sema_big.pack(pady=30)

    # ── ecrã 2: corrida (pilotos + tempo + bandeira) ────
    def _build_race_screen(self):
        self.frame_race = tk.Frame(self.root, bg="#0a0a0a")

        # Pilotos
        top = tk.Frame(self.frame_race, bg="#111")
        top.pack(fill="x", padx=6, pady=(6, 2))

        headers = ["POS", "PILOTO", "TEMPO", "MELHOR", "V", "DIFER"]
        widths  = [4, 14, 12, 12, 4, 10]
        for i, (h, w) in enumerate(zip(headers, widths)):
            tk.Label(top, text=h,
                     font=("Courier New", 10, "bold"),
                     bg="#222", fg="#777", width=w,
                     anchor="center").grid(row=0, column=i, padx=1, pady=1, sticky="ew")
        for c in range(6):
            top.columnconfigure(c, weight=1)

        self.pilot_rows = []
        for r in range(5):
            row_cells = []
            for c, w in enumerate(widths):
                lbl = tk.Label(top, text="",
                               font=("Courier New", 13, "bold"),
                               bg="#1a1a1a", fg="#e0e0e0", width=w,
                               anchor="center", pady=5)
                lbl.grid(row=r+1, column=c, padx=1, pady=1, sticky="ew")
                row_cells.append(lbl)
            self.pilot_rows.append(row_cells)

        # Tempo + Bandeira  (sem semáforo mini)
        mid = tk.Frame(self.frame_race, bg="#0a0a0a")
        mid.pack(fill="both", expand=True, padx=6, pady=4)
        mid.columnconfigure(0, weight=3)
        mid.columnconfigure(1, weight=2)
        mid.rowconfigure(0, weight=1)

        # Tempo sessao
        tf = tk.Frame(mid, bg="#111")
        tf.grid(row=0, column=0, sticky="nsew", padx=(0, 3))
        tk.Label(tf, text="TEMPO DA SESSAO",
                 font=("Courier New", 10, "bold"),
                 bg="#111", fg="#444").pack(pady=(12, 2))
        self.lbl_time = tk.Label(tf, text="00:00:00",
                                  font=("Courier New", 60, "bold"),
                                  bg="#111", fg="#00ff88")
        self.lbl_time.pack(expand=True)

        # Bandeira + Sector
        ff = tk.Frame(mid, bg="#111")
        ff.grid(row=0, column=1, sticky="nsew", padx=(3, 0))
        tk.Label(ff, text="BANDEIRA / SECTOR",
                 font=("Courier New", 10, "bold"),
                 bg="#111", fg="#444").pack(pady=(12, 2))
        self.flag_canvas = tk.Canvas(ff, bg="#111", height=110,
                                      highlightthickness=0)
        self.flag_canvas.pack(fill="x", padx=10, pady=6)
        self.lbl_sector = tk.Label(ff, text="",
                                    font=("Courier New", 20, "bold"),
                                    bg="#111", fg="#ffcc00")
        self.lbl_sector.pack(pady=6)

    # ── desenho das luzes ────────────────────────────────
    def _draw_light(self, canvas, diameter, active_red, active_green):
        d = diameter
        canvas.delete("all")
        m = 5
        canvas.create_oval(m, m, d+m, d+m,
                            fill="#0d0d0d", outline="#2a2a2a", width=3)
        if active_green:
            outer, inner = "#003311", "#00ff44"
        elif active_red:
            outer, inner = "#3a0000", "#ff2200"
        else:
            outer, inner = "#0a0000", "#1a0000"
        p = diameter // 6
        canvas.create_oval(m+p, m+p, d+m-p, d+m-p, fill=outer, outline="")
        p2 = p + diameter // 8
        canvas.create_oval(m+p2, m+p2, d+m-p2, d+m-p2, fill=inner, outline="")
        if active_red or active_green:
            rp = p2 + 4
            canvas.create_oval(m+rp, m+rp,
                                m+rp+diameter//5, m+rp+diameter//8,
                                fill="white", outline="", stipple="gray50")

    def _draw_big_lights(self):
        for i in range(5):
            self._draw_light(self.big_canvases[i], self.LIGHT_D,
                             STATE.sema_lights[i], STATE.sema_green)

    # ── troca de fase ────────────────────────────────────
    def _show_phase(self):
        if STATE.phase == "semaforo":
            self.frame_race.pack_forget()
            self.frame_sema.pack(fill="both", expand=True)
        else:
            self.frame_sema.pack_forget()
            self.frame_race.pack(fill="both", expand=True)

    # ── refresh ──────────────────────────────────────────
    def _refresh(self):
        self._show_phase()
        self._draw_big_lights()

        if STATE.sema_green:
            self.lbl_sema_big.config(text="GO!",
                                      fg="#00ff44",
                                      font=("Courier New", 48, "bold"))
        else:
            modes = {"auto":"AUTOMATICO","manual":"MANUAL",
                     "grelha":"GRELHA","none":""}
            self.lbl_sema_big.config(
                text=modes.get(STATE.sema_mode, ""),
                fg="#444",
                font=("Courier New", 18, "bold"))

        # Pilotos
        for r, p in enumerate(STATE.pilots):
            vals = [str(p["pos"]), p["nome"], p["tempo"],
                    p["melhor"], str(p["volta"]), p["diferenca"]]
            for c, v in enumerate(vals):
                self.pilot_rows[r][c].config(text=v)

        # Bandeira
        fc_map = {"none":"#111","verde":"#006622","vermelho":"#880000",
                  "amarelo":"#886600","azul":"#003388"}
        fg_map = {"none":"#111","verde":"#00ff66","vermelho":"#ff4444",
                  "amarelo":"#ffdd00","azul":"#44aaff"}
        fc = fc_map.get(STATE.bandeira, "#111")
        fg = fg_map.get(STATE.bandeira, "#fff")
        self.flag_canvas.delete("all")
        w = self.flag_canvas.winfo_width() or 300
        self.flag_canvas.create_rectangle(0, 0, w, 110, fill=fc, outline="")
        if STATE.bandeira != "none":
            self.flag_canvas.create_text(w//2, 55,
                text=STATE.bandeira.upper(),
                font=("Courier New", 28, "bold"), fill=fg)
        self.lbl_sector.config(
            text="" if STATE.sector == "none" else STATE.sector)

    def _tick(self):
        self.lbl_time.config(text=fmt_time(STATE.session_time))
        self._draw_big_lights()
        self.root.after(100, self._tick)


# ═══════════════════════════════════════════════════════
#  JANELA DE TREINO CRONOMETRADO  (só o tempo, grande)
# ═══════════════════════════════════════════════════════
class TrainingWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("TREINO CRONOMETRADO")
        self.root.configure(bg="#000")
        self.root.geometry("800x400")
        self.root.resizable(True, True)

        self._training_time   = 0
        self._training_running = False
        self._count_up         = False   # False = decrescente, True = crescente

        self._build()
        self._tick()

    def _build(self):
        # Título
        tk.Label(self.root, text="TREINO CRONOMETRADO",
                 font=("Courier New", 13, "bold"),
                 bg="#000", fg="#333").pack(pady=(18, 0))

        # Tempo grande
        self.lbl_time = tk.Label(self.root, text="00:00:00",
                                  font=("Courier New", 96, "bold"),
                                  bg="#000", fg="#ffffff")
        self.lbl_time.pack(expand=True)

        # Controlo de tempo
        set_row = tk.Frame(self.root, bg="#000")
        set_row.pack(pady=(0, 8))
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

        # Modo crescente / decrescente
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

        # Botões
        btn_row = tk.Frame(self.root, bg="#000")
        btn_row.pack(pady=(0, 20))

        def btn(text, cmd, bg, fg, **kw):
            return tk.Button(btn_row, text=text, command=cmd,
                             font=("Courier New",11,"bold"),
                             bg=bg, fg=fg, relief="flat", bd=0,
                             padx=14, pady=6, cursor="hand2", **kw)

        btn("INICIAR",  self._start,  "#004400", "#00ff88").pack(side="left", padx=6)
        btn("PARAR",    self._stop,   "#333",    "#aaa").pack(side="left", padx=6)
        btn("FECHAR",   self._reset,  "#330000", "#ff6666").pack(side="left", padx=6)

        # Status
        self.lbl_status = tk.Label(self.root, text="PRONTO",
                                    font=("Courier New",10,"bold"),
                                    bg="#000", fg="#333")
        self.lbl_status.pack(pady=(0,10))

    def _mode_changed(self):
        self._count_up = (self.var_mode.get() == "up")

    def _get_secs(self):
        try:
            return (int(self.var_h.get())*3600 +
                    int(self.var_m.get())*60  +
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


# ═══════════════════════════════════════════════════════
#  JANELA CONTROLO
# ═══════════════════════════════════════════════════════
class ControlWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("RACE CONTROL PANEL")
        self.root.configure(bg="#0d0d0d")
        self.root.geometry("680x720")
        self.root.resizable(False, False)

        self._sema_thread   = None
        self._manual_lights = 0
        self._waiting_green = False
        self._training_win  = None

        self._build()

    # ── helpers UI ──────────────────────────────────────
    def _section(self, parent, title, **kw):
        return tk.LabelFrame(parent, text=f"  {title}  ",
                             font=("Courier New", 9, "bold"),
                             bg="#0d0d0d", fg="#555",
                             bd=1, relief="solid", labelanchor="nw", **kw)

    def _btn(self, parent, text, cmd, bg="#222", fg="#ddd", **kw):
        return tk.Button(parent, text=text, command=cmd,
                         font=("Courier New", 10, "bold"),
                         bg=bg, fg=fg,
                         activebackground="#444", activeforeground="#fff",
                         relief="flat", bd=0, padx=8, pady=5,
                         cursor="hand2", **kw)

    # ── construção ──────────────────────────────────────
    def _build(self):
        # Título + botão RESTART
        header = tk.Frame(self.root, bg="#0d0d0d")
        header.pack(fill="x", padx=10, pady=(10, 4))

        tk.Label(header, text="RACE CONTROL PANEL",
                 font=("Courier New", 14, "bold"),
                 bg="#0d0d0d", fg="#cc1100").pack(side="left")

        self._btn(header, "↺  RESTART",
                  self._do_restart,
                  bg="#440000", fg="#ff4444").pack(side="right", padx=4)

        self._btn(header, "⏱  TREINO",
                  self._open_training,
                  bg="#001133", fg="#4488ff").pack(side="right", padx=4)

        # Layout em duas colunas
        main = tk.Frame(self.root, bg="#0d0d0d")
        main.pack(fill="both", expand=True, padx=10, pady=2)
        main.columnconfigure(0, weight=1)
        main.columnconfigure(1, weight=1)

        left  = tk.Frame(main, bg="#0d0d0d")
        right = tk.Frame(main, bg="#0d0d0d")
        left.grid (row=0, column=0, sticky="nsew", padx=(0, 4))
        right.grid(row=0, column=1, sticky="nsew", padx=(4, 0))

        # ══ ESQUERDA ══

        # Semáforo
        sema_sec = self._section(left, "SEMAFORO")
        sema_sec.pack(fill="x", pady=(0, 6))

        prev_row = tk.Frame(sema_sec, bg="#0d0d0d")
        prev_row.pack(pady=6)
        self.mini_cvs = []
        for i in range(5):
            c = tk.Canvas(prev_row, width=34, height=34,
                          bg="#0d0d0d", highlightthickness=0)
            c.grid(row=0, column=i, padx=3)
            self.mini_cvs.append(c)
        self._draw_mini()

        mode_row = tk.Frame(sema_sec, bg="#0d0d0d")
        mode_row.pack(pady=4)
        self._btn(mode_row, "AUTO",   self._sema_auto,
                  bg="#003333", fg="#00ffcc", width=10).grid(row=0,column=0,padx=3,pady=2)
        self._btn(mode_row, "MANUAL", self._sema_manual,
                  bg="#332200", fg="#ffaa00", width=10).grid(row=0,column=1,padx=3,pady=2)
        self._btn(mode_row, "GRELHA", self._sema_grelha,
                  bg="#330033", fg="#ff88ff", width=10).grid(row=1,column=0,padx=3,pady=2)
        self._btn(mode_row, "PARAR",  self._sema_stop,
                  bg="#1a1a1a", fg="#777",   width=10).grid(row=1,column=1,padx=3,pady=2)

        # AUTO: tempo até verde
        auto_frm = tk.Frame(sema_sec, bg="#0d0d0d")
        auto_frm.pack(pady=4)
        tk.Label(auto_frm, text="Tempo ate verde (seg):",
                 font=("Courier New", 9), bg="#0d0d0d", fg="#555").pack(side="left")
        self.var_auto_wait = tk.StringVar(value="5")
        tk.Spinbox(auto_frm, from_=1, to=60, width=4,
                   textvariable=self.var_auto_wait,
                   font=("Courier New", 10, "bold"),
                   bg="#1a1a1a", fg="#00ffcc",
                   buttonbackground="#333", relief="flat").pack(side="left", padx=6)

        # Botão LARGAR
        self.btn_verde = self._btn(sema_sec, "LARGAR - VERDE",
                                    self._sema_go_green,
                                    bg="#004400", fg="#00ff66",
                                    width=26, state="disabled")
        self.btn_verde.pack(pady=(6, 2))

        self.lbl_sema_info = tk.Label(sema_sec, text="Seleciona um modo",
                                       font=("Courier New", 9),
                                       bg="#0d0d0d", fg="#444",
                                       wraplength=300, justify="center")
        self.lbl_sema_info.pack(pady=(2, 8))

        # Bandeira
        flag_sec = self._section(left, "BANDEIRA")
        flag_sec.pack(fill="x", pady=(0, 6))
        fr = tk.Frame(flag_sec, bg="#0d0d0d")
        fr.pack(padx=6, pady=6)
        flags = [("Verde",    "verde",    "#004411", "#00ff66"),
                 ("Vermelha", "vermelho", "#550000", "#ff4444"),
                 ("Amarela",  "amarelo",  "#554400", "#ffcc00"),
                 ("Azul",     "azul",     "#002255", "#4488ff")]
        for txt, val, bg, fg in flags:
            self._btn(fr, txt, lambda v=val: self._set_flag(v),
                      bg=bg, fg=fg, width=8).pack(side="left", padx=2)
        self._btn(flag_sec, "Sem Bandeira", self._clear_flag,
                  bg="#1a1a1a", fg="#555").pack(pady=(0, 6))

        # Sector
        sect_sec = self._section(left, "SECTOR")
        sect_sec.pack(fill="x", pady=(0, 6))
        sr = tk.Frame(sect_sec, bg="#0d0d0d")
        sr.pack(padx=6, pady=6)
        for s in ["S1", "S2", "S3"]:
            self._btn(sr, s, lambda v=s: self._set_sector(v),
                      bg="#1a1a2e", fg="#8888ff", width=7).pack(side="left", padx=3)
        self._btn(sr, "Todos", lambda: self._set_sector("none"),
                  bg="#111", fg="#444").pack(side="left", padx=3)

        self.lbl_status = tk.Label(left, text="PRONTO",
                                    font=("Courier New", 9, "bold"),
                                    bg="#0d0d0d", fg="#005500")
        self.lbl_status.pack(pady=4)

        # ══ DIREITA ══

        # Tempo de sessão
        time_sec = self._section(right, "TEMPO DE SESSAO")
        time_sec.pack(fill="x", pady=(0, 6))

        tf = tk.Frame(time_sec, bg="#0d0d0d")
        tf.pack(padx=8, pady=8)
        for col, (lbl, attr, mx, default) in enumerate([
                ("Horas", "var_h", 23, "0"),
                ("Min",   "var_m", 59, "30"),
                ("Seg",   "var_s", 59, "0")]):
            tk.Label(tf, text=lbl, font=("Courier New",9),
                     bg="#0d0d0d", fg="#555").grid(row=0, column=col*2, padx=(8,2))
            var = tk.StringVar(value=default)
            setattr(self, attr, var)
            tk.Spinbox(tf, from_=0, to=mx, width=4, textvariable=var,
                       font=("Courier New",10,"bold"),
                       bg="#1a1a1a", fg="#fff",
                       buttonbackground="#333", relief="flat").grid(row=0, column=col*2+1, padx=2)

        br = tk.Frame(time_sec, bg="#0d0d0d")
        br.pack(pady=(0, 8))
        self._btn(br, "INICIAR", self._start_timer,
                  bg="#004400", fg="#00ff88").pack(side="left", padx=3)
        self._btn(br, "PARAR",   self._stop_timer,
                  bg="#333",    fg="#aaa").pack(side="left", padx=3)
        self._btn(br, "FECHAR",  self._reset_timer,
                  bg="#330000", fg="#ff6666").pack(side="left", padx=3)

        # Display fase manual
        disp_sec = self._section(right, "ECRA DISPLAY")
        disp_sec.pack(fill="x", pady=(0, 6))
        dr = tk.Frame(disp_sec, bg="#0d0d0d")
        dr.pack(padx=6, pady=8)
        self._btn(dr, "Mostrar Semaforo", self._show_sema_phase,
                  bg="#220033", fg="#cc88ff").pack(side="left", padx=4)
        self._btn(dr, "Mostrar Corrida",  self._show_race_phase,
                  bg="#003322", fg="#00ffaa").pack(side="left", padx=4)

        # Pilotos
        pilot_sec = self._section(right, "PILOTOS")
        pilot_sec.pack(fill="x", pady=(0, 6))
        tk.Label(pilot_sec,
                 text="Integracao via socket (porta 9000)\ndados chegam da aplicacao externa",
                 font=("Courier New", 9), bg="#0d0d0d", fg="#444",
                 justify="center").pack(pady=6)
        self._btn(pilot_sec, "Carregar Dados Teste", self._test_pilots,
                  bg="#1a1a00", fg="#888800").pack(pady=(0, 8))

    # ═══ RESTART ════════════════════════════════════════

    def _do_restart(self):
        """Para tudo, limpa semáforo, volta ao ecrã de semáforo"""
        # Para sessão
        STATE.session_running = False
        STATE.session_time    = 0
        # Para semáforo
        self._sema_stop()
        # Volta ao ecrã de semáforo
        STATE.phase = "semaforo"
        STATE.notify()
        self.lbl_status.config(text="REINICIADO — PRONTO", fg="#ffaa00")

    # ═══ SEMÁFORO ═══════════════════════════════════════

    def _draw_mini(self):
        for i, c in enumerate(self.mini_cvs):
            c.delete("all")
            if STATE.sema_green:         col = "#00ff44"
            elif STATE.sema_lights[i]:   col = "#ff2200"
            else:                        col = "#1a0000"
            c.create_oval(2, 2, 32, 32, fill=col, outline="#222", width=1)

    def _update(self):
        self._draw_mini()
        STATE.notify()

    def _sema_stop(self):
        STATE.sema_running  = False
        self._waiting_green = False
        self._manual_lights = 0
        STATE.sema_mode     = "none"
        STATE.sema_lights   = [False]*5
        STATE.sema_green    = False
        self.btn_verde.config(state="disabled")
        self.lbl_sema_info.config(text="Parado")
        self._update()

    # ── verde → arranca cronómetro automaticamente ───────
    def _on_green(self):
        """Chamado quando o semáforo fica verde"""
        STATE.sema_lights = [False]*5
        STATE.sema_green  = True
        self._update()
        self.lbl_sema_info.config(text="GO!")
        # Arranca cronómetro de sessão automaticamente
        self._start_timer(auto=True)
        # Transição para ecrã de corrida após 2.5s
        def _transition():
            time.sleep(2.5)
            STATE.phase = "race"
            STATE.notify()
        threading.Thread(target=_transition, daemon=True).start()

    # ── AUTO ─────────────────────────────────────────────
    def _sema_auto(self):
        self._sema_stop()
        STATE.sema_mode    = "auto"
        STATE.sema_running = True
        try:
            wait_secs = max(1, int(self.var_auto_wait.get()))
        except:
            wait_secs = 5
        self.lbl_sema_info.config(
            text=f"AUTO: 1 luz/s -> espera {wait_secs}s -> verde")
        threading.Thread(target=self._run_auto,
                         args=(wait_secs,), daemon=True).start()

    def _run_auto(self, wait_secs):
        for i in range(5):
            if not STATE.sema_running: return
            STATE.sema_lights[i] = True
            self._update()
            self._sleep_i(1.0)

        remaining = wait_secs
        while remaining > 0 and STATE.sema_running:
            r = remaining
            self.root.after(0, lambda r=r: self.lbl_sema_info.config(
                text=f"Todas vermelhas - verde em {r}s..."))
            self._sleep_i(1.0)
            remaining -= 1

        if not STATE.sema_running: return
        self.root.after(0, self._on_green)

    # ── MANUAL ───────────────────────────────────────────
    def _sema_manual(self):
        self._sema_stop()
        STATE.sema_mode    = "manual"
        STATE.sema_running = True
        self._manual_lights = 0
        self._waiting_green = False
        self.lbl_sema_info.config(
            text="MANUAL: cada luz acende de 5 em 5s")
        threading.Thread(target=self._run_manual, daemon=True).start()

    def _run_manual(self):
        for i in range(5):
            if not STATE.sema_running: return
            countdown = 5
            while countdown > 0 and STATE.sema_running:
                n = i + 1
                c = countdown
                self.root.after(0, lambda n=n, c=c: self.lbl_sema_info.config(
                    text=f"MANUAL: luz {n}/5 acende em {c}s..."))
                self._sleep_i(1.0)
                countdown -= 1
            if not STATE.sema_running: return
            STATE.sema_lights[i] = True
            self._manual_lights  = i + 1
            self._update()

        if not STATE.sema_running: return
        self.root.after(0, lambda: self.lbl_sema_info.config(
            text="Todas acesas - clica LARGAR para largar!"))
        self.root.after(0, lambda: self.btn_verde.config(state="normal"))
        self._waiting_green = True

    def _sema_go_green(self):
        if not self._waiting_green: return
        self._waiting_green  = False
        STATE.sema_running   = False
        self.btn_verde.config(state="disabled")
        self._on_green()

    # ── GRELHA ───────────────────────────────────────────
    def _sema_grelha(self):
        self._sema_stop()
        STATE.sema_mode   = "grelha"
        STATE.sema_lights = [True]*5
        self.lbl_sema_info.config(text="GRELHA: todas vermelhas")
        self._update()

    def _sleep_i(self, seconds):
        steps = max(1, int(seconds / 0.1))
        for _ in range(steps):
            if not STATE.sema_running: return
            time.sleep(0.1)

    # ═══ DISPLAY FASE ═══════════════════════════════════

    def _show_sema_phase(self):
        STATE.phase = "semaforo"
        STATE.notify()

    def _show_race_phase(self):
        STATE.phase = "race"
        STATE.notify()

    # ═══ TIMER SESSÃO ════════════════════════════════════

    def _get_secs(self):
        try:
            return (int(self.var_h.get())*3600 +
                    int(self.var_m.get())*60  +
                    int(self.var_s.get()))
        except:
            return 0

    def _start_timer(self, auto=False):
        if STATE.session_running: return
        if STATE.session_time == 0:
            secs = self._get_secs()
            if secs == 0 and auto:
                return   # sem tempo definido, não arranca
            STATE.session_time = secs
        STATE.session_running = True
        threading.Thread(target=self._run_timer, daemon=True).start()
        if not auto:
            self.lbl_status.config(text="SESSAO A DECORRER", fg="#00cc44")

    def _run_timer(self):
        while STATE.session_running and STATE.session_time > 0:
            time.sleep(1)
            STATE.session_time = max(0, STATE.session_time - 1)
        if STATE.session_time == 0:
            STATE.session_running = False
            self.root.after(0, lambda: self.lbl_status.config(
                text="SESSAO TERMINADA", fg="#ff4444"))

    def _stop_timer(self):
        STATE.session_running = False
        self.lbl_status.config(text="PAUSADO", fg="#ffaa00")

    def _reset_timer(self):
        STATE.session_running = False
        STATE.session_time    = 0
        self.lbl_status.config(text="PRONTO", fg="#005500")

    # ═══ BANDEIRA / SECTOR ═══════════════════════════════

    def _set_flag(self, val):
        STATE.bandeira = val
        STATE.notify()

    def _clear_flag(self):
        STATE.bandeira = "none"
        STATE.notify()

    def _set_sector(self, val):
        STATE.sector = val
        STATE.notify()

    # ═══ JANELA DE TREINO ════════════════════════════════

    def _open_training(self):
        if self._training_win and self._training_win.winfo_exists():
            self._training_win.lift()
            return
        win = tk.Toplevel(self.root)
        win.geometry("800x400+300+200")
        TrainingWindow(win)
        self._training_win = win

    # ═══ PILOTOS TESTE ═══════════════════════════════════

    def _test_pilots(self):
        names = ["Hamilton", "Verstappen", "Leclerc", "Norris", "Alonso"]
        for i, p in enumerate(STATE.pilots):
            s  = random.uniform(70, 95)
            ms = random.randint(0, 999)
            p["nome"]      = names[i]
            p["tempo"]     = f"{int(s//60):02d}:{int(s%60):02d}.{ms:03d}"
            p["melhor"]    = f"{int(s//60):02d}:{int(s%60):02d}.{ms:03d}"
            p["volta"]     = random.randint(1, 20)
            p["diferenca"] = "LIDER" if i == 0 else f"+{random.uniform(0.1,9.9):.3f}"
        STATE.notify()


# ═══════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════
def main():
    root = tk.Tk()
    root.configure(bg="#0a0a0a")
    root.geometry("1280x720+0+0")

    display = DisplayWindow(root)

    ctrl_win = tk.Toplevel(root)
    ctrl_win.geometry("680x720+1290+0")
    control = ControlWindow(ctrl_win)

    def on_close():
        STATE.session_running = False
        STATE.sema_running    = False
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    ctrl_win.protocol("WM_DELETE_WINDOW", on_close)

    root.mainloop()

if __name__ == "__main__":
    main()
