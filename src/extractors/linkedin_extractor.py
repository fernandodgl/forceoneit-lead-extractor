import time
import json
import re
from typing import List, Dict, Optional, Any
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import logging
from src.models.lead import Lead, Sector, CompanySize
from src.utils.config import Config

logger = logging.getLogger(__name__)


class LinkedInExtractor:
    """
    Extrator do LinkedIn Sales Navigator
    Busca empresas e decision makers
    """
    
    def __init__(self):
        self.username = Config.LINKEDIN_USERNAME
        self.password = Config.LINKEDIN_PASSWORD
        self.driver = None
        self.is_logged_in = False
        self.rate_limit_delay = 3  # seconds between requests
        
    def _setup_driver(self):
        """Configura o driver do Selenium"""
        if self.driver:
            return
            
        options = Options()
        options.add_argument('--disable-bots')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        # Remove headless for LinkedIn (they detect it)
        # options.add_argument('--headless')
        
        # User agent to appear more human
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36')
        
        try:
            self.driver = webdriver.Chrome(options=options)
            self.driver.implicitly_wait(10)
        except Exception as e:
            logger.error(f"Failed to setup Chrome driver: {e}")
            raise
            
    def login(self) -> bool:
        """Faz login no LinkedIn"""
        if not self.username or not self.password:
            logger.error("LinkedIn credentials not configured")
            return False
            
        try:
            self._setup_driver()
            
            # Go to LinkedIn login
            self.driver.get("https://www.linkedin.com/login")
            time.sleep(2)
            
            # Fill credentials
            username_input = self.driver.find_element(By.ID, "username")
            password_input = self.driver.find_element(By.ID, "password")
            
            username_input.send_keys(self.username)
            time.sleep(1)
            password_input.send_keys(self.password)
            time.sleep(1)
            
            # Submit
            login_button = self.driver.find_element(By.XPATH, "//button[@type='submit']")
            login_button.click()
            
            # Wait for redirect
            WebDriverWait(self.driver, 15).until(
                EC.url_contains("linkedin.com/feed") or 
                EC.url_contains("linkedin.com/sales")
            )
            
            self.is_logged_in = True
            logger.info("Successfully logged in to LinkedIn")
            return True
            
        except Exception as e:
            logger.error(f"LinkedIn login failed: {e}")
            return False
            
    def search_companies(self, 
                        query: str,
                        sector: Optional[Sector] = None,
                        location: str = "Brasil",
                        company_size: Optional[str] = None,
                        limit: int = 50) -> List[Lead]:
        """Busca empresas no LinkedIn Sales Navigator"""
        
        if not self.is_logged_in and not self.login():
            return []
            
        leads = []
        
        try:
            # Navigate to Sales Navigator (if available)
            self.driver.get("https://www.linkedin.com/sales/search/company")
            time.sleep(3)
            
            # Build search URL with filters
            search_params = {
                'keywords': query,
                'geoUrn': self._get_geo_urn(location),
                'companySize': self._get_company_size_filter(company_size),
                'industry': self._get_industry_filter(sector)
            }
            
            # Remove None values
            search_params = {k: v for k, v in search_params.items() if v}
            
            # Perform search
            search_url = "https://www.linkedin.com/sales/search/company?" + "&".join([f"{k}={v}" for k, v in search_params.items()])
            self.driver.get(search_url)
            time.sleep(3)
            
            # Extract results
            page_count = 0
            max_pages = min(5, (limit // 10) + 1)  # LinkedIn shows ~10 results per page
            
            while page_count < max_pages and len(leads) < limit:
                # Wait for results to load
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "search-results-container"))
                )
                
                # Extract companies from current page
                company_cards = self.driver.find_elements(By.CSS_SELECTOR, "[data-test-search-result]")
                
                for card in company_cards:
                    if len(leads) >= limit:
                        break
                        
                    try:
                        lead = self._extract_company_from_card(card)
                        if lead:
                            leads.append(lead)
                            
                    except Exception as e:
                        logger.warning(f"Error extracting company card: {e}")
                        continue
                        
                # Try to go to next page
                try:
                    next_button = self.driver.find_element(By.CSS_SELECTOR, "[data-test-pagination-page-btn='next']")
                    if next_button.is_enabled():
                        next_button.click()
                        time.sleep(self.rate_limit_delay)
                        page_count += 1
                    else:
                        break
                except NoSuchElementException:
                    break
                    
        except Exception as e:
            logger.error(f"Error searching LinkedIn companies: {e}")
            
        logger.info(f"Extracted {len(leads)} companies from LinkedIn")
        return leads
        
    def _extract_company_from_card(self, card) -> Optional[Lead]:
        """Extrai dados da empresa do card do LinkedIn"""
        try:
            # Company name
            name_element = card.find_element(By.CSS_SELECTOR, "[data-test-search-result-title] a")
            company_name = name_element.text.strip()
            linkedin_url = name_element.get_attribute("href")
            
            # Industry/Sector
            sector = None
            try:
                industry_element = card.find_element(By.CSS_SELECTOR, "[data-test-search-result-subtitle]")
                industry_text = industry_element.text.strip().lower()
                sector = self._infer_sector_from_text(industry_text)
            except NoSuchElementException:
                pass
                
            # Location
            location = None
            try:
                location_element = card.find_element(By.CSS_SELECTOR, "[data-test-search-result-location]")
                location = location_element.text.strip()
            except NoSuchElementException:
                pass
                
            # Company size (employees)
            employee_count = None
            company_size = None
            try:
                size_element = card.find_element(By.CSS_SELECTOR, "[data-test-search-result-company-size]")
                size_text = size_element.text.strip()
                employee_count, company_size = self._parse_company_size(size_text)
            except NoSuchElementException:
                pass
                
            # Extract city and state from location
            city, state = self._parse_location(location)
            
            lead = Lead(
                company_name=company_name,
                city=city,
                state=state,
                sector=sector,
                company_size=company_size,
                employee_count=employee_count,
                linkedin_url=linkedin_url,
                source="LinkedIn Sales Navigator",
                metadata={
                    "linkedin_company_url": linkedin_url,
                    "raw_location": location,
                    "raw_industry": industry_text if 'industry_text' in locals() else None
                }
            )
            
            return lead
            
        except Exception as e:
            logger.warning(f"Error extracting company card: {e}")
            return None
            
    def find_decision_makers(self, company_name: str, 
                           company_linkedin_url: Optional[str] = None,
                           limit: int = 10) -> List[Dict[str, str]]:
        """Encontra decision makers de uma empresa"""
        
        if not self.is_logged_in:
            return []
            
        decision_makers = []
        
        try:
            # Search for people at the company
            search_params = {
                'keywords': ' '.join(self._get_decision_maker_titles()),
                'company': company_name,
                'geoUrn': self._get_geo_urn("Brasil")
            }
            
            people_search_url = "https://www.linkedin.com/sales/search/people?" + "&".join([f"{k}={v}" for k, v in search_params.items()])
            self.driver.get(people_search_url)
            time.sleep(3)
            
            # Extract people results
            people_cards = self.driver.find_elements(By.CSS_SELECTOR, "[data-test-search-result-person]")
            
            for card in people_cards[:limit]:
                try:
                    dm = self._extract_person_from_card(card)
                    if dm:
                        decision_makers.append(dm)
                        
                except Exception as e:
                    logger.warning(f"Error extracting person card: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error finding decision makers for {company_name}: {e}")
            
        return decision_makers
        
    def _extract_person_from_card(self, card) -> Optional[Dict[str, str]]:
        """Extrai dados de uma pessoa do card do LinkedIn"""
        try:
            # Name
            name_element = card.find_element(By.CSS_SELECTOR, "[data-test-search-result-person-name] a")
            name = name_element.text.strip()
            profile_url = name_element.get_attribute("href")
            
            # Title/Role
            title = None
            try:
                title_element = card.find_element(By.CSS_SELECTOR, "[data-test-search-result-person-title]")
                title = title_element.text.strip()
            except NoSuchElementException:
                pass
                
            # Company
            company = None
            try:
                company_element = card.find_element(By.CSS_SELECTOR, "[data-test-search-result-person-company]")
                company = company_element.text.strip()
            except NoSuchElementException:
                pass
                
            return {
                "name": name,
                "role": title,
                "company": company,
                "linkedin_url": profile_url,
                "source": "LinkedIn Sales Navigator"
            }
            
        except Exception as e:
            logger.warning(f"Error extracting person: {e}")
            return None
            
    def _get_decision_maker_titles(self) -> List[str]:
        """Retorna títulos de decision makers para busca"""
        return [
            "CEO", "CTO", "CIO", "CFO", "Diretor", "Gerente", 
            "VP", "Head", "Coordenador", "Supervisor"
        ]
        
    def _infer_sector_from_text(self, text: str) -> Optional[Sector]:
        """Infere setor baseado no texto da indústria"""
        text_lower = text.lower()
        
        sector_keywords = {
            Sector.BANKING: ["banco", "bank", "financeiro", "financial", "credit"],
            Sector.FINTECH: ["fintech", "payment", "pagamento", "digital bank"],
            Sector.RETAIL: ["retail", "varejo", "loja", "store", "commerce"],
            Sector.ECOMMERCE: ["ecommerce", "e-commerce", "marketplace", "online"],
            Sector.MANUFACTURING: ["manufatura", "manufacturing", "industrial", "fabrica"],
            Sector.MINING: ["mining", "mineracao", "mineral"],
            Sector.TECHNOLOGY: ["technology", "tecnologia", "software", "tech", "it"],
            Sector.HEALTHCARE: ["healthcare", "saude", "hospital", "medical", "pharma"]
        }
        
        for sector, keywords in sector_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                return sector
                
        return None
        
    def _parse_company_size(self, size_text: str) -> tuple[Optional[int], Optional[CompanySize]]:
        """Parse company size from LinkedIn text"""
        if not size_text:
            return None, None
            
        # Extract numbers from text like "501-1000 employees"
        numbers = re.findall(r'\d+', size_text.replace(',', ''))
        
        if numbers:
            # Use the upper bound if range is given
            max_employees = int(numbers[-1])
            
            # Determine size category
            if max_employees <= 10:
                return max_employees, CompanySize.MICRO
            elif max_employees <= 50:
                return max_employees, CompanySize.SMALL
            elif max_employees <= 500:
                return max_employees, CompanySize.MEDIUM
            elif max_employees <= 5000:
                return max_employees, CompanySize.LARGE
            else:
                return max_employees, CompanySize.ENTERPRISE
                
        return None, None
        
    def _parse_location(self, location: str) -> tuple[Optional[str], Optional[str]]:
        """Parse city and state from location string"""
        if not location:
            return None, None
            
        # Brazilian location patterns
        if "," in location:
            parts = location.split(",")
            if len(parts) >= 2:
                city = parts[0].strip()
                state_country = parts[1].strip()
                
                # Extract state (first part before any additional info)
                state = state_country.split()[0] if state_country else None
                
                return city, state
                
        return location, None
        
    def _get_geo_urn(self, location: str) -> str:
        """Get LinkedIn geo URN for location"""
        # Simplified - in production would use LinkedIn's location API
        location_mapping = {
            "Brasil": "103644278",
            "Brazil": "103644278",
            "São Paulo": "90009706",
            "Rio de Janeiro": "90009743"
        }
        
        return location_mapping.get(location, "103644278")  # Default to Brasil
        
    def _get_company_size_filter(self, size: Optional[str]) -> Optional[str]:
        """Get LinkedIn company size filter"""
        if not size:
            return None
            
        size_mapping = {
            "small": "B",      # 11-50
            "medium": "C,D",   # 51-200, 201-500
            "large": "E,F",    # 501-1000, 1001-5000
            "enterprise": "G"   # 5001+
        }
        
        return size_mapping.get(size)
        
    def _get_industry_filter(self, sector: Optional[Sector]) -> Optional[str]:
        """Get LinkedIn industry filter for sector"""
        if not sector:
            return None
            
        # LinkedIn industry IDs (simplified)
        industry_mapping = {
            Sector.BANKING: "43",        # Financial Services
            Sector.FINTECH: "43",        # Financial Services
            Sector.RETAIL: "27",         # Retail
            Sector.ECOMMERCE: "96",      # Internet
            Sector.MANUFACTURING: "25",  # Manufacturing
            Sector.MINING: "54",         # Mining & Metals
            Sector.TECHNOLOGY: "4",      # Computer Software
            Sector.HEALTHCARE: "14"      # Hospital & Health Care
        }
        
        return industry_mapping.get(sector)
        
    def close(self):
        """Fecha o driver do Selenium"""
        if self.driver:
            self.driver.quit()
            self.driver = None
            self.is_logged_in = False
            
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        
    def enrich_lead_with_linkedin_data(self, lead: Lead) -> Lead:
        """Enriquece lead com dados do LinkedIn"""
        if not self.is_logged_in:
            return lead
            
        try:
            # Find decision makers for the company
            decision_makers = self.find_decision_makers(lead.company_name)
            
            if decision_makers:
                # Add to existing decision makers
                lead.decision_makers.extend(decision_makers[:5])  # Limit to 5
                
                logger.info(f"Found {len(decision_makers)} decision makers for {lead.company_name}")
                
        except Exception as e:
            logger.error(f"Error enriching {lead.company_name} with LinkedIn: {e}")
            
        return lead