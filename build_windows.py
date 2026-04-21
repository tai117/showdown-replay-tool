#!/usr/bin/env python3
"""
Script de construcción para generar el ejecutable de Windows (.exe).
⚠️ DEBE EJECUTARSE EN WINDOWS (nativo o VM).
"""
import os
import sys
import subprocess
import shutil
from pathlib import Path

def check_windows():
    if os.name != 'nt':
        print("❌ ERROR: Este script solo funciona en Windows.")
        print("💡 Alternativa: Usa el workflow de GitHub Actions ya configurado en tu repo.")
        sys.exit(1)

def install_deps():
    print("📦 Preparando entorno de build...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
    # Instala el proyecto para que PyInstaller resuelva correctamente las dependencias
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-e", "."], 
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def build_exe():
    print("🔨 Construyendo ejecutable con PyInstaller...")
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--name", "showdown-replay-tool",
        "--clean",
        "--noconfirm",
        "--paths", ".",
        # Hidden imports para carga dinámica y submódulos
        "--hidden-import", "src",
        "--hidden-import", "src.cli",
        "--hidden-import", "src.orchestrator",
        "--hidden-import", "src.config_loader",
        "--hidden-import", "src.http_client",
        "--hidden-import", "src.replay_paginator",
        "--hidden-import", "src.replay_storage",
        "--hidden-import", "src.replay_parser",
        "--hidden-import", "src.state_manager",
        "--hidden-import", "src.metagame_analyzer",
        "--hidden-import", "src.visualizer",
        "src/cli.py"  # Punto de entrada principal
    ]
    
    if Path("assets/icon.ico").exists():
        cmd.extend(["--icon", "assets/icon.ico"])
        
    subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("✅ Build completado. Ejecutable en: dist/showdown-replay-tool.exe")

def package_for_distribution():
    """Crea un ZIP listo para distribuir con el .exe y la carpeta config."""
    dist_dir = Path("dist")
    release_dir = Path("release/windows")
    release_dir.mkdir(parents=True, exist_ok=True)

    exe_path = dist_dir / "showdown-replay-tool.exe"
    if not exe_path.exists():
        print("⚠️ Ejecutable no encontrado. Ejecuta el build primero.")
        return

    print("📦 Empaquetando para distribución...")
    shutil.copy2(exe_path, release_dir)

    if Path("config").exists():
        shutil.copytree("config", release_dir / "config", dirs_exist_ok=True)
    if Path("README.md").exists():
        shutil.copy2("README.md", release_dir)

    print(f"✅ Paquete listo en: {release_dir}/")
    print("💡 Instrucciones: Extrae y ejecuta `showdown-replay-tool.exe` manteniendo la carpeta `config/` al mismo nivel.")

def main():
    print("🚀 Iniciando proceso de build para Windows...")
    check_windows()
    install_deps()
    build_exe()
    package_for_distribution()
    print("🎉 ¡Proceso finalizado con éxito!")

if __name__ == "__main__":
    main()
