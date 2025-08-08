#!/usr/bin/env python3
"""
Status Check Simples
"""

import sys
sys.path.append('.')

from src.utils.config import Config
from datetime import datetime
import psutil
from pathlib import Path

def simple_status_check():
    """Status check simples sem emojis"""
    print("=== FORCE ONE IT SYSTEM STATUS ===")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # System resources
    print("SISTEMA:")
    print(f"   CPU: {psutil.cpu_percent():.1f}%")
    print(f"   Memoria: {psutil.virtual_memory().percent:.1f}%")
    print(f"   Disco: {psutil.disk_usage('.').percent:.1f}%")
    print()
    
    # API Configuration
    print("APIS CONFIGURADAS:")
    google_configured = bool(Config.GOOGLE_MAPS_API_KEY and 
                           Config.GOOGLE_MAPS_API_KEY != "your_google_maps_api_key_here")
    hubspot_configured = bool(Config.HUBSPOT_API_KEY and 
                            Config.HUBSPOT_API_KEY != "your_hubspot_private_app_key_here")
    linkedin_configured = bool(Config.LINKEDIN_USERNAME and Config.LINKEDIN_PASSWORD)
    
    print(f"   Google Maps: {'SIM' if google_configured else 'NAO'}")
    print(f"   HubSpot: {'SIM' if hubspot_configured else 'NAO'}")
    print(f"   LinkedIn: {'SIM' if linkedin_configured else 'NAO'}")
    print()
    
    # Directories
    print("DIRETORIOS:")
    dirs = {
        "data": Config.DATA_DIR,
        "cache": Config.CACHE_DIR, 
        "exports": Config.EXPORTS_DIR,
        "logs": Config.LOGS_DIR
    }
    
    for name, path in dirs.items():
        exists = path.exists()
        count = len(list(path.glob("*"))) if exists else 0
        print(f"   {name}: {'OK' if exists else 'FALTANDO'} ({count} arquivos)")
    print()
    
    # Overall Status
    configured_apis = sum([google_configured, hubspot_configured])
    
    if configured_apis >= 2:
        status = "OTIMO - Todas APIs configuradas"
    elif configured_apis == 1:
        status = "BOM - API principal configurada"
    else:
        status = "PRECISA CONFIGURACAO - Faltam APIs"
    
    print(f"STATUS GERAL: {status}")
    print()
    
    # Next steps
    if not google_configured:
        print("PROXIMO PASSO: Configure GOOGLE_MAPS_API_KEY no .env")
    elif not hubspot_configured:
        print("RECOMENDADO: Configure HUBSPOT_API_KEY para sync CRM")
    else:
        print("SISTEMA PRONTO PARA USO!")
    
    return configured_apis >= 1

if __name__ == "__main__":
    success = simple_status_check()
    sys.exit(0 if success else 1)