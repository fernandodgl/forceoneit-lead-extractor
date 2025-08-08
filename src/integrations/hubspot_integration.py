import requests
import json
from typing import List, Dict, Optional, Any
from datetime import datetime
import logging
from src.models.lead import Lead
from src.utils.config import Config

logger = logging.getLogger(__name__)


class HubSpotIntegration:
    """
    Integração com HubSpot CRM
    Sincroniza leads, contatos e empresas
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or Config.HUBSPOT_API_KEY
        self.base_url = "https://api.hubapi.com"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
    def test_connection(self) -> bool:
        """Testa conexão com HubSpot"""
        try:
            response = requests.get(
                f"{self.base_url}/crm/v3/objects/companies?limit=1",
                headers=self.headers
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"HubSpot connection failed: {e}")
            return False
            
    def create_or_update_company(self, lead: Lead) -> Optional[str]:
        """Cria ou atualiza empresa no HubSpot"""
        try:
            # Prepare company data
            properties = {
                "name": lead.company_name,
                "domain": self._extract_domain(lead.website) if lead.website else None,
                "phone": lead.phone,
                "city": lead.city,
                "state": lead.state,
                "country": "Brasil",
                "industry": lead.sector.value if lead.sector else None,
                "numberofemployees": lead.employee_count,
                "annualrevenue": lead.annual_revenue,
                "forceoneit_score": lead.score,
                "forceoneit_priority": lead.calculate_priority(),
                "aws_usage": "Yes" if lead.aws_usage else "No",
                "cloud_maturity": lead.cloud_maturity.value if lead.cloud_maturity else None,
                "competitor_cloud": lead.competitor_cloud,
                "cnpj": lead.cnpj,
                "website": lead.website,
                "linkedin_company_page": lead.linkedin_url,
                "description": self._build_company_description(lead)
            }
            
            # Remove None values
            properties = {k: v for k, v in properties.items() if v is not None}
            
            # Check if company exists
            existing_id = self._find_company_by_domain_or_name(
                lead.website, 
                lead.company_name
            )
            
            if existing_id:
                # Update existing
                response = requests.patch(
                    f"{self.base_url}/crm/v3/objects/companies/{existing_id}",
                    headers=self.headers,
                    json={"properties": properties}
                )
                
                if response.status_code == 200:
                    logger.info(f"Updated company {lead.company_name} in HubSpot")
                    return existing_id
                    
            else:
                # Create new
                response = requests.post(
                    f"{self.base_url}/crm/v3/objects/companies",
                    headers=self.headers,
                    json={"properties": properties}
                )
                
                if response.status_code == 201:
                    company_id = response.json()["id"]
                    logger.info(f"Created company {lead.company_name} in HubSpot")
                    return company_id
                    
        except Exception as e:
            logger.error(f"Error creating/updating company {lead.company_name}: {e}")
            
        return None
        
    def create_or_update_contact(self, lead: Lead, company_id: str) -> Optional[str]:
        """Cria ou atualiza contato no HubSpot"""
        if not lead.email:
            return None
            
        try:
            # For each decision maker
            contact_ids = []
            
            # Create primary contact if email exists
            if lead.email:
                primary_contact = {
                    "email": lead.email,
                    "company": lead.company_name,
                    "phone": lead.phone,
                    "city": lead.city,
                    "state": lead.state,
                    "forceoneit_lead_source": lead.source,
                    "forceoneit_extracted_at": lead.extracted_at.isoformat()
                }
                
                contact_id = self._create_contact(primary_contact, company_id)
                if contact_id:
                    contact_ids.append(contact_id)
                    
            # Create contacts for decision makers
            for dm in lead.decision_makers[:5]:  # Limit to 5
                if dm.get('email'):
                    dm_contact = {
                        "email": dm['email'],
                        "firstname": dm.get('name', '').split()[0] if dm.get('name') else None,
                        "lastname": ' '.join(dm.get('name', '').split()[1:]) if dm.get('name') else None,
                        "jobtitle": dm.get('role'),
                        "company": lead.company_name,
                        "linkedin_profile": dm.get('linkedin_url')
                    }
                    
                    contact_id = self._create_contact(dm_contact, company_id)
                    if contact_id:
                        contact_ids.append(contact_id)
                        
            return contact_ids[0] if contact_ids else None
            
        except Exception as e:
            logger.error(f"Error creating/updating contacts for {lead.company_name}: {e}")
            return None
            
    def _create_contact(self, contact_data: Dict, company_id: str) -> Optional[str]:
        """Helper para criar contato individual"""
        try:
            email = contact_data.get('email')
            if not email:
                return None
                
            # Check if contact exists
            search_response = requests.post(
                f"{self.base_url}/crm/v3/objects/contacts/search",
                headers=self.headers,
                json={
                    "filterGroups": [{
                        "filters": [{
                            "propertyName": "email",
                            "operator": "EQ",
                            "value": email
                        }]
                    }]
                }
            )
            
            # Filter None values
            properties = {k: v for k, v in contact_data.items() if v is not None}
            
            if search_response.status_code == 200 and search_response.json()["total"] > 0:
                # Update existing
                contact_id = search_response.json()["results"][0]["id"]
                requests.patch(
                    f"{self.base_url}/crm/v3/objects/contacts/{contact_id}",
                    headers=self.headers,
                    json={"properties": properties}
                )
            else:
                # Create new
                response = requests.post(
                    f"{self.base_url}/crm/v3/objects/contacts",
                    headers=self.headers,
                    json={"properties": properties}
                )
                
                if response.status_code == 201:
                    contact_id = response.json()["id"]
                else:
                    return None
                    
            # Associate with company
            if company_id and contact_id:
                self._associate_contact_to_company(contact_id, company_id)
                
            return contact_id
            
        except Exception as e:
            logger.error(f"Error creating contact: {e}")
            return None
            
    def _associate_contact_to_company(self, contact_id: str, company_id: str):
        """Associa contato à empresa"""
        try:
            requests.put(
                f"{self.base_url}/crm/v3/objects/contacts/{contact_id}/associations/companies/{company_id}/1",
                headers=self.headers
            )
        except Exception as e:
            logger.warning(f"Error associating contact to company: {e}")
            
    def create_deal(self, lead: Lead, company_id: str) -> Optional[str]:
        """Cria oportunidade/deal no HubSpot"""
        try:
            # Calculate deal value based on company size and AWS potential
            deal_value = self._estimate_deal_value(lead)
            
            properties = {
                "dealname": f"AWS Migration - {lead.company_name}",
                "pipeline": "default",  # Configure your pipeline ID
                "dealstage": self._get_deal_stage(lead),
                "amount": deal_value,
                "closedate": self._estimate_close_date(lead),
                "dealtype": "newbusiness",
                "forceoneit_score": lead.score,
                "forceoneit_priority": lead.calculate_priority(),
                "aws_services_potential": ', '.join(lead.technologies_used[:5]) if lead.technologies_used else None,
                "description": self._build_deal_description(lead)
            }
            
            # Remove None values
            properties = {k: v for k, v in properties.items() if v is not None}
            
            response = requests.post(
                f"{self.base_url}/crm/v3/objects/deals",
                headers=self.headers,
                json={"properties": properties}
            )
            
            if response.status_code == 201:
                deal_id = response.json()["id"]
                
                # Associate deal with company
                if company_id:
                    requests.put(
                        f"{self.base_url}/crm/v3/objects/deals/{deal_id}/associations/companies/{company_id}/5",
                        headers=self.headers
                    )
                    
                logger.info(f"Created deal for {lead.company_name} in HubSpot")
                return deal_id
                
        except Exception as e:
            logger.error(f"Error creating deal for {lead.company_name}: {e}")
            
        return None
        
    def sync_lead(self, lead: Lead, create_deal: bool = True) -> Dict[str, Any]:
        """Sincroniza lead completo com HubSpot"""
        results = {
            "success": False,
            "company_id": None,
            "contact_id": None,
            "deal_id": None,
            "errors": []
        }
        
        try:
            # Create/update company
            company_id = self.create_or_update_company(lead)
            if company_id:
                results["company_id"] = company_id
                
                # Create/update contacts
                contact_id = self.create_or_update_contact(lead, company_id)
                if contact_id:
                    results["contact_id"] = contact_id
                    
                # Create deal if qualified
                if create_deal and lead.score >= 60:  # Only for WARM and HOT leads
                    deal_id = self.create_deal(lead, company_id)
                    if deal_id:
                        results["deal_id"] = deal_id
                        
                results["success"] = True
            else:
                results["errors"].append("Failed to create company")
                
        except Exception as e:
            results["errors"].append(str(e))
            logger.error(f"Error syncing lead {lead.company_name}: {e}")
            
        return results
        
    def sync_batch(self, leads: List[Lead], create_deals: bool = True) -> List[Dict[str, Any]]:
        """Sincroniza múltiplos leads com HubSpot"""
        results = []
        
        for lead in leads:
            logger.info(f"Syncing {lead.company_name} to HubSpot...")
            result = self.sync_lead(lead, create_deals)
            results.append({
                "company_name": lead.company_name,
                **result
            })
            
        # Summary
        successful = sum(1 for r in results if r["success"])
        logger.info(f"Synced {successful}/{len(leads)} leads to HubSpot")
        
        return results
        
    def _find_company_by_domain_or_name(self, website: Optional[str], name: str) -> Optional[str]:
        """Busca empresa por domínio ou nome"""
        try:
            # Search by domain first
            if website:
                domain = self._extract_domain(website)
                response = requests.post(
                    f"{self.base_url}/crm/v3/objects/companies/search",
                    headers=self.headers,
                    json={
                        "filterGroups": [{
                            "filters": [{
                                "propertyName": "domain",
                                "operator": "EQ",
                                "value": domain
                            }]
                        }]
                    }
                )
                
                if response.status_code == 200 and response.json()["total"] > 0:
                    return response.json()["results"][0]["id"]
                    
            # Search by name
            response = requests.post(
                f"{self.base_url}/crm/v3/objects/companies/search",
                headers=self.headers,
                json={
                    "filterGroups": [{
                        "filters": [{
                            "propertyName": "name",
                            "operator": "EQ",
                            "value": name
                        }]
                    }]
                }
            )
            
            if response.status_code == 200 and response.json()["total"] > 0:
                return response.json()["results"][0]["id"]
                
        except Exception as e:
            logger.warning(f"Error searching company: {e}")
            
        return None
        
    def _extract_domain(self, website: str) -> str:
        """Extrai domínio do website"""
        from urllib.parse import urlparse
        
        if not website.startswith('http'):
            website = f'https://{website}'
            
        parsed = urlparse(website)
        return parsed.netloc.replace('www.', '')
        
    def _build_company_description(self, lead: Lead) -> str:
        """Constrói descrição da empresa"""
        desc = f"Empresa do setor {lead.sector.value if lead.sector else 'não identificado'}.\n"
        desc += f"Porte: {lead.company_size.value if lead.company_size else 'não identificado'}.\n"
        desc += f"Score Force One IT: {lead.score} ({lead.calculate_priority()}).\n"
        
        if lead.cloud_maturity:
            desc += f"Maturidade Cloud: {lead.cloud_maturity.value}.\n"
            
        if lead.aws_usage:
            desc += "Já utiliza AWS.\n"
        elif lead.competitor_cloud:
            desc += f"Utiliza cloud concorrente: {lead.competitor_cloud}.\n"
            
        if lead.pain_points:
            desc += f"Pain points identificados: {', '.join(lead.pain_points[:3])}.\n"
            
        return desc
        
    def _build_deal_description(self, lead: Lead) -> str:
        """Constrói descrição do deal"""
        desc = "Oportunidade de migração/otimização AWS.\n\n"
        
        # Add recommendations
        from src.scorers.lead_scorer import LeadScorer
        scorer = LeadScorer()
        recommendations = scorer.get_recommendations(lead)
        
        if recommendations:
            desc += "Recomendações:\n"
            for rec in recommendations:
                desc += f"• {rec}\n"
                
        return desc
        
    def _get_deal_stage(self, lead: Lead) -> str:
        """Determina estágio do deal baseado no score"""
        # Configure these based on your HubSpot pipeline
        if lead.score >= 80:
            return "qualifiedtobuy"
        elif lead.score >= 60:
            return "presentationscheduled"
        else:
            return "appointmentscheduled"
            
    def _estimate_deal_value(self, lead: Lead) -> float:
        """Estima valor do deal baseado no porte da empresa"""
        # Base values for AWS services (monthly)
        base_values = {
            "micro": 1000,
            "small": 5000,
            "medium": 20000,
            "large": 50000,
            "enterprise": 100000
        }
        
        monthly = base_values.get(
            lead.company_size.value if lead.company_size else "medium",
            10000
        )
        
        # Annual contract value
        return monthly * 12
        
    def _estimate_close_date(self, lead: Lead) -> str:
        """Estima data de fechamento baseada no score"""
        from datetime import datetime, timedelta
        
        # Days to close based on priority
        days_to_close = {
            "HOT": 30,
            "WARM": 60,
            "COOL": 90,
            "COLD": 120
        }
        
        priority = lead.calculate_priority()
        days = days_to_close.get(priority, 90)
        
        close_date = datetime.now() + timedelta(days=days)
        return close_date.strftime("%Y-%m-%d")