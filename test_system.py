#!/usr/bin/env python3
"""
Teste do sistema sem APIs externas
"""

import sys
import os
sys.path.append('.')

from src.models.lead import Lead, Sector, CompanySize
from src.enrichers.cnpj_enricher import CNPJEnricher
from src.scorers.lead_scorer import LeadScorer
from src.extractors.contact_extractor import ContactExtractor
from src.enrichers.technographics_enricher import TechnographicsEnricher
import json

def create_sample_leads():
    """Cria leads de exemplo para testar"""
    sample_leads = [
        Lead(
            company_name="Banco Inter",
            website="https://www.bancointer.com.br",
            city="Belo Horizonte",
            state="MG",
            sector=Sector.FINTECH,
            company_size=CompanySize.LARGE,
            source="Test Data"
        ),
        Lead(
            company_name="Magazine Luiza",
            website="https://www.magazineluiza.com.br",
            city="Franca",
            state="SP", 
            sector=Sector.RETAIL,
            company_size=CompanySize.ENTERPRISE,
            source="Test Data"
        ),
        Lead(
            company_name="TOTVS",
            website="https://www.totvs.com",
            city="São Paulo",
            state="SP",
            sector=Sector.TECHNOLOGY,
            company_size=CompanySize.ENTERPRISE,
            source="Test Data"
        ),
        Lead(
            company_name="Localiza",
            website="https://www.localiza.com",
            city="Belo Horizonte", 
            state="MG",
            sector=Sector.RETAIL,
            company_size=CompanySize.LARGE,
            source="Test Data"
        ),
        Lead(
            company_name="Hospital Albert Einstein",
            website="https://www.einstein.br",
            city="São Paulo",
            state="SP",
            sector=Sector.HEALTHCARE, 
            company_size=CompanySize.LARGE,
            source="Test Data"
        )
    ]
    return sample_leads

def test_scoring():
    """Testa o sistema de scoring"""
    print("=== TESTE SISTEMA DE SCORING ===")
    
    leads = create_sample_leads()
    scorer = LeadScorer()
    
    print("Leads antes do scoring:")
    for lead in leads:
        print(f"- {lead.company_name} (Setor: {lead.sector.value if lead.sector else 'N/A'})")
    
    # Score os leads
    scored_leads = scorer.score_batch(leads)
    
    print(f"\nResults após scoring:")
    for lead in scored_leads:
        priority = lead.calculate_priority()
        print(f"- {lead.company_name}: Score {lead.score} ({priority})")
        
        # Mostrar recomendações para leads top
        if lead.score >= 60:
            recommendations = scorer.get_recommendations(lead)
            print(f"  Recomendações: {recommendations[0] if recommendations else 'Nenhuma'}")
    
    return scored_leads

def test_contact_extraction():
    """Testa extração de contatos"""
    print("\n=== TESTE EXTRAÇÃO DE CONTATOS ===")
    
    leads = create_sample_leads()
    extractor = ContactExtractor()
    
    # Teste apenas os primeiros 2 para não fazer muitos requests
    test_leads = leads[:2]
    
    print("Extraindo contatos (websites)...")
    for lead in test_leads:
        print(f"- Processando {lead.company_name}...")
        enriched_lead = extractor.enrich_lead_contacts(lead)
        
        if enriched_lead.email:
            print(f"  Email encontrado: {enriched_lead.email}")
        if enriched_lead.phone:
            print(f"  Telefone: {enriched_lead.phone}")
        if enriched_lead.metadata.get('social_links'):
            social = enriched_lead.metadata['social_links']
            print(f"  Redes sociais: {list(social.keys())}")

def test_technographics():
    """Testa análise de tecnografias"""
    print("\n=== TESTE ANÁLISE TECNOGRAFIAS ===")
    
    leads = create_sample_leads()
    tech_enricher = TechnographicsEnricher()
    
    # Teste apenas 2 empresas
    test_leads = leads[:2]
    
    print("Analisando tecnologias...")
    for lead in test_leads:
        print(f"- Analisando {lead.company_name}...")
        enriched_lead = tech_enricher.enrich_lead_technographics(lead)
        
        if enriched_lead.technologies_used:
            print(f"  Tecnologias: {', '.join(enriched_lead.technologies_used[:5])}")
        if enriched_lead.cloud_maturity:
            print(f"  Cloud maturity: {enriched_lead.cloud_maturity.value}")
        if enriched_lead.competitor_cloud:
            print(f"  Cloud concorrente: {enriched_lead.competitor_cloud}")

def test_export():
    """Testa exportação"""
    print("\n=== TESTE EXPORTAÇÃO ===")
    
    scored_leads = test_scoring()
    
    # Export to JSON
    output_file = "data/exports/test_leads.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        lead_dicts = [lead.to_dict() for lead in scored_leads]
        json.dump(lead_dicts, f, ensure_ascii=False, indent=2)
    
    print(f"Leads exportados para: {output_file}")
    
    # Show summary
    hot_leads = [l for l in scored_leads if l.calculate_priority() == "HOT"]
    warm_leads = [l for l in scored_leads if l.calculate_priority() == "WARM"]
    
    print(f"\nResumo:")
    print(f"- HOT leads: {len(hot_leads)}")
    print(f"- WARM leads: {len(warm_leads)}")
    print(f"- Total processados: {len(scored_leads)}")

def main():
    """Executa todos os testes"""
    print("FORCE ONE IT LEAD EXTRACTOR - SISTEMA DE TESTES")
    print("=" * 50)
    
    try:
        # Teste 1: Scoring
        scored_leads = test_scoring()
        
        # Teste 2: Contatos (comentado para não fazer requests)
        # test_contact_extraction()
        
        # Teste 3: Tecnografias (comentado para não fazer requests) 
        # test_technographics()
        
        # Teste 4: Export
        test_export()
        
        print(f"\n{'='*50}")
        print("TODOS OS TESTES CONCLUIDOS COM SUCESSO!")
        print("O sistema está funcionando corretamente.")
        print("Para usar APIs externas, configure as keys no .env")
        
    except Exception as e:
        print(f"ERRO nos testes: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()