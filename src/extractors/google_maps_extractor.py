import time
from typing import List, Dict, Any, Optional
import googlemaps
from src.models.lead import Lead, Sector
from src.utils.config import Config
import logging

logger = logging.getLogger(__name__)


class GoogleMapsExtractor:
    def __init__(self):
        self.client = googlemaps.Client(key=Config.GOOGLE_MAPS_API_KEY) if Config.GOOGLE_MAPS_API_KEY else None
        self.rate_limit_delay = 60 / Config.REQUESTS_PER_MINUTE
        
    def search_companies(self, 
                        query: str, 
                        location: str = "Brasil",
                        radius: int = None,
                        sector: Optional[Sector] = None) -> List[Lead]:
        if not self.client:
            logger.error("Google Maps API key not configured")
            return []
            
        leads = []
        radius = radius or Config.DEFAULT_SEARCH_RADIUS * 1000
        
        try:
            # Build search query
            if sector:
                keywords = Config.TARGET_SECTORS.get(sector.value, [])
                for keyword in keywords:
                    search_query = f"{keyword} empresa {query}"
                    results = self._search_places(search_query, location, radius)
                    leads.extend(self._parse_results(results, sector))
                    time.sleep(self.rate_limit_delay)
            else:
                results = self._search_places(query, location, radius)
                leads = self._parse_results(results)
                
        except Exception as e:
            logger.error(f"Error searching Google Maps: {e}")
            
        return leads
    
    def _search_places(self, query: str, location: str, radius: int) -> List[Dict]:
        results = []
        
        # Get geocode for location
        geocode_result = self.client.geocode(location)
        if not geocode_result:
            return results
            
        lat_lng = geocode_result[0]["geometry"]["location"]
        
        # Search nearby places
        places_result = self.client.places_nearby(
            location=lat_lng,
            radius=radius,
            keyword=query,
            type="establishment"
        )
        
        results.extend(places_result.get("results", []))
        
        # Get additional pages if available
        while places_result.get("next_page_token"):
            time.sleep(2)  # Required delay for next page token
            places_result = self.client.places_nearby(
                page_token=places_result["next_page_token"]
            )
            results.extend(places_result.get("results", []))
            
            if len(results) >= Config.DEFAULT_RESULTS_LIMIT:
                break
                
        return results[:Config.DEFAULT_RESULTS_LIMIT]
    
    def _parse_results(self, results: List[Dict], sector: Optional[Sector] = None) -> List[Lead]:
        leads = []
        
        for place in results:
            try:
                # Get detailed place information
                place_details = self.client.place(
                    place["place_id"],
                    fields=["name", "formatted_address", "formatted_phone_number",
                           "website", "url", "types", "business_status"]
                )
                
                if place_details["status"] != "OK":
                    continue
                    
                details = place_details["result"]
                
                # Skip if business is not operational
                if details.get("business_status") != "OPERATIONAL":
                    continue
                
                lead = Lead(
                    company_name=details.get("name", ""),
                    address=details.get("formatted_address", ""),
                    phone=details.get("formatted_phone_number"),
                    website=details.get("website"),
                    sector=sector or self._infer_sector(details.get("types", [])),
                    source="Google Maps",
                    metadata={
                        "google_maps_url": details.get("url"),
                        "place_id": place["place_id"],
                        "types": details.get("types", [])
                    }
                )
                
                # Extract city and state from address
                if lead.address:
                    parts = lead.address.split(",")
                    if len(parts) >= 3:
                        lead.city = parts[-3].strip()
                        state_zip = parts[-2].strip().split()
                        if state_zip:
                            lead.state = state_zip[0]
                
                leads.append(lead)
                time.sleep(self.rate_limit_delay)
                
            except Exception as e:
                logger.warning(f"Error parsing place {place.get('name')}: {e}")
                continue
                
        return leads
    
    def _infer_sector(self, types: List[str]) -> Optional[Sector]:
        sector_mapping = {
            "bank": Sector.BANKING,
            "finance": Sector.BANKING,
            "store": Sector.RETAIL,
            "shopping_mall": Sector.RETAIL,
            "hospital": Sector.HEALTHCARE,
            "health": Sector.HEALTHCARE,
            "pharmacy": Sector.HEALTHCARE
        }
        
        for place_type in types:
            for key, sector in sector_mapping.items():
                if key in place_type.lower():
                    return sector
                    
        return None
    
    def get_company_details(self, company_name: str, location: str = None) -> Optional[Lead]:
        if not self.client:
            return None
            
        try:
            # Search for the company
            query = f"{company_name} {location}" if location else company_name
            results = self.client.places(query=query)
            
            if results["status"] == "OK" and results["results"]:
                place = results["results"][0]
                leads = self._parse_results([place])
                return leads[0] if leads else None
                
        except Exception as e:
            logger.error(f"Error getting company details: {e}")
            
        return None