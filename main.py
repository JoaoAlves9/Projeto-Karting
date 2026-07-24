import queue
import threading

from core.state import AppState
from mylaps.listener import dummy_mylaps_listener
from web.server import run_server
from gui.app import run_gui

def main():
    print("=========================================")
    print(" KARTING DISPLAY SYSTEM - STARTING...")
    print("=========================================")
    
    # 1. A Fila Central e o Estado Global
    cmd_queue = queue.Queue()
    state = AppState()
    
    # [CORREÇÃO MAC OS] A janela Tkinter TEM de ser criada antes das Threads de rede!
    import tkinter as tk
    root = tk.Tk()
    
    # 2. Inicia a Thread do MYLAPS (Thread de Rede 1)
    # Corre em modo Daemon para que termine quando o Tkinter fechar
    t_mylaps = threading.Thread(target=dummy_mylaps_listener, args=(cmd_queue,), daemon=True)
    t_mylaps.start()
    
    # 3. Inicia a Thread do Servidor Flask (Thread de Rede 2)
    t_web = threading.Thread(target=run_server, args=(cmd_queue, state), daemon=True)
    t_web.start()
    
    # 4. Inicia a Interface Gráfica Tkinter (Thread Principal)
    # Passamos o 'root' criado antes para não congelar no macOS.
    run_gui(root, cmd_queue, state)

if __name__ == '__main__':
    main()
