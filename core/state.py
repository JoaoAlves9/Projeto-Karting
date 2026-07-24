import threading

class AppState:
    def __init__(self):
        self.lock = threading.Lock()
        
        # Semáforo
        self.sema_mode    = "none"      # none | auto | manual | grelha
        self.sema_lights  = [False]*5
        self.sema_green         = False
        self.sema_running       = False   # usado pelas threads de semáforo
        self.sema_waiting_green = False   # TRUE quando MANUAL acabou e espera LARGAR
        
        # Fase do ecrã
        self.phase = "semaforo"         # semaforo | race
        
        # Bandeira e Sector
        self.bandeira = "none"          # none | verde | vermelho | amarelo | azul
        self.sector = "none"
        
        # Tempo da sessão
        self.session_time = 0
        self.session_running = False
        
        # Dados dos pilotos
        self.pilots = []
        
    def get_dict(self):
        """Retorna uma cópia thread-safe do estado atual para enviar ao Flask/Web."""
        with self.lock:
            return {
                "sema_mode":           self.sema_mode,
                "sema_lights":         list(self.sema_lights),
                "sema_green":          self.sema_green,
                "sema_waiting_green":  self.sema_waiting_green,
                "phase":               self.phase,
                "bandeira":            self.bandeira,
                "sector":              self.sector,
                "session_time":        self.session_time,
                "session_running":     self.session_running,
                "pilots":              list(self.pilots)
            }
