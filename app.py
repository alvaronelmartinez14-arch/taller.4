import time
import random
import threading
from flask import Flask, render_template
from flask_socketio import SocketIO, emit

app = Flask(__name__)
# Importante: async_mode='threading' asegura que los hilos de Python manejen bien los eventos
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Recursos compartidos sincronizados
pasillo_semaforo = threading.Semaphore(2)
estacion_carga_lock = threading.Lock()

def enviar_log(mensaje, tipo="info"):
    socketio.emit('log_evento', {'mensaje': mensaje, 'tipo': tipo})

def actualizar_estado(id_montacargas, estado, recurso="ninguno"):
    socketio.emit('estado_montacargas', {
        'id': id_montacargas,
        'estado': estado,
        'recurso': recurso
    })

def tarea_montacargas(id_montacargas):
    try:
        # 1. Iniciando
        actualizar_estado(id_montacargas, "Iniciando", "espera")
        enviar_log(f"[Iniciado] Montacargas {id_montacargas} listo para operar.", "info")
        time.sleep(random.uniform(1.0, 2.0))
        
        # --- MECANISMO 1: SEMÁFORO (Pasillo Estrecho) ---
        actualizar_estado(id_montacargas, "Esperando pasillo", "pasillo")
        enviar_log(f"Aviso: Montacargas {id_montacargas} solicitando acceso al pasillo estrecho.", "warning")
        
        with pasillo_semaforo:
            actualizar_estado(id_montacargas, "En pasillo", "pasillo")
            enviar_log(f"Acceso concedido: Montacargas {id_montacargas} ingresó al pasillo estrecho.", "success")
            time.sleep(random.uniform(3.0, 4.0)) # Transitando por el pasillo
            enviar_log(f"Libre: Montacargas {id_montacargas} salió del pasillo estrecho.", "info")

        # Operación intermedia fuera de zona crítica
        actualizar_estado(id_montacargas, "Trabajando en patio", "patio")
        time.sleep(random.uniform(1.5, 2.5))

        # --- MECANISMO 2: LOCK / MUTEX (Estación de Carga Exclusiva) ---
        actualizar_estado(id_montacargas, "Esperando cargador", "carga")
        enviar_log(f"Aviso: Montacargas {id_montacargas} solicitando la estación de carga.", "warning")
        
        with estacion_carga_lock:
            actualizar_estado(id_montacargas, "Cargando bateria", "carga")
            enviar_log(f"Exclusion Mutua: Montacargas {id_montacargas} conectando a la estacion de carga.", "success")
            time.sleep(random.uniform(3.0, 5.0)) # Recargando
            enviar_log(f"Completado: Montacargas {id_montacargas} termino de cargar y libero la estacion.", "info")

        # 4. Finalizado
        actualizar_estado(id_montacargas, "Finalizado", "libre")
        enviar_log(f"Final: Montacargas {id_montacargas} completo su ciclo operativo con exito.", "success")

    except Exception as e:
        print(f"Error en hilo {id_montacargas}: {e}")

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('iniciar_simulacion')
def handle_simulation():
    enviar_log("--- INICIO DE OPERACIONES: Multiprogramacion de hilos activa ---", "info")
    
    # Lanzar 4 hilos concurrentes de forma segura
    for i in range(1, 5):
        hilo = threading.Thread(target=tarea_montacargas, args=(i,))
        hilo.daemon = True
        hilo.start()

if __name__ == '__main__':
    socketio.run(app, debug=True, port=5000)