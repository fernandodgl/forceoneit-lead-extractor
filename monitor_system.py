#!/usr/bin/env python3
"""
Monitor de Sistema - Performance e Status
"""

import time
import json
from datetime import datetime, timedelta
from pathlib import Path
import psutil
import sys

from src.utils.config import Config
from src.compliance.lgpd_compliance import LGPDComplianceManager
from src.monitors.job_change_monitor import JobChangeMonitor
from src.ai.prospect_playlists import ProspectPlaylistAI

class SystemMonitor:
    """Monitor de sistema e performance"""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.stats = {
            "leads_processed": 0,
            "api_calls": 0,
            "errors": 0,
            "exports_created": 0
        }
        
    def get_system_status(self):
        """Status geral do sistema"""
        status = {
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": (datetime.now() - self.start_time).total_seconds(),
            "system": {
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage('.').percent
            },
            "directories": {
                "data_dir": str(Config.DATA_DIR),
                "cache_dir": str(Config.CACHE_DIR),
                "exports_dir": str(Config.EXPORTS_DIR),
                "logs_dir": str(Config.LOGS_DIR)
            },
            "files": self._count_files(),
            "stats": self.stats
        }
        
        return status
    
    def _count_files(self):
        """Conta arquivos nos diretórios"""
        counts = {}
        
        for dir_name, dir_path in [
            ("exports", Config.EXPORTS_DIR),
            ("cache", Config.CACHE_DIR),
            ("logs", Config.LOGS_DIR)
        ]:
            try:
                if dir_path.exists():
                    counts[dir_name] = len(list(dir_path.glob("*")))
                else:
                    counts[dir_name] = 0
            except:
                counts[dir_name] = 0
                
        return counts
    
    def check_api_keys(self):
        """Verifica se APIs estão configuradas"""
        apis = {
            "google_maps": bool(Config.GOOGLE_MAPS_API_KEY and Config.GOOGLE_MAPS_API_KEY != "your_google_maps_api_key_here"),
            "hubspot": bool(Config.HUBSPOT_API_KEY and Config.HUBSPOT_API_KEY != "your_hubspot_private_app_key_here"),
            "linkedin": bool(Config.LINKEDIN_USERNAME and Config.LINKEDIN_PASSWORD)
        }
        
        return apis
    
    def get_compliance_summary(self):
        """Resumo de compliance LGPD"""
        try:
            compliance = LGPDComplianceManager()
            report = compliance.generate_compliance_report()
            
            return {
                "total_subjects": report.get("data_subjects", {}).get("total", 0),
                "consent_status": report.get("data_subjects", {}).get("by_consent_status", {}),
                "expired_subjects": report.get("retention_compliance", {}).get("expired_subjects", 0),
                "action_required": report.get("retention_compliance", {}).get("action_required", False)
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_job_changes_summary(self):
        """Resumo de mudanças de trabalho"""
        try:
            monitor = JobChangeMonitor()
            recent_changes = monitor.get_recent_changes(days=7, min_score=60)
            
            return {
                "recent_changes": len(recent_changes),
                "high_priority": len([c for c in recent_changes if c.get("opportunity_score", 0) >= 80]),
                "last_check": "N/A"  # Would get from database
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_ai_insights(self):
        """Insights do sistema de IA"""
        try:
            ai = ProspectPlaylistAI()
            
            # Simulated insights - in production would get from database
            return {
                "active_playlists": 0,  # Would query database
                "recommendations_today": 0,
                "avg_lead_score": 0,
                "conversion_rate": 0
            }
        except Exception as e:
            return {"error": str(e)}
    
    def run_health_check(self):
        """Verificação completa de saúde do sistema"""
        print("=== FORCE ONE IT SYSTEM HEALTH CHECK ===")
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # System status
        status = self.get_system_status()
        print(f"🖥️  Sistema:")
        print(f"   CPU: {status['system']['cpu_percent']:.1f}%")
        print(f"   Memória: {status['system']['memory_percent']:.1f}%")
        print(f"   Disco: {status['system']['disk_percent']:.1f}%")
        print()
        
        # API Keys
        apis = self.check_api_keys()
        print(f"🔑 APIs Configuradas:")
        for api, configured in apis.items():
            status_icon = "✅" if configured else "❌"
            print(f"   {api}: {status_icon}")
        print()
        
        # Files
        files = status['files']
        print(f"📁 Arquivos:")
        print(f"   Exports: {files.get('exports', 0)}")
        print(f"   Cache: {files.get('cache', 0)}")
        print(f"   Logs: {files.get('logs', 0)}")
        print()
        
        # Compliance
        compliance = self.get_compliance_summary()
        if "error" not in compliance:
            print(f"🛡️  LGPD Compliance:")
            print(f"   Titulares: {compliance.get('total_subjects', 0)}")
            print(f"   Ação necessária: {'Sim' if compliance.get('action_required') else 'Não'}")
        print()
        
        # Job Changes
        job_changes = self.get_job_changes_summary()
        if "error" not in job_changes:
            print(f"💼 Mudanças de Trabalho (7 dias):")
            print(f"   Total: {job_changes.get('recent_changes', 0)}")
            print(f"   Alta prioridade: {job_changes.get('high_priority', 0)}")
        print()
        
        # Overall health
        critical_apis = sum([apis['google_maps'], apis.get('hubspot', False)])
        if critical_apis >= 1:
            health = "🟢 SAUDÁVEL"
        elif critical_apis == 1:
            health = "🟡 FUNCIONANDO"
        else:
            health = "🔴 PRECISA CONFIGURAÇÃO"
            
        print(f"Status Geral: {health}")
        
        return status

def monitor_performance():
    """Monitor de performance em tempo real"""
    print("=== MONITOR DE PERFORMANCE ===")
    print("Pressione Ctrl+C para parar")
    print()
    
    monitor = SystemMonitor()
    
    try:
        while True:
            status = monitor.get_system_status()
            
            print(f"\rCPU: {status['system']['cpu_percent']:5.1f}% | " +
                  f"MEM: {status['system']['memory_percent']:5.1f}% | " +
                  f"DISK: {status['system']['disk_percent']:5.1f}% | " +
                  f"Files: {sum(status['files'].values())}", end="")
            
            time.sleep(2)
            
    except KeyboardInterrupt:
        print("\nMonitoramento interrompido")

def main():
    """Menu principal"""
    print("FORCE ONE IT - SYSTEM MONITOR")
    print("=" * 40)
    
    monitor = SystemMonitor()
    
    while True:
        print("\nOpções:")
        print("1. Health Check completo")
        print("2. Monitor de performance")
        print("3. Status das APIs")
        print("4. Compliance LGPD")
        print("5. Sair")
        
        try:
            choice = input("\nEscolha uma opção (1-5): ").strip()
            
            if choice == "1":
                monitor.run_health_check()
                
            elif choice == "2":
                monitor_performance()
                
            elif choice == "3":
                apis = monitor.check_api_keys()
                print("\n🔑 Status das APIs:")
                for api, configured in apis.items():
                    status = "Configurada" if configured else "Não configurada"
                    print(f"   {api}: {status}")
                    
            elif choice == "4":
                compliance = monitor.get_compliance_summary()
                if "error" not in compliance:
                    print("\n🛡️  LGPD Compliance:")
                    print(f"   Total de titulares: {compliance['total_subjects']}")
                    print(f"   Ação necessária: {'Sim' if compliance['action_required'] else 'Não'}")
                else:
                    print(f"❌ Erro no compliance: {compliance['error']}")
                    
            elif choice == "5":
                print("Saindo...")
                break
                
            else:
                print("Opção inválida")
                
        except KeyboardInterrupt:
            print("\nSaindo...")
            break
        except Exception as e:
            print(f"Erro: {e}")

if __name__ == "__main__":
    main()