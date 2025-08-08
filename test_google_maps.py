#!/usr/bin/env python3
"""
Teste da Google Maps API
"""

import googlemaps
from src.utils.config import Config

def test_google_maps_api():
    """Testa a Google Maps API"""
    print("=== TESTE GOOGLE MAPS API ===")
    
    api_key = Config.GOOGLE_MAPS_API_KEY
    if not api_key or api_key == "your_google_maps_api_key_here":
        print("❌ API Key não configurada")
        return False
    
    print(f"API Key: {api_key[:10]}...")
    
    try:
        # Initialize client
        gmaps = googlemaps.Client(key=api_key)
        
        # Test geocoding
        print("Testando Geocoding...")
        geocode_result = gmaps.geocode("São Paulo, Brasil")
        
        if geocode_result:
            print("✅ Geocoding funcionando")
            location = geocode_result[0]["geometry"]["location"]
            print(f"   São Paulo coordenadas: {location}")
        else:
            print("❌ Geocoding falhou")
            return False
            
        # Test Places API
        print("\nTestando Places API...")
        places_result = gmaps.places_nearby(
            location=location,
            radius=1000,
            keyword="tecnologia",
            type="establishment"
        )
        
        if places_result["status"] == "OK":
            print("✅ Places API funcionando")
            results_count = len(places_result.get("results", []))
            print(f"   Encontrados {results_count} lugares")
            
            # Show first result
            if results_count > 0:
                first_place = places_result["results"][0]
                print(f"   Exemplo: {first_place.get('name')}")
        else:
            print(f"❌ Places API falhou: {places_result['status']}")
            return False
            
        print("\n🎉 Google Maps API está funcionando perfeitamente!")
        return True
        
    except Exception as e:
        print(f"❌ Erro na API: {e}")
        
        if "REQUEST_DENIED" in str(e):
            print("\n🔧 SOLUÇÃO:")
            print("1. Acesse: https://console.cloud.google.com/apis/credentials")
            print("2. Clique na sua API Key")
            print("3. Em 'Application restrictions', selecione 'None'")
            print("4. OU adicione seu IP: 177.46.153.206")
            print("5. Salve e teste novamente")
            
        return False

if __name__ == "__main__":
    test_google_maps_api()