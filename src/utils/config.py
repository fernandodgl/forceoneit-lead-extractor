import os
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

class Config:
    BASE_DIR = Path(__file__).parent.parent.parent
    DATA_DIR = BASE_DIR / "data"
    CACHE_DIR = DATA_DIR / "cache"
    EXPORTS_DIR = DATA_DIR / "exports"
    LOGS_DIR = BASE_DIR / "logs"
    
    # API Keys
    GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")
    LINKEDIN_USERNAME = os.getenv("LINKEDIN_USERNAME", "")
    LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD", "")
    HUBSPOT_API_KEY = os.getenv("HUBSPOT_API_KEY", "")
    
    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR}/leads.db")
    
    # Search Parameters
    DEFAULT_SEARCH_RADIUS = int(os.getenv("DEFAULT_SEARCH_RADIUS", "50"))
    DEFAULT_RESULTS_LIMIT = int(os.getenv("DEFAULT_RESULTS_LIMIT", "100"))
    
    # Scoring Weights
    SCORING_WEIGHTS = {
        "company_size": float(os.getenv("WEIGHT_COMPANY_SIZE", "0.3")),
        "digital_maturity": float(os.getenv("WEIGHT_DIGITAL_MATURITY", "0.25")),
        "cloud_usage": float(os.getenv("WEIGHT_CLOUD_USAGE", "0.25")),
        "sector_fit": float(os.getenv("WEIGHT_SECTOR_FIT", "0.2"))
    }
    
    # Rate Limiting
    REQUESTS_PER_MINUTE = int(os.getenv("REQUESTS_PER_MINUTE", "30"))
    RETRY_ATTEMPTS = int(os.getenv("RETRY_ATTEMPTS", "3"))
    RETRY_DELAY = int(os.getenv("RETRY_DELAY", "5"))
    
    # Target Sectors
    TARGET_SECTORS = {
        "banking": ["banco", "bank", "financeira", "fintech", "pagamento", "payment"],
        "retail": ["varejo", "retail", "loja", "store", "ecommerce", "marketplace"],
        "manufacturing": ["indústria", "industrial", "manufatura", "fábrica", "factory"],
        "mining": ["mineração", "mining", "mineradora", "mineral"],
        "technology": ["tecnologia", "tech", "software", "ti", "it", "digital"],
        "healthcare": ["saúde", "health", "hospital", "clínica", "clinic", "médico", "pharma"]
    }
    
    # Company Size Thresholds
    COMPANY_SIZE_THRESHOLDS = {
        "micro": {"max_employees": 9, "max_revenue": 360000},
        "small": {"max_employees": 49, "max_revenue": 4800000},
        "medium": {"max_employees": 499, "max_revenue": 300000000},
        "large": {"max_employees": 4999, "max_revenue": 1000000000},
        "enterprise": {"max_employees": float('inf'), "max_revenue": float('inf')}
    }
    
    # AWS Services of Interest
    AWS_SERVICES_KEYWORDS = [
        "ec2", "s3", "rds", "lambda", "cloudfront", "elastic",
        "dynamodb", "redshift", "sagemaker", "ecs", "eks",
        "fargate", "aurora", "cloudwatch", "route53"
    ]
    
    # Success Case Companies (Force One IT clients)
    SUCCESS_CASES = [
        "Banco Inter", "BMG", "Localiza", "Carbel", "Kinross",
        "Horizonte Minerals", "Embaré", "Plena Alimentos",
        "TOTVS", "Sonda", "Unimed BH", "Hospital Biocor"
    ]
    
    @classmethod
    def get_all(cls) -> Dict[str, Any]:
        return {
            key: value for key, value in cls.__dict__.items()
            if not key.startswith("_") and not callable(value)
        }
    
    @classmethod
    def create_directories(cls):
        for dir_path in [cls.DATA_DIR, cls.CACHE_DIR, cls.EXPORTS_DIR, cls.LOGS_DIR]:
            dir_path.mkdir(parents=True, exist_ok=True)


Config.create_directories()