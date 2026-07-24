import tkinter as tk

def fmt_time(secs):
    secs = max(0, int(secs))
    h = secs // 3600
    m = (secs % 3600) // 60
    s = secs % 60
    return f"{h:02d}:{m:02d}:{s:02d}"

class DisplayWindow:
    LIGHT_D = 110

    def __init__(self, root, state):
        self.root  = root
        self.state = state
        self.root.title("RACE DISPLAY")
        self.root.configure(bg="#0d0d0d")
        self.root.geometry("1280x720")
        self.root.resizable(True, True)

        self._build_semaforo_screen()
        self._build_race_screen()
        self._show_phase()
        self._tick()

    # ══════════════════════════════════════════
    #  ECRÃ 1 — SEMÁFORO
    # ══════════════════════════════════════════
    def _build_semaforo_screen(self):
        self.frame_sema = tk.Frame(self.root, bg="#0d0d0d")

        tk.Label(self.frame_sema, text="S E M A F O R O",
                 font=("Courier New", 16, "bold"),
                 bg="#0d0d0d", fg="#222").pack(pady=(40, 0))

        lights_row = tk.Frame(self.frame_sema, bg="#0d0d0d")
        lights_row.pack(expand=True)

        self.big_canvases = []
        for i in range(5):
            c = tk.Canvas(lights_row,
                          width=self.LIGHT_D + 20,
                          height=self.LIGHT_D + 20,
                          bg="#0d0d0d", highlightthickness=0)
            c.pack(side="left", padx=14)
            self.big_canvases.append(c)

        self.lbl_sema_big = tk.Label(self.frame_sema, text="",
                                     font=("Courier New", 20, "bold"),
                                     bg="#0d0d0d", fg="#555")
        self.lbl_sema_big.pack(pady=30)

    # ══════════════════════════════════════════
    #  ECRÃ 2 — CORRIDA (design Live Timing)
    # ══════════════════════════════════════════
    def _build_race_screen(self):
        self.frame_race = tk.Frame(self.root, bg="#0d0d0d")

        # ─── TABELA DE PILOTOS (topo) ───────────
        table_outer = tk.Frame(self.frame_race, bg="#0d0d0d")
        table_outer.pack(fill="x", padx=8, pady=(8, 4))

        # Cabeçalho
        hdr = tk.Frame(table_outer, bg="#111")
        hdr.pack(fill="x", pady=(0, 3))
        self.cols   = ["POS", "NO", "NOME", "ULTIMO", "V", "TOTAL", "DIFF"]
        self.widths = [4, 4, 16, 11, 4, 11, 10]
        for i, (h, w) in enumerate(zip(self.cols, self.widths)):
            tk.Label(hdr, text=h, font=("Courier New", 11, "bold"),
                     bg="#111", fg="#444", width=w,
                     anchor="center").grid(row=0, column=i, padx=1, pady=4, sticky="ew")
        for c in range(len(self.cols)):
            hdr.columnconfigure(c, weight=1)

        # Fundo onde as linhas vão ser renderizadas dinamicamente
        self.table_inner = tk.Frame(table_outer, bg="#0d0d0d")
        self.table_inner.pack(fill="x", expand=True)
        self.pilot_rows = []

        # ─── PAINEL INFERIOR (Bandeira + Timer) ──
        bottom = tk.Frame(self.frame_race, bg="#0d0d0d")
        bottom.pack(fill="both", expand=True, padx=8, pady=(4, 8))
        bottom.columnconfigure(0, weight=3)
        bottom.columnconfigure(1, weight=2)
        bottom.rowconfigure(0, weight=1)

        # Painel Esquerdo — Bandeira
        flag_f = tk.Frame(bottom, bg="#111", bd=0)
        flag_f.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        flag_f.rowconfigure(0, weight=1)
        flag_f.columnconfigure(0, weight=1)

        self.flag_canvas = tk.Canvas(flag_f, bg="#111",
                                     highlightthickness=0)
        self.flag_canvas.grid(row=0, column=0, sticky="nsew",
                              padx=16, pady=16)

        self.lbl_sector = tk.Label(flag_f, text="",
                                   font=("Courier New", 14, "bold"),
                                   bg="#111", fg="#ffcc00")
        self.lbl_sector.grid(row=1, column=0, pady=(0, 10))

        # Painel Direito — Cronómetro grande
        timer_f = tk.Frame(bottom, bg="#111")
        timer_f.grid(row=0, column=1, sticky="nsew", padx=(4, 0))
        self.lbl_time = tk.Label(timer_f, text="00:00:00",
                                 font=("Courier New", 58, "bold"),
                                 bg="#111", fg="#00ff44")
        self.lbl_time.pack(expand=True)

    # ══════════════════════════════════════════
    #  DESENHO DAS LUZES
    # ══════════════════════════════════════════
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
                             self.state.sema_lights[i], self.state.sema_green)

    # ══════════════════════════════════════════
    #  TROCA DE FASE
    # ══════════════════════════════════════════
    def _show_phase(self):
        if self.state.phase == "semaforo":
            self.frame_race.pack_forget()
            self.frame_sema.pack(fill="both", expand=True)
        else:
            self.frame_sema.pack_forget()
            self.frame_race.pack(fill="both", expand=True)

    # ══════════════════════════════════════════
    #  REFRESH — atualiza todos os widgets
    # ══════════════════════════════════════════
    def refresh(self):
        self._show_phase()
        self._draw_big_lights()

        # ── Label semáforo ──
        if self.state.sema_green:
            self.lbl_sema_big.config(text="GO!", fg="#00ff44",
                                     font=("Courier New", 48, "bold"))
        else:
            modes = {"auto": "AUTOMATICO", "manual": "MANUAL",
                     "grelha": "GRELHA", "none": ""}
            self.lbl_sema_big.config(
                text=modes.get(self.state.sema_mode, ""),
                fg="#444", font=("Courier New", 18, "bold"))

        # ── Pilotos (Criação dinâmica se nº de pilotos mudar) ──
        if len(self.state.pilots) != len(self.pilot_rows):
            # Limpa linhas antigas
            for row_data in self.pilot_rows:
                row_data["frame"].destroy()
            self.pilot_rows = []
            
            # Recria as linhas
            for r in range(len(self.state.pilots)):
                bg_row = "#141414" if r % 2 == 0 else "#111"
                row_f = tk.Frame(self.table_inner, bg=bg_row)
                row_f.pack(fill="x", pady=1)
                for c in range(len(self.cols)):
                    row_f.columnconfigure(c, weight=1)
                
                cells = []
                for c, w in enumerate(self.widths):
                    # Tamanho da fonte menor se houver muitos pilotos, para caber no ecrã
                    font_size = 17 if len(self.state.pilots) <= 8 else 13
                    lbl = tk.Label(row_f, text="", width=w,
                                   font=("Courier New", font_size, "bold"),
                                   bg=bg_row, fg="#e0e0e0",
                                   anchor="center", pady=4 if len(self.state.pilots) > 8 else 8)
                    lbl.grid(row=0, column=c, padx=1, sticky="ew")
                    cells.append(lbl)
                self.pilot_rows.append({"frame": row_f, "cells": cells})

        # Preenche dados dos pilotos
        for r, p in enumerate(self.state.pilots):
            vals = [
                str(p.get("pos", "")),
                str(p.get("no", "")),
                str(p.get("nome", "")),
                str(p.get("ultimo", "")),
                str(p.get("volta", "")),
                str(p.get("total", "")),
                str(p.get("diff", ""))
            ]
            for c, v in enumerate(vals):
                cell = self.pilot_rows[r]["cells"][c]
                # POS: cinza
                if c == 0:
                    cell.config(text=v, fg="#666")
                # ULTIMO do líder: verde brilhante
                elif c == 3 and p.get("pos") == 1:
                    cell.config(text=v, fg="#00ff44")
                # DIFF do líder
                elif c == 6 and p.get("pos") == 1:
                    cell.config(text=v, fg="#00ff44")
                else:
                    cell.config(text=v, fg="#e0e0e0")

        # ── Bandeira ──
        fc_map = {"none": "#111", "verde": "#003a0f", "vermelho": "#3a0000",
                  "amarelo": "#3a2800", "azul": "#00103a"}
        bar_map = {"none": "#111", "verde": "#00ff44", "vermelho": "#ff2200",
                   "amarelo": "#ffcc00", "azul": "#3388ff"}
        txt_map = {"none": "#111", "verde": "#0d0d0d", "vermelho": "#0d0d0d",
                   "amarelo": "#0d0d0d", "azul": "#0d0d0d"}

        fc  = fc_map.get(self.state.bandeira, "#111")
        bar = bar_map.get(self.state.bandeira, "#111")
        txt = txt_map.get(self.state.bandeira, "#fff")

        self.flag_canvas.delete("all")
        w = self.flag_canvas.winfo_width() or 400
        h = self.flag_canvas.winfo_height() or 100
        # Fundo
        self.flag_canvas.create_rectangle(0, 0, w, h, fill=fc, outline="")
        if self.state.bandeira != "none":
            # Barra cheia de cor
            pad = 12
            self.flag_canvas.create_rectangle(pad, pad, w-pad, h-pad,
                                              fill=bar, outline="")
            self.flag_canvas.create_text(w//2, h//2,
                text=self.state.bandeira.upper(),
                font=("Courier New", 28, "bold"), fill=txt)

        self.lbl_sector.config(
            text="" if self.state.sector == "none" else self.state.sector)

    # ══════════════════════════════════════════
    #  TICK — atualiza o cronómetro a cada 100ms
    # ══════════════════════════════════════════
    def _tick(self):
        self.lbl_time.config(text=fmt_time(self.state.session_time))
        self._draw_big_lights()
        self.root.after(100, self._tick)
