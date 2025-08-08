#!/usr/bin/env python3
"""
Setup HubSpot Integration
Guia para configurar HubSpot API
"""

import sys
from src.integrations.hubspot_integration import HubSpotIntegration
from src.models.lead import Lead, Sector, CompanySize

def show_hubspot_setup_guide():
    """Mostra guia de configuração do HubSpot"""
    print("=== SETUP HUBSPOT INTEGRATION ===")
    print()
    print("Para usar a integração HubSpot, você precisa de uma API Key.")
    print()
    print("PASSO A PASSO:")
    print("1. Acesse: https://app.hubspot.com/")
    print("2. Faça login na sua conta HubSpot")
    print("3. Vá em: Settings (ícone da engrenagem)")
    print("4. No menu lateral: Integrations > Private Apps")
    print("5. Clique 'Create private app'")
    print("6. Nome: 'Force One IT Lead Extractor'")
    print("7. Na aba 'Scopes', marque:")
    print("   - crm.objects.companies.read")
    print("   - crm.objects.companies.write") 
    print("   - crm.objects.contacts.read")
    print("   - crm.objects.contacts.write")
    print("   - crm.objects.deals.read")
    print("   - crm.objects.deals.write")
    print("8. Clique 'Create app'")
    print("9. Copie o 'Access token' (começa com 'pat-na1-...')")
    print("10. Cole no arquivo .env: HUBSPOT_API_KEY=sua_key_aqui")
    print()
    print("ALTERNATIVA RÁPIDA (Sandbox):")
    print("- Crie conta gratuita: https://developers.hubspot.com/get-started")
    print("- Teste com dados fictícios")
    print()

def test_hubspot_connection(api_key=None):
    """Testa conexão com HubSpot"""
    print("=== TESTE CONEXÃO HUBSPOT ===")
    
    if not api_key:
        print("API Key não fornecida")
        return False
    
    print(f"Testando API Key: {api_key[:10]}...")
    
    try:
        hubspot = HubSpotIntegration(api_key)
        
        if hubspot.test_connection():
            print("✅ HubSpot conectado com sucesso!")
            return True
        else:
            print("❌ Falha na conexão HubSpot")
            return False
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

def test_hubspot_sync():
    """Testa sincronização de leads com HubSpot"""
    print("=== TESTE SYNC HUBSPOT ===")
    
    # Create test lead
    test_lead = Lead(
        company_name="Empresa Teste ForceOneIT",
        website="https://www.teste.com.br",
        email="contato@teste.com.br",
        phone="(11) 99999-9999",
        city="São Paulo",
        state="SP",
        sector=Sector.TECHNOLOGY,
        company_size=CompanySize.MEDIUM,
        score=75.5,
        source="Test - Force One IT"
    )
    
    print(f"Lead de teste: {test_lead.company_name}")
    print(f"Score: {test_lead.score} ({test_lead.calculate_priority()})")
    
    try:
        hubspot = HubSpotIntegration()
        
        if not hubspot.test_connection():
            print("❌ HubSpot não conectado - configure API key primeiro")
            return False
        
        # Sync test lead
        result = hubspot.sync_lead(test_lead, create_deal=True)
        
        if result["success"]:
            print("✅ Lead sincronizado com sucesso!")
            print(f"   Company ID: {result['company_id']}")
            if result['contact_id']:
                print(f"   Contact ID: {result['contact_id']}")
            if result['deal_id']:
                print(f"   Deal ID: {result['deal_id']}")
        else:
            print("❌ Falha na sincronização")
            print(f"   Erros: {result['errors']}")
            
        return result["success"]
        
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        return False

def main():
    """Menu principal"""
    print("FORCE ONE IT - HUBSPOT SETUP")
    print("=" * 40)
    
    while True:
        print("\nOpções:")
        print("1. Mostrar guia de configuração")
        print("2. Testar conexão HubSpot")
        print("3. Teste completo de sincronização")
        print("4. Sair")
        
        try:
            choice = input("\nEscolha uma opção (1-4): ").strip()
            
            if choice == "1":
                show_hubspot_setup_guide()
                
            elif choice == "2":
                api_key = input("Digite sua HubSpot API Key (ou Enter para usar .env): ").strip()
                if not api_key:
                    api_key = None
                test_hubspot_connection(api_key)
                
            elif choice == "3":
                test_hubspot_sync()
                
            elif choice == "4":
                print("Saindo...")
                break
                
            else:
                print("Opção inválida")
                
        except KeyboardInterrupt:
            print("\nSaindo...")
            break
        except Exception as e:
            print(f"Erro: {e}")

if __name__ == "__main__":
    main()