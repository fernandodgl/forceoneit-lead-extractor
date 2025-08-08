import requests
from typing import List, Dict, Optional, Set
from bs4 import BeautifulSoup
import re
import logging
from src.models.lead import Lead, CloudMaturity
from src.utils.config import Config

logger = logging.getLogger(__name__)


class TechnographicsEnricher:
    """
    Enriquece leads com dados tecnográficos
    Identifica tecnologias usadas pelas empresas
    """
    
    def __init__(self):
        # Technology signatures to detect
        self.tech_signatures = {
            # Cloud Providers
            "aws": {
                "patterns": ["amazonaws.com", "aws-", "cloudfront.net", "elasticbeanstalk.com"],
                "headers": ["x-amz-", "x-amzn-"],
                "category": "cloud_provider"
            },
            "azure": {
                "patterns": ["azurewebsites.net", "blob.core.windows.net", "azure.com"],
                "headers": ["x-ms-"],
                "category": "cloud_provider"
            },
            "gcp": {
                "patterns": ["googleapis.com", "googleusercontent.com", "appspot.com"],
                "headers": ["x-goog-"],
                "category": "cloud_provider"
            },
            
            # Web Technologies
            "wordpress": {
                "patterns": ["/wp-content/", "/wp-includes/", "wordpress"],
                "headers": [],
                "category": "cms"
            },
            "magento": {
                "patterns": ["/skin/frontend/", "magento", "/customer/account/"],
                "headers": [],
                "category": "ecommerce"
            },
            "shopify": {
                "patterns": ["cdn.shopify.com", "myshopify.com"],
                "headers": [],
                "category": "ecommerce"
            },
            
            # Analytics
            "google_analytics": {
                "patterns": ["google-analytics.com", "gtag.js", "ga.js"],
                "headers": [],
                "category": "analytics"
            },
            "hotjar": {
                "patterns": ["hotjar.com"],
                "headers": [],
                "category": "analytics"
            },
            
            # CDN
            "cloudflare": {
                "patterns": ["cloudflare.com"],
                "headers": ["cf-ray", "cf-cache-status"],
                "category": "cdn"
            },
            "akamai": {
                "patterns": ["akamai.net"],
                "headers": ["x-akamai-"],
                "category": "cdn"
            },
            
            # Databases (indicators)
            "mongodb": {
                "patterns": ["mongodb"],
                "headers": [],
                "category": "database"
            },
            "mysql": {
                "patterns": ["mysql"],
                "headers": [],
                "category": "database"
            },
            "postgresql": {
                "patterns": ["postgresql", "postgres"],
                "headers": [],
                "category": "database"
            },
            
            # Frameworks
            "react": {
                "patterns": ["react", "_next", "jsx"],
                "headers": [],
                "category": "frontend"
            },
            "angular": {
                "patterns": ["ng-", "angular"],
                "headers": [],
                "category": "frontend"
            },
            "vue": {
                "patterns": ["vue", "v-"],
                "headers": [],
                "category": "frontend"
            },
            
            # Languages/Platforms
            "nodejs": {
                "patterns": ["express", "x-powered-by: Express"],
                "headers": [],
                "category": "backend"
            },
            "php": {
                "patterns": [".php", "x-powered-by: PHP"],
                "headers": [],
                "category": "backend"
            },
            "java": {
                "patterns": [".jsp", "java", "spring"],
                "headers": [],
                "category": "backend"
            },
            "dotnet": {
                "patterns": [".aspx", ".asp", "asp.net"],
                "headers": ["x-aspnet-version"],
                "category": "backend"
            }
        }
        
        # AWS service indicators
        self.aws_service_indicators = {
            "s3": ["s3.amazonaws.com", "s3-", "static content", "media storage"],
            "cloudfront": ["cloudfront.net", "cdn", "content delivery"],
            "ec2": ["compute", "server", "instances"],
            "rds": ["database", "mysql", "postgresql", "aurora"],
            "lambda": ["serverless", "functions", "api gateway"],
            "elastic_beanstalk": ["elasticbeanstalk.com", "eb-"],
            "ecs": ["container", "docker", "kubernetes"],
            "dynamodb": ["nosql", "dynamodb"],
            "redshift": ["data warehouse", "analytics", "bi"],
            "sagemaker": ["machine learning", "ml", "ai"]
        }
        
    def analyze_website_tech(self, url: str) -> Dict[str, any]:
        """Analisa tecnologias do website"""
        if not url:
            return {}
            
        try:
            if not url.startswith('http'):
                url = f'https://{url}'
                
            response = requests.get(url, timeout=10, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            
            if response.status_code != 200:
                return {}
                
            # Analyze response
            technologies = set()
            categories = {}
            aws_services = set()
            
            # Check headers
            for tech, config in self.tech_signatures.items():
                for header_pattern in config["headers"]:
                    for header_name, header_value in response.headers.items():
                        if header_pattern.lower() in header_name.lower() or \
                           header_pattern.lower() in str(header_value).lower():
                            technologies.add(tech)
                            categories[config["category"]] = categories.get(config["category"], [])
                            categories[config["category"]].append(tech)
                            
            # Check content
            content = response.text.lower()
            for tech, config in self.tech_signatures.items():
                for pattern in config["patterns"]:
                    if pattern.lower() in content:
                        technologies.add(tech)
                        categories[config["category"]] = categories.get(config["category"], [])
                        if tech not in categories[config["category"]]:
                            categories[config["category"]].append(tech)
                            
            # Check for AWS services
            for service, indicators in self.aws_service_indicators.items():
                for indicator in indicators:
                    if indicator.lower() in content:
                        aws_services.add(service)
                        
            # Parse HTML for meta tags and scripts
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Check meta generators
            meta_generator = soup.find('meta', attrs={'name': 'generator'})
            if meta_generator:
                content = meta_generator.get('content', '').lower()
                for tech in ["wordpress", "drupal", "joomla", "wix", "squarespace"]:
                    if tech in content:
                        technologies.add(tech)
                        categories["cms"] = categories.get("cms", [])
                        if tech not in categories["cms"]:
                            categories["cms"].append(tech)
                            
            # Check for specific JavaScript libraries
            scripts = soup.find_all('script', src=True)
            for script in scripts:
                src = script['src'].lower()
                if 'jquery' in src:
                    technologies.add('jquery')
                elif 'bootstrap' in src:
                    technologies.add('bootstrap')
                elif 'react' in src:
                    technologies.add('react')
                elif 'angular' in src:
                    technologies.add('angular')
                elif 'vue' in src:
                    technologies.add('vue')
                    
            return {
                "technologies": list(technologies),
                "categories": categories,
                "aws_services": list(aws_services),
                "tech_count": len(technologies)
            }
            
        except Exception as e:
            logger.warning(f"Error analyzing website tech for {url}: {e}")
            return {}
            
    def calculate_cloud_maturity(self, tech_data: Dict) -> CloudMaturity:
        """Calcula maturidade cloud baseada nas tecnologias"""
        
        if not tech_data.get("technologies"):
            return CloudMaturity.NONE
            
        cloud_providers = tech_data.get("categories", {}).get("cloud_provider", [])
        aws_services = tech_data.get("aws_services", [])
        
        # Already using cloud
        if cloud_providers:
            if "aws" in cloud_providers:
                if len(aws_services) >= 5:
                    return CloudMaturity.NATIVE
                elif len(aws_services) >= 2:
                    return CloudMaturity.MATURE
                else:
                    return CloudMaturity.ADOPTING
            else:
                # Using competitor cloud
                return CloudMaturity.ADOPTING
                
        # Check for cloud-ready indicators
        categories = tech_data.get("categories", {})
        
        # Has CDN, analytics, modern frameworks
        cloud_indicators = 0
        if "cdn" in categories:
            cloud_indicators += 1
        if "analytics" in categories:
            cloud_indicators += 1
        if "frontend" in categories and any(
            f in categories["frontend"] for f in ["react", "angular", "vue"]
        ):
            cloud_indicators += 1
            
        if cloud_indicators >= 2:
            return CloudMaturity.EXPLORING
        elif cloud_indicators >= 1:
            return CloudMaturity.EXPLORING
        else:
            return CloudMaturity.NONE
            
    def detect_migration_opportunities(self, tech_data: Dict) -> List[str]:
        """Detecta oportunidades de migração para AWS"""
        opportunities = []
        categories = tech_data.get("categories", {})
        
        # Using competitor cloud
        if "cloud_provider" in categories:
            providers = categories["cloud_provider"]
            if "azure" in providers or "gcp" in providers:
                opportunities.append("Migration from competitor cloud to AWS")
                
        # Using traditional hosting (no cloud)
        if "cloud_provider" not in categories and tech_data.get("tech_count", 0) > 0:
            opportunities.append("Cloud migration opportunity - currently on-premises or traditional hosting")
            
        # E-commerce without cloud
        if "ecommerce" in categories and "cloud_provider" not in categories:
            opportunities.append("E-commerce platform would benefit from AWS scalability")
            
        # Has database but no managed database service
        if "database" in categories and "rds" not in tech_data.get("aws_services", []):
            opportunities.append("Database migration to Amazon RDS for better management")
            
        # No CDN but has web presence
        if "cdn" not in categories and tech_data.get("tech_count", 0) > 3:
            opportunities.append("CloudFront CDN implementation for better performance")
            
        # Analytics without cloud
        if "analytics" in categories and "cloud_provider" not in categories:
            opportunities.append("Analytics workload migration to AWS for better insights")
            
        return opportunities
        
    def calculate_intent_signals(self, lead: Lead, tech_data: Dict) -> Dict[str, any]:
        """Calcula sinais de intenção de compra"""
        signals = {
            "score": 0,
            "indicators": [],
            "urgency": "low"
        }
        
        # Technology gaps
        if not tech_data.get("categories", {}).get("cloud_provider"):
            signals["score"] += 20
            signals["indicators"].append("No cloud provider detected - migration opportunity")
            
        # Using competitor
        categories = tech_data.get("categories", {})
        if "cloud_provider" in categories:
            providers = categories["cloud_provider"]
            if "aws" not in providers and providers:
                signals["score"] += 30
                signals["indicators"].append("Using competitor cloud - potential switch")
                
        # E-commerce or high-traffic site without CDN
        if "ecommerce" in categories and "cdn" not in categories:
            signals["score"] += 25
            signals["indicators"].append("E-commerce without CDN - performance opportunity")
            signals["urgency"] = "medium"
            
        # Multiple databases without cloud
        if "database" in categories and "cloud_provider" not in categories:
            signals["score"] += 15
            signals["indicators"].append("Database workloads not in cloud")
            
        # Modern tech stack (cloud-ready)
        if "frontend" in categories:
            modern_frameworks = ["react", "angular", "vue"]
            if any(f in categories["frontend"] for f in modern_frameworks):
                signals["score"] += 10
                signals["indicators"].append("Modern tech stack - cloud-ready")
                
        # Calculate urgency
        if signals["score"] >= 50:
            signals["urgency"] = "high"
        elif signals["score"] >= 30:
            signals["urgency"] = "medium"
            
        return signals
        
    def enrich_lead_technographics(self, lead: Lead) -> Lead:
        """Enriquece lead com dados tecnográficos"""
        
        if lead.website:
            # Analyze website technologies
            tech_data = self.analyze_website_tech(lead.website)
            
            if tech_data:
                # Store technologies
                lead.technologies_used = tech_data.get("technologies", [])
                
                # Calculate cloud maturity
                lead.cloud_maturity = self.calculate_cloud_maturity(tech_data)
                
                # Check AWS usage
                if "aws" in tech_data.get("technologies", []):
                    lead.aws_usage = True
                    
                # Check competitor clouds
                cloud_providers = tech_data.get("categories", {}).get("cloud_provider", [])
                for provider in cloud_providers:
                    if provider != "aws":
                        lead.competitor_cloud = provider
                        break
                        
                # Detect migration opportunities
                opportunities = self.detect_migration_opportunities(tech_data)
                if opportunities:
                    lead.pain_points.extend(opportunities[:3])  # Add top 3
                    
                # Calculate intent signals
                intent_signals = self.calculate_intent_signals(lead, tech_data)
                
                # Update metadata
                lead.metadata.update({
                    "technographics": tech_data,
                    "intent_signals": intent_signals,
                    "tech_categories": tech_data.get("categories", {}),
                    "aws_services_detected": tech_data.get("aws_services", [])
                })
                
                logger.info(f"Enriched technographics for {lead.company_name}: "
                          f"{len(lead.technologies_used)} technologies found")
                
        return lead
        
    def enrich_batch(self, leads: List[Lead]) -> List[Lead]:
        """Enriquece múltiplos leads com tecnografias"""
        enriched_leads = []
        
        for lead in leads:
            try:
                enriched_lead = self.enrich_lead_technographics(lead)
                enriched_leads.append(enriched_lead)
            except Exception as e:
                logger.error(f"Error enriching technographics for {lead.company_name}: {e}")
                enriched_leads.append(lead)
                
        return enriched_leads