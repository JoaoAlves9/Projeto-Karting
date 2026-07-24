import tkinter as tk
import threading
import time
import random

from gui.training import TrainingWindow

class ControlWindow:
    def __init__(self, root, state, cmd_queue):
        self.root       = root
        self.state      = state
        self.cmd_queue  = cmd_queue
        self.root.title("RACE CONTROL PANEL")
        self.root.configure(bg="#0d0d0d")
        self.root.geometry("680x720")
        self.root.resizable(False, False)
        self._manual_lights  = 0
        self._waiting_green  = False
        self._training_win   = None
        self._is_fullscreen  = False

        # Fullscreen: F11 activa, Escape sai
        self.root.bind('<F11>',  lambda e: self._toggle_fullscreen())
        self.root.bind('<Escape>', lambda e: self._exit_fullscreen())

        self._build()

    # ── helpers UI ───────────────────────────────────────
    def _section(self, parent, title, **kw):
        return tk.LabelFrame(parent, text=f"  {title}  ",
                             font=("Courier New",9,"bold"),
                             bg="#0d0d0d", fg="#555",
                             bd=1, relief="solid", labelanchor="nw", **kw)

    def _btn(self, parent, text, cmd, bg="#222", fg="#ddd", **kw):
        return tk.Button(parent, text=text, command=cmd,
                         font=("Courier New",10,"bold"),
                         bg=bg, fg=fg,
                         activebackground="#444", activeforeground="#fff",
                         relief="flat", bd=0, padx=8, pady=5,
                         cursor="hand2", **kw)

    # ── construção ──────────────────────────────────────
    def _build(self):
        header = tk.Frame(self.root, bg="#0d0d0d")
        header.pack(fill="x", padx=10, pady=(10,4))
        tk.Label(header, text="RACE CONTROL PANEL",
                 font=("Courier New",14,"bold"),
                 bg="#0d0d0d", fg="#cc1100").pack(side="left")
        self._btn(header, "↺  RESTART", self._do_restart,
                  bg="#440000", fg="#ff4444").pack(side="right", padx=4)
        self._btn(header, "⏱  TREINO", self._open_training,
                  bg="#001133", fg="#4488ff").pack(side="right", padx=4)
        self._btn(header, "⛶  FULLSCREEN", self._toggle_fullscreen,
                  bg="#1a1a1a", fg="#666").pack(side="right", padx=4)

        main = tk.Frame(self.root, bg="#0d0d0d")
        main.pack(fill="both", expand=True, padx=10, pady=2)
        main.columnconfigure(0, weight=1)
        main.columnconfigure(1, weight=1)
        left  = tk.Frame(main, bg="#0d0d0d")
        right = tk.Frame(main, bg="#0d0d0d")
        left.grid(row=0, column=0, sticky="nsew", padx=(0,4))
        right.grid(row=0, column=1, sticky="nsew", padx=(4,0))

        # ══ ESQUERDA: Semáforo ══
        sema_sec = self._section(left, "SEMAFORO")
        sema_sec.pack(fill="x", pady=(0,6))
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
        auto_frm = tk.Frame(sema_sec, bg="#0d0d0d")
        auto_frm.pack(pady=4)
        tk.Label(auto_frm, text="Tempo ate verde (seg):",
                 font=("Courier New",9), bg="#0d0d0d", fg="#555").pack(side="left")
        self.var_auto_wait = tk.StringVar(value="5")
        tk.Spinbox(auto_frm, from_=1, to=60, width=4,
                   textvariable=self.var_auto_wait,
                   font=("Courier New",10,"bold"),
                   bg="#1a1a1a", fg="#00ffcc",
                   buttonbackground="#333", relief="flat").pack(side="left", padx=6)
        self.btn_verde = self._btn(sema_sec, "LARGAR - VERDE",
                                   self._sema_go_green,
                                   bg="#004400", fg="#00ff66",
                                   width=26, state="disabled")
        self.btn_verde.pack(pady=(6,2))
        self.lbl_sema_info = tk.Label(sema_sec, text="Seleciona um modo",
                                      font=("Courier New",9),
                                      bg="#0d0d0d", fg="#444",
                                      wraplength=300, justify="center")
        self.lbl_sema_info.pack(pady=(2,8))

        # Bandeira
        flag_sec = self._section(left, "BANDEIRA")
        flag_sec.pack(fill="x", pady=(0,6))
        fr = tk.Frame(flag_sec, bg="#0d0d0d")
        fr.pack(padx=6, pady=6)
        flags = [("Verde","verde","#004411","#00ff66"),
                 ("Vermelha","vermelho","#550000","#ff4444"),
                 ("Amarela","amarelo","#554400","#ffcc00"),
                 ("Azul","azul","#002255","#4488ff")]
        for txt, val, bg, fg in flags:
            self._btn(fr, txt, lambda v=val: self._set_flag(v),
                      bg=bg, fg=fg, width=8).pack(side="left", padx=2)
        self._btn(flag_sec, "Sem Bandeira", self._clear_flag,
                  bg="#1a1a1a", fg="#555").pack(pady=(0,6))

        # Sector
        sect_sec = self._section(left, "SECTOR")
        sect_sec.pack(fill="x", pady=(0,6))
        sr = tk.Frame(sect_sec, bg="#0d0d0d")
        sr.pack(padx=6, pady=6)
        for s in ["S1","S2","S3"]:
            self._btn(sr, s, lambda v=s: self._set_sector(v),
                      bg="#1a1a2e", fg="#8888ff", width=7).pack(side="left", padx=3)
        self._btn(sr, "Todos", lambda: self._set_sector("none"),
                  bg="#111", fg="#444").pack(side="left", padx=3)
        self.lbl_status = tk.Label(left, text="PRONTO",
                                    font=("Courier New",9,"bold"),
                                    bg="#0d0d0d", fg="#005500")
        self.lbl_status.pack(pady=4)

        # ══ DIREITA: Tempo de sessão ══
        time_sec = self._section(right, "TEMPO DE SESSAO")
        time_sec.pack(fill="x", pady=(0,6))
        tf = tk.Frame(time_sec, bg="#0d0d0d")
        tf.pack(padx=8, pady=8)
        for col, (lbl, attr, mx, default) in enumerate([
                ("Horas","var_h",23,"0"),
                ("Min",  "var_m",59,"30"),
                ("Seg",  "var_s",59,"0")]):
            tk.Label(tf, text=lbl, font=("Courier New",9),
                     bg="#0d0d0d", fg="#555").grid(row=0, column=col*2, padx=(8,2))
            var = tk.StringVar(value=default)
            setattr(self, attr, var)
            tk.Spinbox(tf, from_=0, to=mx, width=4, textvariable=var,
                       font=("Courier New",10,"bold"),
                       bg="#1a1a1a", fg="#fff",
                       buttonbackground="#333", relief="flat").grid(row=0, column=col*2+1, padx=2)
        br = tk.Frame(time_sec, bg="#0d0d0d")
        br.pack(pady=(0,8))
        self._btn(br, "INICIAR", self._start_timer,
                  bg="#004400", fg="#00ff88").pack(side="left", padx=3)
        self._btn(br, "PARAR",   self._stop_timer,
                  bg="#333",    fg="#aaa").pack(side="left", padx=3)
        self._btn(br, "FECHAR",  self._reset_timer,
                  bg="#330000", fg="#ff6666").pack(side="left", padx=3)

        # Ecrã Display
        disp_sec = self._section(right, "ECRA DISPLAY")
        disp_sec.pack(fill="x", pady=(0,6))
        dr = tk.Frame(disp_sec, bg="#0d0d0d")
        dr.pack(padx=6, pady=8)
        self._btn(dr, "Mostrar Semaforo", self._show_sema_phase,
                  bg="#220033", fg="#cc88ff").pack(side="left", padx=4)
        self._btn(dr, "Mostrar Corrida",  self._show_race_phase,
                  bg="#003322", fg="#00ffaa").pack(side="left", padx=4)

        # Pilotos
        pilot_sec = self._section(right, "PILOTOS")
        pilot_sec.pack(fill="x", pady=(0,6))
        tk.Label(pilot_sec,
                 text="Integracao via socket (porta 9000)\ndados chegam da aplicacao externa",
                 font=("Courier New",9), bg="#0d0d0d", fg="#444",
                 justify="center").pack(pady=6)
        self._btn(pilot_sec, "Carregar Dados Teste", self._test_pilots,
                  bg="#1a1a00", fg="#888800").pack(pady=(0,8))

    # ═══ FULLSCREEN ═══════════════════════════════════════
    def _toggle_fullscreen(self):
        self._is_fullscreen = not self._is_fullscreen
        self.root.attributes('-fullscreen', self._is_fullscreen)

    def _exit_fullscreen(self):
        if self._is_fullscreen:
            self._is_fullscreen = False
            self.root.attributes('-fullscreen', False)

    # ═══ NOTIFY (atualiza display) ═══════════════════════
    def _notify(self):
        """Coloca mensagem de REFRESH na queue para o GUI processar."""
        self.cmd_queue.put({"type": "REFRESH"})

    # ═══ RESTART ═════════════════════════════════════════
    def _do_restart(self):
        self.state.session_running = False
        self.state.session_time    = 0
        self._sema_stop()
        self.state.phase = "semaforo"
        self._notify()
        self.lbl_status.config(text="REINICIADO — PRONTO", fg="#ffaa00")

    # ═══ SEMÁFORO ════════════════════════════════════════
    def _draw_mini(self):
        for i, c in enumerate(self.mini_cvs):
            c.delete("all")
            if self.state.sema_green:       col = "#00ff44"
            elif self.state.sema_lights[i]: col = "#ff2200"
            else:                           col = "#1a0000"
            c.create_oval(2,2,32,32, fill=col, outline="#222", width=1)

    def _update(self):
        self._draw_mini()
        self._notify()

    def _sema_stop(self):
        self.state.sema_running      = False
        self._waiting_green          = False
        self.state.sema_waiting_green = False
        self._manual_lights          = 0
        self.state.sema_mode     = "none"
        self.state.sema_lights   = [False]*5
        self.state.sema_green    = False
        self.btn_verde.config(state="disabled")
        self.lbl_sema_info.config(text="Parado")
        self._update()

    def _on_green(self):
        self.state.sema_lights = [False]*5
        self.state.sema_green  = True
        self._update()
        self.lbl_sema_info.config(text="GO!")
        self._start_timer(auto=True)
        def _transition():
            time.sleep(2.5)
            self.state.phase = "race"
            self._notify()
        threading.Thread(target=_transition, daemon=True).start()

    def _sema_auto(self):
        self._sema_stop()
        self.state.sema_mode    = "auto"
        self.state.sema_running = True
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
            if not self.state.sema_running: return
            self.state.sema_lights[i] = True
            self._update()
            self._sleep_i(1.0)
        remaining = wait_secs
        while remaining > 0 and self.state.sema_running:
            r = remaining
            self.root.after(0, lambda r=r: self.lbl_sema_info.config(
                text=f"Todas vermelhas - verde em {r}s..."))
            self._sleep_i(1.0)
            remaining -= 1
        if not self.state.sema_running: return
        self.root.after(0, self._on_green)

    def _sema_manual(self):
        self._sema_stop()
        self.state.sema_mode    = "manual"
        self.state.sema_running = True
        self._manual_lights     = 0
        self._waiting_green     = False
        self.lbl_sema_info.config(text="MANUAL: cada luz acende de 5 em 5s")
        threading.Thread(target=self._run_manual, daemon=True).start()

    def _run_manual(self):
        for i in range(5):
            if not self.state.sema_running: return
            countdown = 5
            while countdown > 0 and self.state.sema_running:
                n = i+1; c = countdown
                self.root.after(0, lambda n=n, c=c: self.lbl_sema_info.config(
                    text=f"MANUAL: luz {n}/5 acende em {c}s..."))
                self._sleep_i(1.0)
                countdown -= 1
            if not self.state.sema_running: return
            self.state.sema_lights[i] = True
            self._manual_lights = i+1
            self._update()
        if not self.state.sema_running: return
        self.root.after(0, lambda: self.lbl_sema_info.config(
            text="Todas acesas - clica LARGAR para largar!"))
        self.root.after(0, lambda: self.btn_verde.config(state="normal"))
        self._waiting_green           = True
        self.state.sema_waiting_green = True

    def _sema_go_green(self):
        if not self._waiting_green: return
        self._waiting_green           = False
        self.state.sema_waiting_green = False
        self.state.sema_running       = False
        self.btn_verde.config(state="disabled")
        self._on_green()

    def _sema_grelha(self):
        self._sema_stop()
        self.state.sema_mode   = "grelha"
        self.state.sema_lights = [True]*5
        self.lbl_sema_info.config(text="GRELHA: todas vermelhas")
        self._update()

    def _sleep_i(self, seconds):
        steps = max(1, int(seconds / 0.1))
        for _ in range(steps):
            if not self.state.sema_running: return
            time.sleep(0.1)

    # ═══ DISPLAY FASE ════════════════════════════════════
    def _show_sema_phase(self):
        self.state.phase = "semaforo"
        self._notify()

    def _show_race_phase(self):
        self.state.phase = "race"
        self._notify()

    # ═══ TIMER SESSÃO ════════════════════════════════════
    def _get_secs(self):
        try:
            return (int(self.var_h.get())*3600 +
                    int(self.var_m.get())*60  +
                    int(self.var_s.get()))
        except:
            return 0

    def _start_timer(self, auto=False):
        if self.state.session_running: return
        if self.state.session_time == 0:
            secs = self._get_secs()
            if secs == 0 and auto: return
            self.state.session_time = secs
        self.state.session_running = True
        threading.Thread(target=self._run_timer, daemon=True).start()
        if not auto:
            self.lbl_status.config(text="SESSAO A DECORRER", fg="#00cc44")

    def _run_timer(self):
        while self.state.session_running and self.state.session_time > 0:
            time.sleep(1)
            self.state.session_time = max(0, self.state.session_time - 1)
        if self.state.session_time == 0:
            self.state.session_running = False
            self.root.after(0, lambda: self.lbl_status.config(
                text="SESSAO TERMINADA", fg="#ff4444"))

    def _stop_timer(self):
        self.state.session_running = False
        self.lbl_status.config(text="PAUSADO", fg="#ffaa00")

    def _reset_timer(self):
        self.state.session_running = False
        self.state.session_time    = 0
        self.lbl_status.config(text="PRONTO", fg="#005500")

    # ═══ BANDEIRA / SECTOR ═══════════════════════════════
    def _set_flag(self, val):
        self.state.bandeira = val
        self._notify()

    def _clear_flag(self):
        self.state.bandeira = "none"
        self._notify()

    def _set_sector(self, val):
        self.state.sector = val
        self._notify()

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
        names = ["Hamilton","Verstappen","Leclerc","Norris","Alonso"]
        for i, p in enumerate(self.state.pilots):
            s  = random.uniform(70, 95)
            ms = random.randint(0, 999)
            p["nome"]      = names[i]
            p["tempo"]     = f"{int(s//60):02d}:{int(s%60):02d}.{ms:03d}"
            p["melhor"]    = f"{int(s//60):02d}:{int(s%60):02d}.{ms:03d}"
            p["volta"]     = random.randint(1, 20)
            p["diferenca"] = "LIDER" if i == 0 else f"+{random.uniform(0.1,9.9):.3f}"
        self._notify()
