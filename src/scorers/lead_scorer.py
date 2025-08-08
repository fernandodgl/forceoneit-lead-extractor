from typing import Dict, List
from src.models.lead import Lead, CompanySize, Sector, CloudMaturity
from src.utils.config import Config
import logging

logger = logging.getLogger(__name__)


class LeadScorer:
    def __init__(self):
        self.weights = Config.SCORING_WEIGHTS
        self.target_sectors = [
            Sector.BANKING, Sector.FINTECH, Sector.RETAIL, 
            Sector.ECOMMERCE, Sector.MANUFACTURING, Sector.MINING,
            Sector.TECHNOLOGY, Sector.HEALTHCARE
        ]
        
    def score_lead(self, lead: Lead) -> Lead:
        scores = {
            "company_size": self._score_company_size(lead),
            "digital_maturity": self._score_digital_maturity(lead),
            "cloud_usage": self._score_cloud_usage(lead),
            "sector_fit": self._score_sector_fit(lead)
        }
        
        # Calculate weighted total score
        total_score = sum(
            scores[key] * self.weights[key] 
            for key in scores
        )
        
        lead.score = round(total_score, 2)
        lead.score_details = scores
        
        return lead
    
    def _score_company_size(self, lead: Lead) -> float:
        if not lead.company_size:
            return 30  # Default score if size unknown
            
        size_scores = {
            CompanySize.MICRO: 10,
            CompanySize.SMALL: 30,
            CompanySize.MEDIUM: 60,
            CompanySize.LARGE: 90,
            CompanySize.ENTERPRISE: 100
        }
        
        return size_scores.get(lead.company_size, 30)
    
    def _score_digital_maturity(self, lead: Lead) -> float:
        score = 0
        
        # Check for website
        if lead.website:
            score += 20
            
        # Check for technology keywords
        tech_keywords = [
            "digital", "tech", "software", "cloud", "data",
            "analytics", "ai", "ml", "automation", "devops"
        ]
        
        if lead.technologies_used:
            tech_count = len(lead.technologies_used)
            score += min(tech_count * 10, 40)
            
        # Check cloud maturity level
        if lead.cloud_maturity:
            maturity_scores = {
                CloudMaturity.NONE: 0,
                CloudMaturity.EXPLORING: 20,
                CloudMaturity.ADOPTING: 40,
                CloudMaturity.MATURE: 60,
                CloudMaturity.NATIVE: 80
            }
            score = max(score, maturity_scores.get(lead.cloud_maturity, 0))
            
        # Check for digital transformation indicators
        if lead.notes:
            notes_lower = lead.notes.lower()
            for keyword in tech_keywords:
                if keyword in notes_lower:
                    score += 5
                    if score >= 100:
                        break
                        
        return min(score, 100)
    
    def _score_cloud_usage(self, lead: Lead) -> float:
        score = 0
        
        # Already using AWS - highest potential
        if lead.aws_usage:
            score = 100
            
        # Using competitor cloud - high migration potential
        elif lead.competitor_cloud:
            competitor_scores = {
                "azure": 80,
                "gcp": 80,
                "google cloud": 80,
                "ibm cloud": 70,
                "oracle cloud": 70,
                "alibaba": 60,
                "other": 50
            }
            score = competitor_scores.get(lead.competitor_cloud.lower(), 50)
            
        # Check for AWS service mentions
        elif lead.technologies_used:
            aws_services = sum(
                1 for tech in lead.technologies_used
                if any(aws in tech.lower() for aws in Config.AWS_SERVICES_KEYWORDS)
            )
            score = min(aws_services * 20, 80)
            
        # Check pain points that AWS could solve
        if lead.pain_points:
            aws_solvable = [
                "scalability", "performance", "cost", "reliability",
                "security", "compliance", "infrastructure", "deployment",
                "monitoring", "backup", "disaster recovery"
            ]
            
            pain_score = sum(
                10 for pain in lead.pain_points
                if any(keyword in pain.lower() for keyword in aws_solvable)
            )
            score = max(score, min(pain_score, 70))
            
        return score
    
    def _score_sector_fit(self, lead: Lead) -> float:
        if not lead.sector:
            return 40  # Default score if sector unknown
            
        # Perfect fit sectors
        if lead.sector in self.target_sectors:
            base_score = 80
            
            # Bonus for sectors matching Force One IT success cases
            success_sectors = {
                Sector.BANKING: 100,
                Sector.FINTECH: 95,
                Sector.RETAIL: 90,
                Sector.MINING: 90,
                Sector.TECHNOLOGY: 85,
                Sector.HEALTHCARE: 85,
                Sector.MANUFACTURING: 80,
                Sector.ECOMMERCE: 80
            }
            
            return success_sectors.get(lead.sector, base_score)
            
        # Other sectors
        return 40
    
    def score_batch(self, leads: List[Lead]) -> List[Lead]:
        scored_leads = []
        
        for lead in leads:
            try:
                scored_lead = self.score_lead(lead)
                scored_leads.append(scored_lead)
                logger.info(f"Scored {lead.company_name}: {scored_lead.score} ({scored_lead.calculate_priority()})")
            except Exception as e:
                logger.error(f"Error scoring lead {lead.company_name}: {e}")
                lead.score = 0
                scored_leads.append(lead)
                
        # Sort by score descending
        scored_leads.sort(key=lambda x: x.score, reverse=True)
        
        return scored_leads
    
    def get_recommendations(self, lead: Lead) -> List[str]:
        recommendations = []
        
        # Size-based recommendations
        if lead.company_size in [CompanySize.LARGE, CompanySize.ENTERPRISE]:
            recommendations.append("Enterprise-grade AWS solutions with dedicated support")
            recommendations.append("Cost optimization assessment for large-scale infrastructure")
            
        # Cloud maturity recommendations
        if lead.cloud_maturity == CloudMaturity.NONE:
            recommendations.append("Cloud readiness assessment and migration planning")
        elif lead.cloud_maturity == CloudMaturity.EXPLORING:
            recommendations.append("Proof of concept for key workloads")
        elif lead.cloud_maturity in [CloudMaturity.ADOPTING, CloudMaturity.MATURE]:
            recommendations.append("AWS Well-Architected Review")
            recommendations.append("Advanced services adoption (AI/ML, Analytics)")
            
        # Competitor migration
        if lead.competitor_cloud:
            recommendations.append(f"Migration assessment from {lead.competitor_cloud} to AWS")
            recommendations.append("TCO comparison and migration roadmap")
            
        # Sector-specific
        sector_recommendations = {
            Sector.BANKING: ["Compliance and security assessment", "High-availability architecture"],
            Sector.RETAIL: ["Scalable e-commerce infrastructure", "CDN and performance optimization"],
            Sector.HEALTHCARE: ["HIPAA compliance setup", "Secure data storage solutions"],
            Sector.MANUFACTURING: ["IoT and data analytics platform", "Supply chain optimization"]
        }
        
        if lead.sector in sector_recommendations:
            recommendations.extend(sector_recommendations[lead.sector])
            
        return recommendations[:5]  # Limit to top 5 recommendations