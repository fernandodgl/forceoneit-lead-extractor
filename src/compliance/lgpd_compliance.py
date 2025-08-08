import json
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from pathlib import Path
import hashlib
import logging
from src.models.lead import Lead
from src.utils.config import Config

logger = logging.getLogger(__name__)


class LGPDComplianceManager:
    """
    Gerenciador de compliance LGPD
    Controla consentimentos, anonização e direitos dos titulares
    """
    
    def __init__(self):
        self.db_path = Config.DATA_DIR / "compliance.db"
        self._init_database()
        
    def _init_database(self):
        """Inicializa banco de dados de compliance"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Data subject rights table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS data_subjects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email_hash TEXT UNIQUE,
                    phone_hash TEXT,
                    cpf_hash TEXT,
                    consent_status TEXT DEFAULT 'pending',
                    consent_date TEXT,
                    consent_source TEXT,
                    purposes TEXT,
                    retention_until TEXT,
                    created_date TEXT NOT NULL,
                    last_updated TEXT,
                    status TEXT DEFAULT 'active'
                )
            """)
            
            # Consent log table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS consent_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    data_subject_id INTEGER,
                    action TEXT NOT NULL,
                    previous_status TEXT,
                    new_status TEXT,
                    source TEXT,
                    timestamp TEXT NOT NULL,
                    metadata TEXT,
                    FOREIGN KEY (data_subject_id) REFERENCES data_subjects (id)
                )
            """)
            
            # Data processing activities
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS processing_activities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    activity_name TEXT NOT NULL,
                    purpose TEXT NOT NULL,
                    legal_basis TEXT NOT NULL,
                    data_categories TEXT,
                    retention_period INTEGER,
                    automated_decision BOOLEAN DEFAULT FALSE,
                    third_party_sharing BOOLEAN DEFAULT FALSE,
                    international_transfer BOOLEAN DEFAULT FALSE,
                    created_date TEXT NOT NULL,
                    status TEXT DEFAULT 'active'
                )
            """)
            
            # Data breach incidents
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS breach_incidents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    incident_date TEXT NOT NULL,
                    discovered_date TEXT NOT NULL,
                    breach_type TEXT NOT NULL,
                    affected_records INTEGER,
                    risk_level TEXT,
                    anpd_notified BOOLEAN DEFAULT FALSE,
                    anpd_notification_date TEXT,
                    subjects_notified BOOLEAN DEFAULT FALSE,
                    description TEXT,
                    mitigation_actions TEXT,
                    status TEXT DEFAULT 'open'
                )
            """)
            
            conn.commit()
            conn.close()
            
            # Register default processing activities
            self._register_default_activities()
            
        except Exception as e:
            logger.error(f"Error initializing compliance database: {e}")
            
    def _register_default_activities(self):
        """Registra atividades de processamento padrão"""
        activities = [
            {
                "name": "Lead Generation",
                "purpose": "Identificação e qualificação de leads B2B",
                "legal_basis": "Interesse legítimo",
                "categories": "Dados profissionais, contato corporativo",
                "retention": 24,  # months
                "automated": True,
                "sharing": False,
                "transfer": False
            },
            {
                "name": "CRM Integration",
                "purpose": "Gestão de relacionamento com prospects",
                "legal_basis": "Interesse legítimo",
                "categories": "Dados de contato, empresa, histórico interações",
                "retention": 36,  # months
                "automated": False,
                "sharing": True,  # HubSpot
                "transfer": True  # HubSpot servers
            }
        ]
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for activity in activities:
                cursor.execute("""
                    INSERT OR IGNORE INTO processing_activities
                    (activity_name, purpose, legal_basis, data_categories, 
                     retention_period, automated_decision, third_party_sharing,
                     international_transfer, created_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    activity["name"],
                    activity["purpose"],
                    activity["legal_basis"],
                    activity["categories"],
                    activity["retention"],
                    activity["automated"],
                    activity["sharing"],
                    activity["transfer"],
                    datetime.now().isoformat()
                ))
                
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error registering default activities: {e}")
            
    def _hash_pii(self, data: str) -> str:
        """Cria hash irreversível de PII"""
        if not data:
            return None
        return hashlib.sha256(data.lower().strip().encode()).hexdigest()
        
    def register_data_subject(self, lead: Lead, 
                            consent_source: str = "business_card_public") -> str:
        """Registra titular de dados e consentimento implícito"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Hash PII
            email_hash = self._hash_pii(lead.email) if lead.email else None
            phone_hash = self._hash_pii(lead.phone) if lead.phone else None
            
            # Check if already exists
            if email_hash:
                cursor.execute(
                    "SELECT id FROM data_subjects WHERE email_hash = ?",
                    (email_hash,)
                )
                existing = cursor.fetchone()
                if existing:
                    return existing[0]
                    
            # Calculate retention date (24 months default)
            retention_until = (datetime.now() + timedelta(days=730)).isoformat()
            
            # Define purposes
            purposes = [
                "Prospecção B2B",
                "Qualificação de leads",
                "Comunicação comercial"
            ]
            
            # Insert new data subject
            cursor.execute("""
                INSERT INTO data_subjects
                (email_hash, phone_hash, consent_status, consent_date, consent_source,
                 purposes, retention_until, created_date, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                email_hash,
                phone_hash,
                "legitimate_interest",  # Base legal: interesse legítimo
                datetime.now().isoformat(),
                consent_source,
                json.dumps(purposes),
                retention_until,
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
            
            subject_id = cursor.lastrowid
            
            # Log consent
            self._log_consent_action(
                cursor, subject_id, "registered", 
                None, "legitimate_interest", consent_source
            )
            
            conn.commit()
            conn.close()
            
            return subject_id
            
        except Exception as e:
            logger.error(f"Error registering data subject: {e}")
            return None
            
    def _log_consent_action(self, cursor, subject_id: int, action: str,
                          previous_status: str, new_status: str,
                          source: str, metadata: Dict = None):
        """Registra ação de consentimento no log"""
        cursor.execute("""
            INSERT INTO consent_log
            (data_subject_id, action, previous_status, new_status, 
             source, timestamp, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            subject_id, action, previous_status, new_status,
            source, datetime.now().isoformat(),
            json.dumps(metadata or {})
        ))
        
    def check_consent_status(self, email: str) -> Optional[Dict[str, Any]]:
        """Verifica status de consentimento de um email"""
        try:
            email_hash = self._hash_pii(email)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT consent_status, consent_date, purposes, retention_until, status
                FROM data_subjects
                WHERE email_hash = ?
            """, (email_hash,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return {
                    "consent_status": result[0],
                    "consent_date": result[1],
                    "purposes": json.loads(result[2]) if result[2] else [],
                    "retention_until": result[3],
                    "status": result[4]
                }
                
        except Exception as e:
            logger.error(f"Error checking consent status: {e}")
            
        return None
        
    def update_consent(self, email: str, new_status: str, 
                      source: str = "manual") -> bool:
        """Atualiza consentimento de um titular"""
        try:
            email_hash = self._hash_pii(email)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get current status
            cursor.execute(
                "SELECT id, consent_status FROM data_subjects WHERE email_hash = ?",
                (email_hash,)
            )
            result = cursor.fetchone()
            
            if not result:
                logger.warning(f"Data subject not found for email")
                return False
                
            subject_id, current_status = result
            
            # Update status
            cursor.execute("""
                UPDATE data_subjects
                SET consent_status = ?, last_updated = ?
                WHERE id = ?
            """, (new_status, datetime.now().isoformat(), subject_id))
            
            # Log action
            self._log_consent_action(
                cursor, subject_id, "consent_updated",
                current_status, new_status, source
            )
            
            conn.commit()
            conn.close()
            
            logger.info(f"Updated consent status to {new_status}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating consent: {e}")
            return False
            
    def process_deletion_request(self, email: str) -> bool:
        """Processa solicitação de exclusão (direito ao esquecimento)"""
        try:
            email_hash = self._hash_pii(email)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Mark as deleted
            cursor.execute("""
                UPDATE data_subjects
                SET status = 'deleted', consent_status = 'revoked', 
                    last_updated = ?
                WHERE email_hash = ?
            """, (datetime.now().isoformat(), email_hash))
            
            if cursor.rowcount == 0:
                logger.warning("No data subject found for deletion")
                return False
                
            # Log deletion
            cursor.execute(
                "SELECT id FROM data_subjects WHERE email_hash = ?",
                (email_hash,)
            )
            subject_id = cursor.fetchone()[0]
            
            self._log_consent_action(
                cursor, subject_id, "deletion_request",
                "active", "deleted", "data_subject_request"
            )
            
            conn.commit()
            conn.close()
            
            logger.info(f"Processed deletion request")
            
            # TODO: Implement actual data deletion from all systems
            # This should include HubSpot, local caches, exports, etc.
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing deletion request: {e}")
            return False
            
    def generate_data_portability_export(self, email: str) -> Optional[Dict[str, Any]]:
        """Gera exportação de dados para portabilidade"""
        try:
            # This would collect all data about the subject
            # from all systems for export
            
            consent_status = self.check_consent_status(email)
            if not consent_status:
                return None
                
            export_data = {
                "personal_data": {
                    "email": email,  # Only if consented
                    "consent_status": consent_status
                },
                "processing_activities": self.get_processing_activities(),
                "export_date": datetime.now().isoformat(),
                "format_version": "1.0"
            }
            
            return export_data
            
        except Exception as e:
            logger.error(f"Error generating portability export: {e}")
            return None
            
    def get_processing_activities(self) -> List[Dict[str, Any]]:
        """Retorna atividades de processamento registradas"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT activity_name, purpose, legal_basis, data_categories,
                       retention_period, automated_decision, third_party_sharing,
                       international_transfer
                FROM processing_activities
                WHERE status = 'active'
            """)
            
            activities = []
            for row in cursor.fetchall():
                activities.append({
                    "name": row[0],
                    "purpose": row[1],
                    "legal_basis": row[2],
                    "data_categories": row[3],
                    "retention_months": row[4],
                    "automated_decision_making": bool(row[5]),
                    "third_party_sharing": bool(row[6]),
                    "international_transfer": bool(row[7])
                })
                
            conn.close()
            return activities
            
        except Exception as e:
            logger.error(f"Error getting processing activities: {e}")
            return []
            
    def audit_data_retention(self) -> List[Dict[str, Any]]:
        """Auditoria de retenção de dados"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Find subjects past retention period
            current_date = datetime.now().isoformat()
            cursor.execute("""
                SELECT id, email_hash, consent_date, retention_until, status
                FROM data_subjects
                WHERE retention_until < ? AND status = 'active'
            """, (current_date,))
            
            expired_subjects = []
            for row in cursor.fetchall():
                expired_subjects.append({
                    "subject_id": row[0],
                    "email_hash": row[1],
                    "consent_date": row[2],
                    "retention_until": row[3],
                    "days_expired": (datetime.now() - datetime.fromisoformat(row[3])).days
                })
                
            conn.close()
            
            if expired_subjects:
                logger.warning(f"Found {len(expired_subjects)} subjects past retention period")
                
            return expired_subjects
            
        except Exception as e:
            logger.error(f"Error auditing data retention: {e}")
            return []
            
    def anonymize_expired_data(self, dry_run: bool = True) -> int:
        """Anonimiza dados expirados"""
        expired_subjects = self.audit_data_retention()
        
        if not expired_subjects:
            return 0
            
        if dry_run:
            logger.info(f"DRY RUN: Would anonymize {len(expired_subjects)} subjects")
            return len(expired_subjects)
            
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            anonymized_count = 0
            
            for subject in expired_subjects:
                subject_id = subject["subject_id"]
                
                # Mark as anonymized
                cursor.execute("""
                    UPDATE data_subjects
                    SET status = 'anonymized', email_hash = NULL, 
                        phone_hash = NULL, last_updated = ?
                    WHERE id = ?
                """, (datetime.now().isoformat(), subject_id))
                
                # Log anonymization
                self._log_consent_action(
                    cursor, subject_id, "anonymized",
                    "active", "anonymized", "automated_retention"
                )
                
                anonymized_count += 1
                
            conn.commit()
            conn.close()
            
            logger.info(f"Anonymized {anonymized_count} expired data subjects")
            return anonymized_count
            
        except Exception as e:
            logger.error(f"Error anonymizing expired data: {e}")
            return 0
            
    def validate_lead_compliance(self, lead: Lead) -> Dict[str, Any]:
        """Valida compliance de um lead"""
        validation = {
            "compliant": True,
            "issues": [],
            "recommendations": []
        }
        
        # Check if email is in do-not-process list
        if lead.email:
            consent_status = self.check_consent_status(lead.email)
            if consent_status and consent_status["consent_status"] == "revoked":
                validation["compliant"] = False
                validation["issues"].append("Email in revoked consent list")
                
        # Check data minimization
        if not lead.company_name:
            validation["recommendations"].append("Ensure business context for data collection")
            
        # Check if data is from legitimate source
        legitimate_sources = ["Google Maps", "LinkedIn Sales Navigator", "website", "public_directory"]
        if lead.source not in legitimate_sources:
            validation["issues"].append("Data source may not meet legitimate interest requirements")
            validation["compliant"] = False
            
        return validation
        
    def generate_compliance_report(self) -> Dict[str, Any]:
        """Gera relatório de compliance LGPD"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Data subjects summary
            cursor.execute("""
                SELECT consent_status, COUNT(*) 
                FROM data_subjects 
                GROUP BY consent_status
            """)
            consent_summary = dict(cursor.fetchall())
            
            # Processing activities
            activities = self.get_processing_activities()
            
            # Recent consent actions
            cursor.execute("""
                SELECT action, COUNT(*) 
                FROM consent_log 
                WHERE timestamp >= date('now', '-30 days')
                GROUP BY action
            """)
            recent_actions = dict(cursor.fetchall())
            
            # Retention audit
            expired_data = self.audit_data_retention()
            
            conn.close()
            
            report = {
                "report_date": datetime.now().isoformat(),
                "data_subjects": {
                    "total": sum(consent_summary.values()),
                    "by_consent_status": consent_summary
                },
                "processing_activities": len(activities),
                "recent_consent_actions": recent_actions,
                "retention_compliance": {
                    "expired_subjects": len(expired_data),
                    "action_required": len(expired_data) > 0
                },
                "recommendations": self._get_compliance_recommendations(expired_data)
            }
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating compliance report: {e}")
            return {}
            
    def _get_compliance_recommendations(self, expired_data: List) -> List[str]:
        """Gera recomendações de compliance"""
        recommendations = []
        
        if expired_data:
            recommendations.append("Executar anonymização de dados expirados")
            
        recommendations.extend([
            "Implementar privacy by design em novos recursos",
            "Revisar bases legais para processamento regularmente",
            "Manter registro atualizado de atividades de tratamento",
            "Treinar equipe sobre direitos dos titulares"
        ])
        
        return recommendations