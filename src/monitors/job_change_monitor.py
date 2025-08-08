import time
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import sqlite3
from pathlib import Path
import logging
from src.models.lead import Lead
from src.utils.config import Config
from src.extractors.linkedin_extractor import LinkedInExtractor

logger = logging.getLogger(__name__)


class JobChangeMonitor:
    """
    Monitor de mudanças de trabalho
    Detecta quando decision makers mudam de empresa
    """
    
    def __init__(self):
        self.db_path = Config.DATA_DIR / "job_changes.db"
        self.linkedin_extractor = None
        self._init_database()
        
    def _init_database(self):
        """Inicializa banco de dados para monitoramento"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Table for tracked decision makers
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tracked_contacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    current_company TEXT,
                    current_role TEXT,
                    linkedin_url TEXT UNIQUE,
                    email TEXT,
                    phone TEXT,
                    original_company TEXT,
                    original_role TEXT,
                    original_lead_score REAL,
                    added_date TEXT NOT NULL,
                    last_checked TEXT,
                    status TEXT DEFAULT 'active',
                    metadata TEXT
                )
            """)
            
            # Table for job change events
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS job_changes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    contact_id INTEGER,
                    previous_company TEXT,
                    new_company TEXT,
                    previous_role TEXT,
                    new_role TEXT,
                    change_date TEXT NOT NULL,
                    detected_date TEXT NOT NULL,
                    change_type TEXT,
                    opportunity_score REAL,
                    alert_status TEXT DEFAULT 'new',
                    notes TEXT,
                    FOREIGN KEY (contact_id) REFERENCES tracked_contacts (id)
                )
            """)
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error initializing job change database: {e}")
            
    def add_contacts_for_monitoring(self, leads: List[Lead]):
        """Adiciona contatos dos leads para monitoramento"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            added_count = 0
            
            for lead in leads:
                # Add decision makers from the lead
                for dm in lead.decision_makers:
                    if not dm.get('linkedin_url'):
                        continue
                        
                    # Check if already exists
                    cursor.execute(
                        "SELECT id FROM tracked_contacts WHERE linkedin_url = ?",
                        (dm['linkedin_url'],)
                    )
                    
                    if cursor.fetchone():
                        continue  # Already tracking this contact
                        
                    # Add new contact for tracking
                    cursor.execute("""
                        INSERT INTO tracked_contacts 
                        (name, current_company, current_role, linkedin_url, email, phone,
                         original_company, original_role, original_lead_score, added_date, metadata)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        dm.get('name'),
                        lead.company_name,
                        dm.get('role'),
                        dm.get('linkedin_url'),
                        dm.get('email'),
                        dm.get('phone'),
                        lead.company_name,  # original company
                        dm.get('role'),     # original role
                        lead.score,
                        datetime.now().isoformat(),
                        json.dumps(dm.get('metadata', {}))
                    ))
                    
                    added_count += 1
                    
            conn.commit()
            conn.close()
            
            logger.info(f"Added {added_count} contacts for job change monitoring")
            return added_count
            
        except Exception as e:
            logger.error(f"Error adding contacts for monitoring: {e}")
            return 0
            
    def check_job_changes(self, max_contacts: int = 100) -> List[Dict[str, Any]]:
        """Verifica mudanças de trabalho dos contatos monitorados"""
        changes = []
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get contacts to check (prioritize those not checked recently)
            cursor.execute("""
                SELECT id, name, current_company, current_role, linkedin_url, last_checked
                FROM tracked_contacts
                WHERE status = 'active'
                ORDER BY 
                    CASE WHEN last_checked IS NULL THEN 0 ELSE 1 END,
                    last_checked ASC
                LIMIT ?
            """, (max_contacts,))
            
            contacts = cursor.fetchall()
            
            # Initialize LinkedIn extractor if needed
            if not self.linkedin_extractor:
                self.linkedin_extractor = LinkedInExtractor()
                if not self.linkedin_extractor.login():
                    logger.error("Failed to login to LinkedIn for job change monitoring")
                    return changes
                    
            for contact in contacts:
                contact_id, name, current_company, current_role, linkedin_url, last_checked = contact
                
                try:
                    # Check current profile
                    new_info = self._check_linkedin_profile(linkedin_url)
                    
                    if new_info:
                        new_company = new_info.get('company')
                        new_role = new_info.get('role')
                        
                        # Detect changes
                        company_changed = new_company and new_company != current_company
                        role_changed = new_role and new_role != current_role
                        
                        if company_changed or role_changed:
                            # Record the job change
                            change_data = self._record_job_change(
                                cursor, contact_id, name,
                                current_company, new_company,
                                current_role, new_role,
                                linkedin_url
                            )
                            
                            if change_data:
                                changes.append(change_data)
                                
                        # Update contact's current info
                        cursor.execute("""
                            UPDATE tracked_contacts
                            SET current_company = ?, current_role = ?, last_checked = ?
                            WHERE id = ?
                        """, (
                            new_company or current_company,
                            new_role or current_role,
                            datetime.now().isoformat(),
                            contact_id
                        ))
                        
                    # Rate limiting
                    time.sleep(2)
                    
                except Exception as e:
                    logger.warning(f"Error checking contact {name}: {e}")
                    continue
                    
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error checking job changes: {e}")
            
        logger.info(f"Found {len(changes)} job changes")
        return changes
        
    def _check_linkedin_profile(self, linkedin_url: str) -> Optional[Dict[str, str]]:
        """Verifica perfil atual no LinkedIn"""
        if not self.linkedin_extractor or not linkedin_url:
            return None
            
        try:
            self.linkedin_extractor.driver.get(linkedin_url)
            time.sleep(3)
            
            # Extract current company and role
            company = None
            role = None
            
            try:
                # Current role/company (first experience item)
                exp_section = self.linkedin_extractor.driver.find_element(
                    By.CSS_SELECTOR, "[data-section='experience'] ul li:first-child"
                )
                
                role_element = exp_section.find_element(By.CSS_SELECTOR, "h3")
                role = role_element.text.strip()
                
                company_element = exp_section.find_element(By.CSS_SELECTOR, "h4 a")
                company = company_element.text.strip()
                
            except Exception:
                # Alternative selectors
                try:
                    role_element = self.linkedin_extractor.driver.find_element(
                        By.CSS_SELECTOR, ".top-card-layout__headline"
                    )
                    role = role_element.text.strip()
                except Exception:
                    pass
                    
            return {
                "company": company,
                "role": role
            }
            
        except Exception as e:
            logger.warning(f"Error checking LinkedIn profile {linkedin_url}: {e}")
            return None
            
    def _record_job_change(self, cursor, contact_id: int, name: str,
                          old_company: str, new_company: str,
                          old_role: str, new_role: str,
                          linkedin_url: str) -> Optional[Dict[str, Any]]:
        """Registra mudança de trabalho"""
        try:
            # Determine change type
            change_type = "unknown"
            if old_company != new_company and old_role != new_role:
                change_type = "company_and_role_change"
            elif old_company != new_company:
                change_type = "company_change"
            elif old_role != new_role:
                change_type = "role_change"
                
            # Calculate opportunity score
            opportunity_score = self._calculate_opportunity_score(
                old_company, new_company, old_role, new_role
            )
            
            # Insert job change record
            cursor.execute("""
                INSERT INTO job_changes
                (contact_id, previous_company, new_company, previous_role, new_role,
                 change_date, detected_date, change_type, opportunity_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                contact_id, old_company, new_company, old_role, new_role,
                datetime.now().isoformat(),  # Assuming recent change
                datetime.now().isoformat(),
                change_type,
                opportunity_score
            ))
            
            change_id = cursor.lastrowid
            
            return {
                "id": change_id,
                "contact_id": contact_id,
                "name": name,
                "previous_company": old_company,
                "new_company": new_company,
                "previous_role": old_role,
                "new_role": new_role,
                "change_type": change_type,
                "opportunity_score": opportunity_score,
                "linkedin_url": linkedin_url,
                "detected_date": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error recording job change for {name}: {e}")
            return None
            
    def _calculate_opportunity_score(self, old_company: str, new_company: str,
                                   old_role: str, new_role: str) -> float:
        """Calcula score de oportunidade da mudança"""
        score = 50.0  # Base score
        
        # Company change increases opportunity
        if old_company != new_company:
            score += 20
            
        # Role upgrade/promotion
        if new_role and old_role:
            promotion_indicators = ["diretor", "director", "head", "vp", "vice", "chief", "ceo", "cto", "cio"]
            old_role_lower = old_role.lower()
            new_role_lower = new_role.lower()
            
            old_is_senior = any(indicator in old_role_lower for indicator in promotion_indicators)
            new_is_senior = any(indicator in new_role_lower for indicator in promotion_indicators)
            
            if new_is_senior and not old_is_senior:
                score += 30  # Promoted to senior role
            elif new_is_senior:
                score += 15  # Already senior, still valuable
                
        # Target sectors/companies
        target_keywords = ["tecnologia", "tech", "cloud", "aws", "digital", "software"]
        if new_company:
            new_company_lower = new_company.lower()
            if any(keyword in new_company_lower for keyword in target_keywords):
                score += 10
                
        # Timing bonus (new role = good time to approach)
        score += 10
        
        return min(score, 100.0)
        
    def get_recent_changes(self, days: int = 7, min_score: float = 60.0) -> List[Dict[str, Any]]:
        """Recupera mudanças recentes com score mínimo"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            cursor.execute("""
                SELECT jc.*, tc.name, tc.linkedin_url, tc.original_company, tc.original_lead_score
                FROM job_changes jc
                JOIN tracked_contacts tc ON jc.contact_id = tc.id
                WHERE jc.detected_date >= ? AND jc.opportunity_score >= ?
                ORDER BY jc.opportunity_score DESC, jc.detected_date DESC
            """, (cutoff_date, min_score))
            
            changes = []
            columns = [desc[0] for desc in cursor.description]
            
            for row in cursor.fetchall():
                change = dict(zip(columns, row))
                changes.append(change)
                
            conn.close()
            
            return changes
            
        except Exception as e:
            logger.error(f"Error getting recent changes: {e}")
            return []
            
    def generate_opportunity_alerts(self, changes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Gera alertas de oportunidade baseados nas mudanças"""
        alerts = []
        
        for change in changes:
            alert = {
                "type": "job_change_opportunity",
                "priority": self._get_priority_from_score(change["opportunity_score"]),
                "contact_name": change["name"],
                "previous_company": change["previous_company"],
                "new_company": change["new_company"],
                "new_role": change["new_role"],
                "opportunity_score": change["opportunity_score"],
                "linkedin_url": change["linkedin_url"],
                "detected_date": change["detected_date"],
                "message": self._generate_alert_message(change),
                "action_items": self._generate_action_items(change)
            }
            
            alerts.append(alert)
            
        return alerts
        
    def _get_priority_from_score(self, score: float) -> str:
        """Converte score em prioridade"""
        if score >= 80:
            return "HIGH"
        elif score >= 65:
            return "MEDIUM"
        else:
            return "LOW"
            
    def _generate_alert_message(self, change: Dict[str, Any]) -> str:
        """Gera mensagem do alerta"""
        name = change["name"]
        new_company = change["new_company"]
        new_role = change["new_role"]
        previous_company = change["previous_company"]
        
        if change["change_type"] == "company_change":
            return f"{name} mudou de {previous_company} para {new_company} como {new_role}"
        elif change["change_type"] == "role_change":
            return f"{name} foi promovido(a) para {new_role} na {new_company}"
        else:
            return f"{name} mudou para {new_company} como {new_role}"
            
    def _generate_action_items(self, change: Dict[str, Any]) -> List[str]:
        """Gera itens de ação para o alerta"""
        actions = [
            "Enviar mensagem de congratulações no LinkedIn",
            "Avaliar se nova empresa é prospect qualificado"
        ]
        
        if change["opportunity_score"] >= 80:
            actions.extend([
                "Agendar reunião de descoberta AWS",
                "Apresentar cases similares da Force One IT"
            ])
        elif change["opportunity_score"] >= 65:
            actions.append("Avaliar fit com soluções AWS")
            
        return actions
        
    def cleanup_old_records(self, days: int = 365):
        """Remove registros antigos"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            # Remove old job changes
            cursor.execute(
                "DELETE FROM job_changes WHERE detected_date < ?",
                (cutoff_date,)
            )
            
            # Mark inactive contacts that haven't been checked in a long time
            cursor.execute("""
                UPDATE tracked_contacts 
                SET status = 'inactive' 
                WHERE last_checked < ? OR last_checked IS NULL
            """, (cutoff_date,))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error cleaning up old records: {e}")