import tkinter as tk

from gui.display import DisplayWindow
from gui.control import ControlWindow

def run_gui(root, cmd_queue, state):
    """
    Coordena as duas janelas (Display + Controlo) e processa
    a Fila Central a cada 100ms para manter o ecrã atualizado.
    """
    # ── Janela 1: Ecrã Gigante (root já criado no main.py) ──
    root.configure(bg="#0a0a0a")
    root.geometry("1280x720+0+0")
    display = DisplayWindow(root, state)

    # ── Janela 2: Painel de Controlo (janela separada) ──
    ctrl_win = tk.Toplevel(root)
    ctrl_win.geometry("680x720+1290+0")
    control = ControlWindow(ctrl_win, state, cmd_queue)

    # ── Leitura da Fila Central (100ms) ──
    def process_queue():
        while not cmd_queue.empty():
            msg = cmd_queue.get_nowait()
            t   = msg.get("type")

            if t == "MYLAPS_UPDATE":
                with state.lock:
                    state.pilots = msg["data"]

            elif t == "WEB_CMD":
                cmd = msg.get("cmd")
                val = msg.get("val")

                # ── Bandeira / Fase ──
                if cmd == "FLAG":
                    with state.lock:
                        state.bandeira = val
                elif cmd == "PHASE":
                    with state.lock:
                        state.phase = val

                # ── Semáforo ──
                elif cmd == "SEMA_STOP":
                    control._sema_stop()
                elif cmd == "SEMA_GRELHA":
                    control._sema_grelha()
                elif cmd == "SEMA_GO_GREEN":
                    control._sema_go_green()
                elif cmd == "SEMA_AUTO":
                    try:
                        control.var_auto_wait.set(str(int(val)))
                    except:
                        pass
                    control._sema_auto()
                elif cmd == "SEMA_MANUAL":
                    control._sema_manual()

                # ── Timer de sessão ──
                elif cmd == "TIMER_SET":
                    if isinstance(val, dict):
                        try:
                            control.var_h.set(str(val.get("h", 0)))
                            control.var_m.set(str(val.get("m", 0)))
                            control.var_s.set(str(val.get("s", 0)))
                        except:
                            pass
                elif cmd == "TIMER_START":
                    control._start_timer()
                elif cmd == "TIMER_STOP":
                    control._stop_timer()
                elif cmd == "TIMER_RESET":
                    control._reset_timer()

                # ── Sector ──
                elif cmd == "SECTOR":
                    with state.lock:
                        state.sector = val if val else "none"

                # ── Pilotos de Teste ──
                elif cmd == "TEST_PILOTS":
                    control._test_pilots()

                # ── Restart geral ──
                elif cmd == "RESTART":
                    control._do_restart()

            # Atualiza o ecrã gigante com o estado atual
            display.refresh()

        root.after(100, process_queue)

    # ── Encerramento limpo ──
    def on_close():
        state.session_running = False
        state.sema_running    = False
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    ctrl_win.protocol("WM_DELETE_WINDOW", on_close)

    # Arranca o ciclo
    root.after(100, process_queue)

    print("[GUI] Interface Gráfica iniciada.")
    root.mainloop()
