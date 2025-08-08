import re
import time
import requests
from typing import List, Dict, Optional, Tuple
from bs4 import BeautifulSoup
import logging
from src.models.lead import Lead
from src.utils.config import Config

logger = logging.getLogger(__name__)


class ContactExtractor:
    """
    Extrator de contatos B2B similar ao Lusha
    Busca emails, telefones e decision makers
    """
    
    def __init__(self):
        self.email_patterns = [
            r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
        ]
        self.phone_patterns = [
            r'\+?55[\s-]?\(?[1-9]{2}\)?[\s-]?9?[0-9]{4}[\s-]?[0-9]{4}',  # Brazilian mobile
            r'\+?55[\s-]?\(?[1-9]{2}\)?[\s-]?[2-5][0-9]{3}[\s-]?[0-9]{4}',  # Brazilian landline
            r'\(?[1-9]{2}\)?[\s-]?9?[0-9]{4}[\s-]?[0-9]{4}',  # Without country code
        ]
        self.decision_maker_titles = [
            # C-Level
            'CEO', 'CTO', 'CIO', 'CFO', 'COO', 'CMO', 'CISO', 'CDO',
            'Chief Executive', 'Chief Technology', 'Chief Information',
            'Chief Financial', 'Chief Operating', 'Chief Marketing',
            # Directors
            'Diretor', 'Director', 'Diretora', 'Head of', 
            'VP', 'Vice President', 'Vice-Presidente',
            # Managers
            'Gerente', 'Manager', 'Coordenador', 'Coordinator',
            'Supervisor', 'Lead', 'Líder',
            # IT Specific
            'Arquiteto', 'Architect', 'DevOps', 'SRE', 'Engenheiro',
            'Engineer', 'Infraestrutura', 'Infrastructure', 'Cloud',
            # Procurement
            'Compras', 'Procurement', 'Suprimentos', 'Supply'
        ]
        
    def extract_from_website(self, url: str) -> Dict[str, any]:
        """Extrai contatos do website da empresa"""
        if not url:
            return {}
            
        try:
            # Normalize URL
            if not url.startswith('http'):
                url = f'https://{url}'
                
            response = requests.get(url, timeout=10, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            
            if response.status_code != 200:
                return {}
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract emails
            emails = self._extract_emails(response.text)
            
            # Extract phones
            phones = self._extract_phones(response.text)
            
            # Look for contact pages
            contact_urls = self._find_contact_pages(soup, url)
            for contact_url in contact_urls[:2]:  # Limit to 2 pages
                try:
                    contact_response = requests.get(contact_url, timeout=10)
                    if contact_response.status_code == 200:
                        emails.extend(self._extract_emails(contact_response.text))
                        phones.extend(self._extract_phones(contact_response.text))
                except:
                    continue
                    
            # Extract social media links
            social_links = self._extract_social_links(soup)
            
            return {
                'emails': list(set(emails))[:5],  # Limit to 5 unique emails
                'phones': list(set(phones))[:5],  # Limit to 5 unique phones
                'social_links': social_links
            }
            
        except Exception as e:
            logger.warning(f"Error extracting from website {url}: {e}")
            return {}
            
    def _extract_emails(self, text: str) -> List[str]:
        """Extrai emails do texto"""
        emails = []
        for pattern in self.email_patterns:
            found = re.findall(pattern, text)
            emails.extend(found)
            
        # Filter out common non-contact emails
        filtered = []
        exclude = ['example', 'test', 'demo', 'noreply', 'no-reply', 
                  'info@', 'contact@', 'admin@', 'webmaster@']
        
        for email in emails:
            email_lower = email.lower()
            if not any(ex in email_lower for ex in exclude):
                # Prefer corporate emails
                if any(title in email_lower for title in ['sales', 'vendas', 'comercial', 'negocios']):
                    filtered.insert(0, email)  # Priority
                else:
                    filtered.append(email)
                    
        return filtered
        
    def _extract_phones(self, text: str) -> List[str]:
        """Extrai telefones do texto"""
        phones = []
        for pattern in self.phone_patterns:
            found = re.findall(pattern, text)
            phones.extend(found)
            
        # Clean and format phones
        cleaned = []
        for phone in phones:
            # Remove special characters
            clean = re.sub(r'[^\d+]', '', phone)
            if len(clean) >= 10:  # Valid phone length
                cleaned.append(self._format_phone(clean))
                
        return cleaned
        
    def _format_phone(self, phone: str) -> str:
        """Formata telefone para padrão brasileiro"""
        # Remove country code if present
        if phone.startswith('55'):
            phone = phone[2:]
        elif phone.startswith('+55'):
            phone = phone[3:]
            
        # Format as (XX) XXXXX-XXXX or (XX) XXXX-XXXX
        if len(phone) == 11:  # Mobile
            return f"({phone[:2]}) {phone[2:7]}-{phone[7:]}"
        elif len(phone) == 10:  # Landline
            return f"({phone[:2]}) {phone[2:6]}-{phone[6:]}"
        else:
            return phone
            
    def _find_contact_pages(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Encontra páginas de contato no site"""
        contact_urls = []
        keywords = ['contato', 'contact', 'fale-conosco', 'about', 'sobre', 
                   'quem-somos', 'team', 'equipe']
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            text = link.get_text().lower()
            
            if any(kw in text or kw in href.lower() for kw in keywords):
                # Build absolute URL
                if href.startswith('http'):
                    url = href
                elif href.startswith('/'):
                    url = base_url.rstrip('/') + href
                else:
                    url = base_url.rstrip('/') + '/' + href
                    
                if url not in contact_urls and url != base_url:
                    contact_urls.append(url)
                    
        return contact_urls
        
    def _extract_social_links(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extrai links de redes sociais"""
        social = {}
        platforms = {
            'linkedin': 'linkedin.com',
            'facebook': 'facebook.com',
            'twitter': 'twitter.com',
            'instagram': 'instagram.com',
            'youtube': 'youtube.com'
        }
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            for platform, domain in platforms.items():
                if domain in href and platform not in social:
                    social[platform] = href
                    
        return social
        
    def find_decision_makers_linkedin(self, company_name: str, 
                                     linkedin_url: Optional[str] = None) -> List[Dict[str, str]]:
        """
        Encontra decision makers via LinkedIn
        Nota: Implementação simplificada sem API oficial
        """
        decision_makers = []
        
        # This would require LinkedIn API or scraping
        # For now, returning structured placeholder
        logger.info(f"Searching decision makers for {company_name}")
        
        # In production, this would:
        # 1. Use LinkedIn Sales Navigator API
        # 2. Search for employees with decision-making titles
        # 3. Extract names, titles, and profile URLs
        
        return decision_makers
        
    def verify_email(self, email: str) -> Tuple[bool, float]:
        """
        Verifica validade e confiança do email
        Returns: (is_valid, confidence_score)
        """
        # Basic validation
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, email):
            return False, 0.0
            
        # Check domain exists
        domain = email.split('@')[1]
        try:
            import socket
            socket.gethostbyname(domain)
        except:
            return False, 0.0
            
        # Confidence scoring
        confidence = 0.5  # Base confidence
        
        # Corporate email patterns increase confidence
        corporate_patterns = ['firstname.lastname', 'f.lastname', 'firstname_lastname']
        local_part = email.split('@')[0].lower()
        
        if '.' in local_part or '_' in local_part:
            confidence += 0.2
            
        # Known corporate domains increase confidence
        if any(tld in domain for tld in ['.com.br', '.com', '.org', '.net']):
            confidence += 0.1
            
        # Generic emails decrease confidence  
        if local_part in ['info', 'contact', 'admin', 'sales']:
            confidence -= 0.3
            
        return True, min(max(confidence, 0.0), 1.0)
        
    def enrich_lead_contacts(self, lead: Lead) -> Lead:
        """Enriquece lead com informações de contato"""
        
        # Extract from website
        if lead.website:
            contact_data = self.extract_from_website(lead.website)
            
            # Add emails
            if contact_data.get('emails'):
                lead.email = lead.email or contact_data['emails'][0]
                lead.metadata['additional_emails'] = contact_data['emails']
                
                # Verify primary email
                is_valid, confidence = self.verify_email(lead.email)
                lead.metadata['email_confidence'] = confidence
                
            # Add phones
            if contact_data.get('phones'):
                lead.phone = lead.phone or contact_data['phones'][0]
                lead.metadata['additional_phones'] = contact_data['phones']
                
            # Add social links
            if contact_data.get('social_links'):
                lead.metadata['social_links'] = contact_data['social_links']
                lead.linkedin_url = contact_data['social_links'].get('linkedin')
                
        # Find decision makers
        if lead.company_name:
            decision_makers = self.find_decision_makers_linkedin(
                lead.company_name, 
                lead.linkedin_url
            )
            if decision_makers:
                lead.decision_makers.extend(decision_makers)
                
        return lead
        
    def extract_batch(self, leads: List[Lead]) -> List[Lead]:
        """Extrai contatos para múltiplos leads"""
        enriched_leads = []
        
        for lead in leads:
            try:
                enriched_lead = self.enrich_lead_contacts(lead)
                enriched_leads.append(enriched_lead)
                logger.info(f"Extracted contacts for {lead.company_name}")
                time.sleep(1)  # Rate limiting
            except Exception as e:
                logger.error(f"Error extracting contacts for {lead.company_name}: {e}")
                enriched_leads.append(lead)
                
        return enriched_leads