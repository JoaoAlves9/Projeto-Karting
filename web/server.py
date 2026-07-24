import logging
from flask import Flask, render_template, request, jsonify, session, redirect, url_for

def run_server(cmd_queue, state):
    app = Flask(__name__)
    app.secret_key = 'super_secret_key_karting' # Necessário para a sessão (Login PIN)
    
    # Desativa logs excessivos do Flask na consola para não sujar o terminal
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    
    ADMIN_PIN = "1234"
    
    @app.route('/live')
    def live():
        # Rota pública acessível pelo Wi-Fi para espectadores
        return render_template("live.html")
        
    @app.route('/api/state')
    def api_state():
        # Rota para o JS da página /live ir buscar os dados atuais em JSON
        return jsonify(state.get_dict())
        
    @app.route('/admin', methods=['GET', 'POST'])
    def admin():
        # Rota protegida com um PIN simples
        if request.method == 'POST':
            pin = request.form.get("pin", "")
            if pin == ADMIN_PIN:
                session['is_admin'] = True
                return redirect(url_for('admin'))
            else:
                return "PIN Inválido. <a href='/admin'>Tentar Novamente</a>", 401
                
        if not session.get('is_admin'):
            # Ecrã de Login simples
            return '''
            <div style="font-family:sans-serif; text-align:center; margin-top:50px;">
                <h2>Admin Login</h2>
                <form method="POST">
                    <input type="password" name="pin" placeholder="PIN (1234)" autofocus style="padding:10px; font-size:16px;">
                    <button type="submit" style="padding:10px 20px; font-size:16px;">Entrar</button>
                </form>
            </div>
            '''
            
        # Se chegou aqui, já fez login
        return render_template("admin.html")
        
    @app.route('/api/command', methods=['POST'])
    def api_command():
        # Rota para o painel de admin enviar comandos para a Fila Central
        if not session.get('is_admin'):
            return jsonify({"status": "error", "msg": "Não autorizado"}), 403
            
        data = request.json
        cmd = data.get("cmd")
        val = data.get("val")
        
        if cmd:
            cmd_queue.put({"type": "WEB_CMD", "cmd": cmd, "val": val})
            
        return jsonify({"status": "ok"})
        
    print("[FLASK] Servidor iniciado. Acessível em http://localhost:5000/live e /admin")
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
