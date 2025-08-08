#!/usr/bin/env python3
"""
Quick Start - Force One IT Lead Extractor
"""

import subprocess
import sys
from pathlib import Path

def run_command(command, description):
    print(f"Executando: {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True)
        print(f"{description} - OK")
        return True
    except subprocess.CalledProcessError as e:
        print(f"{description} - ERRO: {e}")
        return False

def quick_start():
    print("=== FORCE ONE IT LEAD EXTRACTOR - QUICK START ===")
    print()
    
    # Check Python
    print(f"Python version: {sys.version}")
    
    # Check if dependencies are installed
    try:
        import pandas, requests, click
        print("✅ Dependências instaladas")
    except ImportError:
        print("❌ Instalando dependências...")
        if not run_command("python -m pip install -r requirements.txt", "Install dependencies"):
            return False
    
    # Check .env
    env_file = Path('.env')
    if not env_file.exists():
        print("❌ Arquivo .env não encontrado")
        print("   1. Copie: cp .env.example .env")
        print("   2. Configure sua Google Maps API key")
        return False
    else:
        print("✅ Arquivo .env encontrado")
    
    # Test system
    print("\nTestando sistema...")
    success = run_command("python status_check.py", "Status check")
    
    if success:
        print("\n🎉 Sistema pronto!")
        print("\nPróximos comandos:")
        print("  python leadextractor.py extract --sector technology --limit 5")
        print("  python leadextractor.py pipeline --sector banking --limit 10")
        print("  python leadextractor.py start-api")
    else:
        print("\n⚠️  Configure APIs no arquivo .env primeiro")
    
    return success

if __name__ == "__main__":
    quick_start()
