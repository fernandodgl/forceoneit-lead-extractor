import json
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Set
import logging
import random
from collections import defaultdict
from src.models.lead import Lead, Sector, CompanySize, CloudMaturity
from src.utils.config import Config
from src.scorers.lead_scorer import LeadScorer

logger = logging.getLogger(__name__)


class ProspectPlaylistAI:
    """
    Sistema de Prospect Playlists com IA
    Cria listas personalizadas e recomendações inteligentes
    """
    
    def __init__(self):
        self.db_path = Config.DATA_DIR / "playlists.db"
        self.scorer = LeadScorer()
        self._init_database()
        
    def _init_database(self):
        """Inicializa banco de dados de playlists"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Playlists table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS playlists (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    type TEXT NOT NULL,
                    criteria TEXT,
                    target_count INTEGER DEFAULT 50,
                    refresh_frequency INTEGER DEFAULT 24,
                    created_date TEXT NOT NULL,
                    last_updated TEXT,
                    last_refreshed TEXT,
                    status TEXT DEFAULT 'active',
                    metadata TEXT
                )
            """)
            
            # Playlist leads relationship
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS playlist_leads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    playlist_id INTEGER,
                    lead_data TEXT NOT NULL,
                    added_date TEXT NOT NULL,
                    score REAL,
                    priority TEXT,
                    status TEXT DEFAULT 'new',
                    engagement_history TEXT,
                    FOREIGN KEY (playlist_id) REFERENCES playlists (id)
                )
            """)
            
            # User preferences for AI recommendations
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    preferred_sectors TEXT,
                    preferred_company_sizes TEXT,
                    min_score REAL DEFAULT 60.0,
                    max_leads_per_day INTEGER DEFAULT 10,
                    engagement_tracking BOOLEAN DEFAULT TRUE,
                    created_date TEXT NOT NULL,
                    updated_date TEXT
                )
            """)
            
            # Engagement tracking
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS lead_engagement (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    lead_id TEXT NOT NULL,
                    user_id TEXT,
                    action_type TEXT NOT NULL,
                    action_date TEXT NOT NULL,
                    outcome TEXT,
                    notes TEXT,
                    metadata TEXT
                )
            """)
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error initializing playlists database: {e}")
            
    def create_playlist(self, name: str, description: str, 
                       criteria: Dict[str, Any], target_count: int = 50,
                       playlist_type: str = "dynamic") -> int:
        """Cria uma nova playlist"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO playlists
                (name, description, type, criteria, target_count, created_date, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                name, description, playlist_type,
                json.dumps(criteria), target_count,
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
            
            playlist_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            logger.info(f"Created playlist '{name}' with ID {playlist_id}")
            return playlist_id
            
        except Exception as e:
            logger.error(f"Error creating playlist: {e}")
            return None
            
    def generate_ai_recommendations(self, user_id: str = "default",
                                  leads_pool: List[Lead] = None) -> List[Dict[str, Any]]:
        """Gera recomendações de playlists baseadas em IA"""
        
        recommendations = []
        
        # Get user preferences
        preferences = self._get_user_preferences(user_id)
        
        # Predefined smart playlists based on Force One IT expertise
        smart_playlists = [
            {
                "name": "🔥 Hot AWS Migration Prospects",
                "description": "Empresas usando Azure/GCP com alto potencial de migração",
                "criteria": {
                    "competitor_cloud": ["azure", "gcp"],
                    "min_score": 75,
                    "sectors": ["banking", "retail", "manufacturing"]
                },
                "reasoning": "Empresas já na cloud com concorrentes são mais fáceis de converter"
            },
            {
                "name": "🏦 Banking Digital Transformation",
                "description": "Bancos e Fintechs em processo de transformação digital",
                "criteria": {
                    "sectors": ["banking", "fintech"],
                    "min_score": 70,
                    "company_sizes": ["large", "enterprise"],
                    "cloud_maturity": ["exploring", "adopting"]
                },
                "reasoning": "Setor bancário é prioridade e tem orçamento para projetos grandes"
            },
            {
                "name": "🚀 Scale-up Tech Companies",
                "description": "Empresas de tecnologia em crescimento precisando de escala",
                "criteria": {
                    "sectors": ["technology"],
                    "company_sizes": ["medium", "large"],
                    "min_score": 65,
                    "has_website": True
                },
                "reasoning": "Tech companies crescendo precisam de infraestrutura escalável"
            },
            {
                "name": "🏭 Industry 4.0 Manufacturers",
                "description": "Indústrias modernizando com IoT e dados",
                "criteria": {
                    "sectors": ["manufacturing"],
                    "min_score": 60,
                    "technologies_mentioned": ["iot", "data", "analytics", "automation"]
                },
                "reasoning": "Indústria 4.0 requer cloud para IoT e analytics"
            },
            {
                "name": "💎 E-commerce Growth Opportunities",
                "description": "E-commerces sem CDN ou escalabilidade cloud",
                "criteria": {
                    "sectors": ["retail", "ecommerce"],
                    "min_score": 55,
                    "pain_points": ["performance", "scalability", "traffic"]
                },
                "reasoning": "E-commerce precisa de performance e escalabilidade para crescer"
            },
            {
                "name": "🆕 New Decision Makers",
                "description": "Profissionais que mudaram recentemente de cargo",
                "criteria": {
                    "job_change_recent": True,
                    "min_score": 50,
                    "decision_maker_roles": True
                },
                "reasoning": "Novos decision makers estão mais abertos a mudanças"
            }
        ]
        
        # Filter recommendations based on user preferences
        for playlist_config in smart_playlists:
            if self._matches_user_preferences(playlist_config, preferences):
                
                # Estimate potential leads
                estimated_count = self._estimate_playlist_size(playlist_config["criteria"], leads_pool)
                
                recommendation = {
                    **playlist_config,
                    "estimated_leads": estimated_count,
                    "confidence": self._calculate_recommendation_confidence(playlist_config, preferences),
                    "playlist_type": "dynamic"
                }
                
                recommendations.append(recommendation)
                
        # Sort by confidence and estimated value
        recommendations.sort(key=lambda x: (x["confidence"], x["estimated_leads"]), reverse=True)
        
        return recommendations[:5]  # Top 5 recommendations
        
    def _get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """Recupera preferências do usuário"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT preferred_sectors, preferred_company_sizes, min_score, max_leads_per_day
                FROM user_preferences
                WHERE user_id = ?
            """, (user_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return {
                    "preferred_sectors": json.loads(result[0]) if result[0] else [],
                    "preferred_company_sizes": json.loads(result[1]) if result[1] else [],
                    "min_score": result[2],
                    "max_leads_per_day": result[3]
                }
                
        except Exception as e:
            logger.error(f"Error getting user preferences: {e}")
            
        # Default preferences
        return {
            "preferred_sectors": ["banking", "technology", "retail"],
            "preferred_company_sizes": ["medium", "large", "enterprise"],
            "min_score": 60.0,
            "max_leads_per_day": 10
        }
        
    def _matches_user_preferences(self, playlist_config: Dict, preferences: Dict) -> bool:
        """Verifica se playlist combina com preferências do usuário"""
        criteria = playlist_config.get("criteria", {})
        
        # Check sector preferences
        if preferences.get("preferred_sectors"):
            playlist_sectors = criteria.get("sectors", [])
            if playlist_sectors and not any(s in preferences["preferred_sectors"] for s in playlist_sectors):
                return False
                
        # Check minimum score
        if criteria.get("min_score", 0) < preferences.get("min_score", 0):
            return False
            
        return True
        
    def _estimate_playlist_size(self, criteria: Dict[str, Any], leads_pool: List[Lead] = None) -> int:
        """Estima quantidade de leads que uma playlist geraria"""
        if not leads_pool:
            # Return estimates based on typical data
            base_estimate = 100
            
            # Adjust based on selectivity
            if criteria.get("min_score", 0) > 80:
                base_estimate *= 0.3
            elif criteria.get("min_score", 0) > 70:
                base_estimate *= 0.5
            elif criteria.get("min_score", 0) > 60:
                base_estimate *= 0.7
                
            # Sector selectivity
            sectors = criteria.get("sectors", [])
            if len(sectors) == 1:
                base_estimate *= 0.6
            elif len(sectors) == 2:
                base_estimate *= 0.8
                
            return int(base_estimate)
            
        # Actually filter the leads pool
        filtered = self._filter_leads_by_criteria(leads_pool, criteria)
        return len(filtered)
        
    def _calculate_recommendation_confidence(self, playlist_config: Dict, preferences: Dict) -> float:
        """Calcula confiança da recomendação"""
        confidence = 0.5  # Base confidence
        
        criteria = playlist_config.get("criteria", {})
        
        # Sector match
        if preferences.get("preferred_sectors"):
            playlist_sectors = criteria.get("sectors", [])
            if any(s in preferences["preferred_sectors"] for s in playlist_sectors):
                confidence += 0.2
                
        # Score alignment
        min_score = criteria.get("min_score", 50)
        pref_min_score = preferences.get("min_score", 60)
        if abs(min_score - pref_min_score) <= 10:
            confidence += 0.15
            
        # Force One IT specialization bonus
        specialized_keywords = ["aws", "cloud", "migration", "banking", "fintech"]
        description = playlist_config.get("description", "").lower()
        if any(keyword in description for keyword in specialized_keywords):
            confidence += 0.15
            
        return min(confidence, 1.0)
        
    def populate_playlist(self, playlist_id: int, leads: List[Lead]) -> int:
        """Popula playlist com leads"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get playlist criteria
            cursor.execute("SELECT criteria FROM playlists WHERE id = ?", (playlist_id,))
            result = cursor.fetchone()
            if not result:
                return 0
                
            criteria = json.loads(result[0])
            
            # Filter leads based on criteria
            filtered_leads = self._filter_leads_by_criteria(leads, criteria)
            
            # Clear existing leads (for dynamic playlists)
            cursor.execute("DELETE FROM playlist_leads WHERE playlist_id = ?", (playlist_id,))
            
            # Add new leads
            added_count = 0
            for lead in filtered_leads:
                cursor.execute("""
                    INSERT INTO playlist_leads
                    (playlist_id, lead_data, added_date, score, priority)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    playlist_id,
                    json.dumps(lead.to_dict()),
                    datetime.now().isoformat(),
                    lead.score,
                    lead.calculate_priority()
                ))
                added_count += 1
                
            # Update playlist
            cursor.execute("""
                UPDATE playlists
                SET last_refreshed = ?, last_updated = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), datetime.now().isoformat(), playlist_id))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Populated playlist {playlist_id} with {added_count} leads")
            return added_count
            
        except Exception as e:
            logger.error(f"Error populating playlist: {e}")
            return 0
            
    def _filter_leads_by_criteria(self, leads: List[Lead], criteria: Dict[str, Any]) -> List[Lead]:
        """Filtra leads baseado nos critérios"""
        filtered = []
        
        for lead in leads:
            if self._lead_matches_criteria(lead, criteria):
                filtered.append(lead)
                
        # Sort by score descending
        filtered.sort(key=lambda x: x.score, reverse=True)
        
        # Apply limit if specified
        limit = criteria.get("limit", len(filtered))
        return filtered[:limit]
        
    def _lead_matches_criteria(self, lead: Lead, criteria: Dict[str, Any]) -> bool:
        """Verifica se lead atende aos critérios"""
        
        # Minimum score
        if lead.score < criteria.get("min_score", 0):
            return False
            
        # Sectors
        sectors = criteria.get("sectors", [])
        if sectors and (not lead.sector or lead.sector.value not in sectors):
            return False
            
        # Company sizes
        sizes = criteria.get("company_sizes", [])
        if sizes and (not lead.company_size or lead.company_size.value not in sizes):
            return False
            
        # Cloud maturity
        maturity_levels = criteria.get("cloud_maturity", [])
        if maturity_levels and (not lead.cloud_maturity or lead.cloud_maturity.value not in maturity_levels):
            return False
            
        # Competitor cloud
        competitor_clouds = criteria.get("competitor_cloud", [])
        if competitor_clouds and lead.competitor_cloud not in competitor_clouds:
            return False
            
        # Has website
        if criteria.get("has_website", False) and not lead.website:
            return False
            
        # Technologies mentioned
        tech_keywords = criteria.get("technologies_mentioned", [])
        if tech_keywords:
            lead_techs = [tech.lower() for tech in lead.technologies_used]
            if not any(keyword.lower() in ' '.join(lead_techs) for keyword in tech_keywords):
                return False
                
        # Pain points
        required_pain_points = criteria.get("pain_points", [])
        if required_pain_points:
            lead_pain_points = [pp.lower() for pp in lead.pain_points]
            if not any(rpp.lower() in ' '.join(lead_pain_points) for rpp in required_pain_points):
                return False
                
        return True
        
    def get_daily_recommendations(self, user_id: str = "default", 
                                limit: int = 10) -> List[Dict[str, Any]]:
        """Gera recomendações diárias de leads"""
        try:
            preferences = self._get_user_preferences(user_id)
            daily_limit = min(limit, preferences.get("max_leads_per_day", 10))
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get leads from active playlists
            cursor.execute("""
                SELECT pl.lead_data, pl.score, pl.priority, p.name as playlist_name
                FROM playlist_leads pl
                JOIN playlists p ON pl.playlist_id = p.id
                WHERE p.status = 'active' AND pl.status = 'new'
                ORDER BY pl.score DESC, pl.added_date DESC
                LIMIT ?
            """, (daily_limit * 2,))  # Get more to allow filtering
            
            results = cursor.fetchall()
            conn.close()
            
            recommendations = []
            seen_companies = set()
            
            for row in results:
                if len(recommendations) >= daily_limit:
                    break
                    
                lead_data = json.loads(row[0])
                company_name = lead_data.get("company_name")
                
                # Avoid duplicates
                if company_name in seen_companies:
                    continue
                    
                seen_companies.add(company_name)
                
                # Generate personalized reasoning
                reasoning = self._generate_lead_reasoning(lead_data, row[3])  # playlist_name
                
                recommendation = {
                    "lead": lead_data,
                    "score": row[1],
                    "priority": row[2],
                    "source_playlist": row[3],
                    "reasoning": reasoning,
                    "suggested_actions": self._generate_suggested_actions(lead_data),
                    "recommended_at": datetime.now().isoformat()
                }
                
                recommendations.append(recommendation)
                
            return recommendations
            
        except Exception as e:
            logger.error(f"Error getting daily recommendations: {e}")
            return []
            
    def _generate_lead_reasoning(self, lead_data: Dict, playlist_name: str) -> str:
        """Gera reasoning personalizado para o lead"""
        company_name = lead_data.get("company_name", "Empresa")
        sector = lead_data.get("sector", "")
        score = lead_data.get("score", 0)
        
        reasons = []
        
        # Score-based reasoning
        if score >= 80:
            reasons.append("🔥 Score muito alto - prospect extremamente qualificado")
        elif score >= 70:
            reasons.append("⭐ Score alto - excelente oportunidade")
        elif score >= 60:
            reasons.append("✅ Score bom - vale a pena abordar")
            
        # Sector-specific reasoning
        if sector == "banking":
            reasons.append("🏦 Setor bancário - alta prioridade Force One IT")
        elif sector == "technology":
            reasons.append("💻 Tech company - entende valor da cloud")
        elif sector == "retail":
            reasons.append("🛍️ Varejo - precisa escalar para picos de demanda")
            
        # Cloud status
        if lead_data.get("aws_usage"):
            reasons.append("☁️ Já usa AWS - oportunidade de expansão")
        elif lead_data.get("competitor_cloud"):
            reasons.append("🔄 Usa cloud concorrente - potencial migração")
        else:
            reasons.append("🚀 Sem cloud - oportunidade de primeira migração")
            
        return f"Selecionado da playlist '{playlist_name}'. " + ". ".join(reasons[:3])
        
    def _generate_suggested_actions(self, lead_data: Dict) -> List[str]:
        """Gera ações sugeridas para o lead"""
        actions = []
        
        # Basic actions
        actions.append("📞 Pesquisar contatos no LinkedIn")
        
        if lead_data.get("website"):
            actions.append("🌐 Analisar website da empresa")
            
        # Score-based actions
        score = lead_data.get("score", 0)
        if score >= 80:
            actions.extend([
                "📅 Agendar reunião de descoberta",
                "📊 Preparar case similar da Force One IT"
            ])
        elif score >= 70:
            actions.extend([
                "📧 Enviar email personalizado",
                "🎯 Preparar proposta inicial"
            ])
        else:
            actions.append("📝 Fazer nurturing com conteúdo")
            
        # Sector-specific actions
        sector = lead_data.get("sector", "")
        if sector == "banking":
            actions.append("🔒 Enfatizar compliance e security")
        elif sector == "retail":
            actions.append("📈 Destacar escalabilidade para picos")
            
        return actions[:4]  # Limit to 4 actions
        
    def track_engagement(self, lead_id: str, user_id: str, 
                        action_type: str, outcome: str = None, 
                        notes: str = None) -> bool:
        """Rastreia engajamento com leads para melhorar IA"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO lead_engagement
                (lead_id, user_id, action_type, action_date, outcome, notes)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                lead_id, user_id, action_type,
                datetime.now().isoformat(), outcome, notes
            ))
            
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            logger.error(f"Error tracking engagement: {e}")
            return False
            
    def get_playlist_performance(self, playlist_id: int) -> Dict[str, Any]:
        """Analisa performance de uma playlist"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Playlist basic info
            cursor.execute("""
                SELECT name, description, created_date, last_refreshed
                FROM playlists WHERE id = ?
            """, (playlist_id,))
            playlist_info = cursor.fetchone()
            
            if not playlist_info:
                return {}
                
            # Lead stats
            cursor.execute("""
                SELECT COUNT(*), AVG(score), 
                       COUNT(CASE WHEN priority = 'HOT' THEN 1 END),
                       COUNT(CASE WHEN priority = 'WARM' THEN 1 END),
                       COUNT(CASE WHEN status = 'contacted' THEN 1 END)
                FROM playlist_leads WHERE playlist_id = ?
            """, (playlist_id,))
            lead_stats = cursor.fetchone()
            
            # Engagement stats
            cursor.execute("""
                SELECT action_type, COUNT(*), 
                       COUNT(CASE WHEN outcome = 'positive' THEN 1 END)
                FROM lead_engagement le
                JOIN playlist_leads pl ON le.lead_id = pl.lead_data
                WHERE pl.playlist_id = ?
                GROUP BY action_type
            """, (playlist_id,))
            engagement_stats = cursor.fetchall()
            
            conn.close()
            
            return {
                "playlist_name": playlist_info[0],
                "description": playlist_info[1],
                "created_date": playlist_info[2],
                "last_refreshed": playlist_info[3],
                "total_leads": lead_stats[0],
                "average_score": round(lead_stats[1] or 0, 2),
                "hot_leads": lead_stats[2],
                "warm_leads": lead_stats[3],
                "contacted_leads": lead_stats[4],
                "engagement_by_action": {
                    row[0]: {"count": row[1], "positive_outcomes": row[2]}
                    for row in engagement_stats
                },
                "conversion_rate": round((lead_stats[4] / lead_stats[0] * 100) if lead_stats[0] > 0 else 0, 2)
            }
            
        except Exception as e:
            logger.error(f"Error getting playlist performance: {e}")
            return {}
            
    def auto_refresh_playlists(self, leads_pool: List[Lead]) -> Dict[str, int]:
        """Atualiza automaticamente playlists dinâmicas"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get playlists that need refresh
            cutoff_time = (datetime.now() - timedelta(hours=24)).isoformat()
            cursor.execute("""
                SELECT id, name, refresh_frequency
                FROM playlists
                WHERE type = 'dynamic' AND status = 'active'
                AND (last_refreshed IS NULL OR last_refreshed < ?)
            """, (cutoff_time,))
            
            playlists_to_refresh = cursor.fetchall()
            conn.close()
            
            refresh_results = {}
            
            for playlist_id, name, frequency in playlists_to_refresh:
                count = self.populate_playlist(playlist_id, leads_pool)
                refresh_results[name] = count
                logger.info(f"Refreshed playlist '{name}' with {count} leads")
                
            return refresh_results
            
        except Exception as e:
            logger.error(f"Error auto-refreshing playlists: {e}")
            return {}