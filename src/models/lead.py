from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum


class CompanySize(Enum):
    MICRO = "micro"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    ENTERPRISE = "enterprise"


class Sector(Enum):
    BANKING = "banking"
    FINTECH = "fintech"
    RETAIL = "retail"
    ECOMMERCE = "ecommerce"
    MANUFACTURING = "manufacturing"
    MINING = "mining"
    TECHNOLOGY = "technology"
    HEALTHCARE = "healthcare"
    OTHER = "other"


class CloudMaturity(Enum):
    NONE = "none"
    EXPLORING = "exploring"
    ADOPTING = "adopting"
    MATURE = "mature"
    NATIVE = "native"


@dataclass
class Lead:
    company_name: str
    cnpj: Optional[str] = None
    website: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    sector: Optional[Sector] = None
    company_size: Optional[CompanySize] = None
    employee_count: Optional[int] = None
    annual_revenue: Optional[float] = None
    linkedin_url: Optional[str] = None
    decision_makers: List[Dict[str, str]] = field(default_factory=list)
    technologies_used: List[str] = field(default_factory=list)
    cloud_maturity: Optional[CloudMaturity] = None
    aws_usage: bool = False
    competitor_cloud: Optional[str] = None
    pain_points: List[str] = field(default_factory=list)
    score: float = 0.0
    score_details: Dict[str, float] = field(default_factory=dict)
    notes: Optional[str] = None
    source: Optional[str] = None
    extracted_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "company_name": self.company_name,
            "cnpj": self.cnpj,
            "website": self.website,
            "email": self.email,
            "phone": self.phone,
            "address": self.address,
            "city": self.city,
            "state": self.state,
            "sector": self.sector.value if self.sector else None,
            "company_size": self.company_size.value if self.company_size else None,
            "employee_count": self.employee_count,
            "annual_revenue": self.annual_revenue,
            "linkedin_url": self.linkedin_url,
            "decision_makers": self.decision_makers,
            "technologies_used": self.technologies_used,
            "cloud_maturity": self.cloud_maturity.value if self.cloud_maturity else None,
            "aws_usage": self.aws_usage,
            "competitor_cloud": self.competitor_cloud,
            "pain_points": self.pain_points,
            "score": self.score,
            "score_details": self.score_details,
            "notes": self.notes,
            "source": self.source,
            "extracted_at": self.extracted_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Lead":
        if "sector" in data and data["sector"]:
            data["sector"] = Sector(data["sector"])
        if "company_size" in data and data["company_size"]:
            data["company_size"] = CompanySize(data["company_size"])
        if "cloud_maturity" in data and data["cloud_maturity"]:
            data["cloud_maturity"] = CloudMaturity(data["cloud_maturity"])
        if "extracted_at" in data and isinstance(data["extracted_at"], str):
            data["extracted_at"] = datetime.fromisoformat(data["extracted_at"])
        if "updated_at" in data and isinstance(data["updated_at"], str):
            data["updated_at"] = datetime.fromisoformat(data["updated_at"])
        return cls(**data)
    
    def calculate_priority(self) -> str:
        if self.score >= 80:
            return "HOT"
        elif self.score >= 60:
            return "WARM"
        elif self.score >= 40:
            return "COOL"
        else:
            return "COLD"