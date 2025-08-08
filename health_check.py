#!/usr/bin/env python3
"""
Health Check Direto - Sem Menu Interativo
"""

import sys
sys.path.append('.')

from monitor_system import SystemMonitor

def run_health_check():
    """Executa health check completo"""
    monitor = SystemMonitor()
    return monitor.run_health_check()

if __name__ == "__main__":
    run_health_check()