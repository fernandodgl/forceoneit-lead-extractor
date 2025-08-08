import requests
import time
from typing import Optional, Dict, Any
from validate_docbr import CNPJ
from src.models.lead import Lead, CompanySize
from src.utils.config import Config
import logging

logger = logging.getLogger(__name__)


class CNPJEnricher:
    def __init__(self):
        self.cnpj_validator = CNPJ()
        self.api_base_url = "https://receitaws.com.br/v1/cnpj"
        self.rate_limit_delay = 20  # ReceitaWS has strict rate limits
        
    def enrich_lead(self, lead: Lead) -> Lead:
        if not lead.cnpj:
            # Try to find CNPJ by company name
            lead.cnpj = self._search_cnpj(lead.company_name, lead.city, lead.state)
            
        if lead.cnpj:
            cnpj_data = self._fetch_cnpj_data(lead.cnpj)
            if cnpj_data:
                lead = self._update_lead_with_cnpj_data(lead, cnpj_data)
                
        return lead
    
    def _search_cnpj(self, company_name: str, city: str = None, state: str = None) -> Optional[str]:
        # This would integrate with a CNPJ search service
        # For now, returning None as placeholder
        logger.info(f"Searching CNPJ for {company_name}")
        return None
    
    def _fetch_cnpj_data(self, cnpj: str) -> Optional[Dict[str, Any]]:
        # Clean CNPJ
        cnpj_clean = ''.join(filter(str.isdigit, cnpj))
        
        if not self.cnpj_validator.validate(cnpj_clean):
            logger.warning(f"Invalid CNPJ: {cnpj}")
            return None
            
        try:
            response = requests.get(
                f"{self.api_base_url}/{cnpj_clean}",
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") != "ERROR":
                    return data
                else:
                    logger.warning(f"CNPJ API error: {data.get('message')}")
            elif response.status_code == 429:
                logger.warning("Rate limit exceeded for CNPJ API")
                time.sleep(60)  # Wait longer on rate limit
            else:
                logger.error(f"CNPJ API request failed: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching CNPJ data: {e}")
            
        return None
    
    def _update_lead_with_cnpj_data(self, lead: Lead, data: Dict[str, Any]) -> Lead:
        # Update basic information
        lead.company_name = data.get("nome", lead.company_name)
        lead.phone = lead.phone or data.get("telefone", "").split("/")[0].strip()
        lead.email = lead.email or data.get("email")
        
        # Update address
        lead.address = lead.address or self._format_address(data)
        lead.city = lead.city or data.get("municipio")
        lead.state = lead.state or data.get("uf")
        
        # Determine company size based on capital
        capital = data.get("capital_social", 0)
        if capital:
            lead.annual_revenue = float(capital)
            lead.company_size = self._determine_size_by_capital(capital)
            
        # Store additional metadata
        lead.metadata.update({
            "cnpj_situacao": data.get("situacao"),
            "cnpj_abertura": data.get("abertura"),
            "cnpj_atividade_principal": data.get("atividade_principal", [{}])[0].get("text"),
            "cnpj_natureza_juridica": data.get("natureza_juridica"),
            "cnpj_porte": data.get("porte"),
            "cnpj_qsa": data.get("qsa", [])
        })
        
        # Extract decision makers from QSA (board members)
        for member in data.get("qsa", [])[:5]:  # Limit to 5 members
            lead.decision_makers.append({
                "name": member.get("nome"),
                "role": member.get("qual"),
                "source": "CNPJ"
            })
            
        return lead
    
    def _format_address(self, data: Dict[str, Any]) -> str:
        parts = [
            data.get("logradouro"),
            data.get("numero"),
            data.get("complemento"),
            data.get("bairro"),
            data.get("municipio"),
            data.get("uf"),
            data.get("cep")
        ]
        return ", ".join(filter(None, parts))
    
    def _determine_size_by_capital(self, capital: float) -> CompanySize:
        thresholds = Config.COMPANY_SIZE_THRESHOLDS
        
        if capital <= thresholds["micro"]["max_revenue"]:
            return CompanySize.MICRO
        elif capital <= thresholds["small"]["max_revenue"]:
            return CompanySize.SMALL
        elif capital <= thresholds["medium"]["max_revenue"]:
            return CompanySize.MEDIUM
        elif capital <= thresholds["large"]["max_revenue"]:
            return CompanySize.LARGE
        else:
            return CompanySize.ENTERPRISE
    
    def validate_cnpj(self, cnpj: str) -> bool:
        cnpj_clean = ''.join(filter(str.isdigit, cnpj))
        return self.cnpj_validator.validate(cnpj_clean)