import time
import random
import socket
import threading
import re

# ====================================================================
# CONFIGURAÇÕES DO ORBIT
# ====================================================================
ORBIT_IP = "192.168.1.115"  # <-- METE AQUI O IP DO ORBIT
ORBIT_PORT = 50000          # <-- METE AQUI A PORTA DO ORBIT
# ====================================================================

def dummy_mylaps_listener(cmd_queue):
    """
    Liga-se por TCP ao MYLAPS Orbits.
    Faz o parsing dinâmico dos dados baseados na estrutura:
    Pos,No.,Nome,Classe;Ultimo Tm,Voltas,Total Tempo,Diff;Espaço
    """
    print(f"[MYLAPS] A tentar ligar ao Orbit em {ORBIT_IP}:{ORBIT_PORT}...")
    
    # Dicionário partilhado para guardar os pilotos (chave = pos)
    orbit_pilots = {}
    
    def orbit_socket_thread():
        nonlocal orbit_pilots
        buffer = ""
        while True:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(5.0)
                    s.connect((ORBIT_IP, ORBIT_PORT))
                    print("[MYLAPS] LIGADO COM SUCESSO AO ORBIT! A escutar dados...")
                    
                    while True:
                        data_bytes = s.recv(4096)
                        if not data_bytes:
                            break
                        
                        buffer += data_bytes.decode('utf-8', errors='ignore')
                        
                        # Processar linha a linha
                        while '\n' in buffer:
                            line, buffer = buffer.split('\n', 1)
                            line = line.strip()
                            if not line:
                                continue
                                
                            # Imprime para o terminal para debug (pode comentar depois)
                            print(f"[ORBIT_RAW] {line}")
                            
                            # Faz o parsing com base nos separadores "," e ";"
                            # Esperado: Pos,No.,Nome,Classe;Ultimo Tm,Voltas,Total Tempo,Diff;Espaço
                            parts = re.split(r'[,;]', line)
                            
                            if len(parts) >= 8:
                                try:
                                    # Valida se a primeira coluna é efetivamente a posição (número)
                                    pos = int(parts[0].strip())
                                    no = parts[1].strip()
                                    nome = parts[2].strip()
                                    # parts[3] é classe (ignoramos)
                                    ultimo = parts[4].strip()
                                    voltas = parts[5].strip()
                                    total = parts[6].strip()
                                    diff = parts[7].strip()
                                    
                                    # Guarda ou atualiza o piloto no dicionário
                                    orbit_pilots[pos] = {
                                        "pos": pos,
                                        "no": no,
                                        "nome": nome,
                                        "ultimo": ultimo,
                                        "volta": voltas,
                                        "total": total,
                                        "diff": diff
                                    }
                                except ValueError:
                                    # Se a posição não for um número (ex: cabeçalhos), ignora a linha
                                    pass
                                    
            except Exception as e:
                print(f"[MYLAPS] Aviso: Não foi possível ligar ao Orbit ({e}). A tentar novamente em 5s...")
            time.sleep(5)
            
    # Inicia a thread de escuta do socket
    t_sock = threading.Thread(target=orbit_socket_thread, daemon=True)
    t_sock.start()

    # Loop principal para atualizar os ecrãs
    # Envia o estado atual dos pilotos para a fila a cada 1 segundo
    while True:
        time.sleep(1)
        
        # Converte o dicionário numa lista ordenada pela posição
        pilots_data = [orbit_pilots[p] for p in sorted(orbit_pilots.keys())]
        
        cmd_queue.put({
            "type": "MYLAPS_UPDATE",
            "data": pilots_data
        })
