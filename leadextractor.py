#!/usr/bin/env python3

import click
import pandas as pd
from pathlib import Path
from datetime import datetime
import logging
from typing import List, Optional
from src.models.lead import Lead, Sector
from src.extractors.google_maps_extractor import GoogleMapsExtractor
from src.extractors.contact_extractor import ContactExtractor
from src.enrichers.cnpj_enricher import CNPJEnricher
from src.enrichers.technographics_enricher import TechnographicsEnricher
from src.scorers.lead_scorer import LeadScorer
from src.integrations.hubspot_integration import HubSpotIntegration
from src.extractors.linkedin_extractor import LinkedInExtractor
from src.monitors.job_change_monitor import JobChangeMonitor
from src.compliance.lgpd_compliance import LGPDComplianceManager
from src.ai.prospect_playlists import ProspectPlaylistAI
from src.utils.config import Config
import json

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Config.LOGS_DIR / 'leadextractor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@click.group()
def cli():
    """ForceOneIT Lead Extractor - Find and qualify B2B leads for AWS solutions"""
    pass


@cli.command()
@click.option('--sector', type=click.Choice(['banking', 'retail', 'manufacturing', 'mining', 'technology', 'healthcare', 'all']), 
              default='all', help='Target sector')
@click.option('--location', default='São Paulo, Brasil', help='Search location')
@click.option('--radius', type=int, default=50, help='Search radius in km')
@click.option('--limit', type=int, default=100, help='Maximum results')
@click.option('--output', default='leads.json', help='Output file')
def extract(sector, location, radius, limit, output):
    """Extract leads from various sources"""
    click.echo(f"Extracting {sector} leads from {location}...")
    
    leads = []
    
    # Google Maps extraction
    maps_extractor = GoogleMapsExtractor()
    
    if sector == 'all':
        for s in ['banking', 'retail', 'manufacturing', 'mining', 'technology', 'healthcare']:
            sector_enum = Sector[s.upper()]
            sector_leads = maps_extractor.search_companies(
                query=s,
                location=location,
                radius=radius,
                sector=sector_enum
            )
            leads.extend(sector_leads)
            click.echo(f"  Found {len(sector_leads)} {s} companies")
    else:
        sector_enum = Sector[sector.upper()]
        leads = maps_extractor.search_companies(
            query=sector,
            location=location,
            radius=radius,
            sector=sector_enum
        )
        
    # Limit results
    leads = leads[:limit]
    
    # Save to file
    output_path = Config.EXPORTS_DIR / output
    with open(output_path, 'w', encoding='utf-8') as f:
        lead_dicts = [lead.to_dict() for lead in leads]
        json.dump(lead_dicts, f, ensure_ascii=False, indent=2)
        
    click.echo(f"Extracted {len(leads)} leads saved to {output_path}")
    return leads


@cli.command()
@click.option('--input', 'input_file', required=True, help='Input file with leads')
@click.option('--output', default='enriched_leads.json', help='Output file')
@click.option('--contacts/--no-contacts', default=True, help='Extract contact information')
@click.option('--technographics/--no-technographics', default=True, help='Analyze technographics')
def enrich(input_file, output, contacts, technographics):
    """Enrich leads with additional data"""
    click.echo(f"Enriching leads from {input_file}...")
    
    # Load leads
    input_path = Config.EXPORTS_DIR / input_file
    with open(input_path, 'r', encoding='utf-8') as f:
        lead_dicts = json.load(f)
        leads = [Lead.from_dict(lead_dict) for lead_dict in lead_dicts]
        
    # Enrich with CNPJ data
    click.echo("  📋 Enriching with CNPJ data...")
    cnpj_enricher = CNPJEnricher()
    enriched_leads = []
    
    for lead in leads:
        try:
            enriched_lead = cnpj_enricher.enrich_lead(lead)
            enriched_leads.append(enriched_lead)
        except Exception as e:
            logger.error(f"Error enriching CNPJ for {lead.company_name}: {e}")
            enriched_leads.append(lead)
            
    # Extract contacts
    if contacts:
        click.echo("  📧 Extracting contact information...")
        contact_extractor = ContactExtractor()
        enriched_leads = contact_extractor.extract_batch(enriched_leads)
        
    # Analyze technographics
    if technographics:
        click.echo("  💻 Analyzing technographics...")
        tech_enricher = TechnographicsEnricher()
        enriched_leads = tech_enricher.enrich_batch(enriched_leads)
                
    # Save enriched leads
    output_path = Config.EXPORTS_DIR / output
    with open(output_path, 'w', encoding='utf-8') as f:
        lead_dicts = [lead.to_dict() for lead in enriched_leads]
        json.dump(lead_dicts, f, ensure_ascii=False, indent=2)
        
    click.echo(f"✅ Enriched {len(enriched_leads)} leads saved to {output_path}")
    return enriched_leads


@cli.command()
@click.option('--input', 'input_file', required=True, help='Input file with leads')
@click.option('--output', default='scored_leads.json', help='Output file')
@click.option('--format', 'output_format', type=click.Choice(['json', 'csv', 'excel']), 
              default='excel', help='Output format')
def score(input_file, output, output_format):
    """Calculate qualification score for leads"""
    click.echo(f"📊 Scoring leads from {input_file}...")
    
    # Load leads
    input_path = Config.EXPORTS_DIR / input_file
    with open(input_path, 'r', encoding='utf-8') as f:
        lead_dicts = json.load(f)
        leads = [Lead.from_dict(lead_dict) for lead_dict in lead_dicts]
        
    # Score leads
    scorer = LeadScorer()
    scored_leads = scorer.score_batch(leads)
    
    # Prepare output
    output_path = Config.EXPORTS_DIR / output.replace('.json', f'.{output_format}')
    
    if output_format == 'json':
        with open(output_path, 'w', encoding='utf-8') as f:
            lead_dicts = [lead.to_dict() for lead in scored_leads]
            json.dump(lead_dicts, f, ensure_ascii=False, indent=2)
            
    elif output_format in ['csv', 'excel']:
        # Convert to DataFrame
        df_data = []
        for lead in scored_leads:
            row = {
                'Empresa': lead.company_name,
                'CNPJ': lead.cnpj,
                'Website': lead.website,
                'Email': lead.email,
                'Telefone': lead.phone,
                'Cidade': lead.city,
                'Estado': lead.state,
                'Setor': lead.sector.value if lead.sector else '',
                'Porte': lead.company_size.value if lead.company_size else '',
                'Score': lead.score,
                'Prioridade': lead.calculate_priority(),
                'Usa AWS': 'Sim' if lead.aws_usage else 'Não',
                'Cloud Competidor': lead.competitor_cloud or '',
                'Fonte': lead.source
            }
            df_data.append(row)
            
        df = pd.DataFrame(df_data)
        
        if output_format == 'csv':
            df.to_csv(output_path, index=False, encoding='utf-8-sig')
        else:  # excel
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Leads', index=False)
                
                # Add formatting
                worksheet = writer.sheets['Leads']
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
                    
    # Print summary
    click.echo("\n📈 Scoring Summary:")
    priorities = {}
    for lead in scored_leads:
        priority = lead.calculate_priority()
        priorities[priority] = priorities.get(priority, 0) + 1
        
    for priority in ['HOT', 'WARM', 'COOL', 'COLD']:
        count = priorities.get(priority, 0)
        emoji = {'HOT': '🔥', 'WARM': '☀️', 'COOL': '❄️', 'COLD': '🧊'}[priority]
        click.echo(f"  {emoji} {priority}: {count} leads")
        
    click.echo(f"\n✅ Scored {len(scored_leads)} leads saved to {output_path}")
    
    # Show top 5 leads
    click.echo("\n🏆 Top 5 Leads:")
    for i, lead in enumerate(scored_leads[:5], 1):
        click.echo(f"  {i}. {lead.company_name} - Score: {lead.score} ({lead.calculate_priority()})")
        

@cli.command()
@click.option('--input', 'input_file', required=True, help='Input file with scored leads')
@click.option('--create-deals/--no-deals', default=True, help='Create deals for qualified leads')
@click.option('--min-score', type=float, default=60.0, help='Minimum score to sync (default: 60)')
def sync_hubspot(input_file, create_deals, min_score):
    """Sync leads to HubSpot CRM"""
    click.echo(f"🔄 Syncing leads to HubSpot...")
    
    # Check HubSpot connection
    hubspot = HubSpotIntegration()
    if not hubspot.test_connection():
        click.echo("❌ Failed to connect to HubSpot. Check your API key in .env")
        return
        
    # Load leads
    input_path = Config.EXPORTS_DIR / input_file
    with open(input_path, 'r', encoding='utf-8') as f:
        lead_dicts = json.load(f)
        leads = [Lead.from_dict(lead_dict) for lead_dict in lead_dicts]
        
    # Filter by score
    qualified_leads = [lead for lead in leads if lead.score >= min_score]
    click.echo(f"  Found {len(qualified_leads)} qualified leads (score >= {min_score})")
    
    # Sync to HubSpot
    results = hubspot.sync_batch(qualified_leads, create_deals)
    
    # Show results
    successful = sum(1 for r in results if r["success"])
    click.echo(f"\n✅ Synced {successful}/{len(qualified_leads)} leads to HubSpot")
    
    # Show errors if any
    errors = [r for r in results if not r["success"]]
    if errors:
        click.echo("\n⚠️ Errors:")
        for error in errors[:5]:  # Show first 5 errors
            click.echo(f"  - {error['company_name']}: {error['errors']}")
            

@cli.command()
@click.option('--sector', type=click.Choice(['banking', 'retail', 'manufacturing', 'mining', 'technology', 'healthcare', 'all']), 
              default='all', help='Target sector')
@click.option('--location', default='São Paulo, Brasil', help='Search location')
@click.option('--export', type=click.Choice(['json', 'csv', 'excel']), default='excel', help='Export format')
@click.option('--sync-hubspot/--no-sync', default=False, help='Sync to HubSpot CRM')
def pipeline(sector, location, export, sync_hubspot):
    """Run complete pipeline: extract -> enrich -> score"""
    click.echo("🚀 Running complete lead extraction pipeline...\n")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Step 1: Extract
    click.echo("Step 1/3: Extracting leads...")
    extract_file = f"raw_leads_{timestamp}.json"
    ctx = click.Context(extract)
    ctx.invoke(extract, sector=sector, location=location, output=extract_file)
    
    # Step 2: Enrich
    click.echo("\nStep 2/3: Enriching leads...")
    enrich_file = f"enriched_leads_{timestamp}.json"
    ctx = click.Context(enrich)
    ctx.invoke(enrich, input_file=extract_file, output=enrich_file)
    
    # Step 3: Score
    click.echo("\nStep 3/3: Scoring leads...")
    score_file = f"scored_leads_{timestamp}"
    ctx = click.Context(score)
    ctx.invoke(score, input_file=enrich_file, output=score_file, output_format=export)
    
    # Step 4: Sync to HubSpot (optional)
    if sync_hubspot:
        click.echo("\nStep 4/4: Syncing to HubSpot...")
        ctx = click.Context(sync_hubspot)
        ctx.invoke(sync_hubspot, input_file=f"{score_file}.json", create_deals=True, min_score=60.0)
    
    click.echo("\n🎉 Pipeline completed successfully!")
    click.echo(f"📁 Final output: {Config.EXPORTS_DIR / score_file}.{export}")


@cli.command()
@click.option('--days', type=int, default=7, help='Days to check for changes')
@click.option('--limit', type=int, default=50, help='Maximum contacts to check')
def monitor_job_changes(days, limit):
    """Monitor job changes of tracked contacts"""
    click.echo(f"🔍 Monitoring job changes for last {days} days...")
    
    monitor = JobChangeMonitor()
    
    # Check for recent changes
    changes = monitor.check_job_changes(max_contacts=limit)
    
    if changes:
        click.echo(f"\n📈 Found {len(changes)} job changes:")
        for change in changes[:10]:  # Show first 10
            click.echo(f"  • {change['name']}: {change['previous_company']} → {change['new_company']}")
            click.echo(f"    Score: {change['opportunity_score']}")
            
        # Generate alerts
        alerts = monitor.generate_opportunity_alerts(changes)
        high_priority = [a for a in alerts if a['priority'] == 'HIGH']
        
        if high_priority:
            click.echo(f"\n🚨 {len(high_priority)} HIGH PRIORITY alerts:")
            for alert in high_priority:
                click.echo(f"  🔥 {alert['contact_name']}: {alert['message']}")
    else:
        click.echo("No job changes detected.")
        

@cli.command()
@click.option('--email', prompt=True, help='Email to check/update consent')
@click.option('--status', type=click.Choice(['legitimate_interest', 'consent', 'revoked']), 
              default='legitimate_interest', help='Consent status')
def manage_consent(email, status):
    """Manage LGPD consent for data subjects"""
    click.echo(f"🛡️ Managing LGPD consent for {email}...")
    
    compliance = LGPDComplianceManager()
    
    # Check current status
    current = compliance.check_consent_status(email)
    if current:
        click.echo(f"Current status: {current['consent_status']}")
        
    # Update consent
    success = compliance.update_consent(email, status, "cli")
    
    if success:
        click.echo(f"✅ Updated consent status to: {status}")
    else:
        click.echo("❌ Failed to update consent")


@cli.command()
def compliance_report():
    """Generate LGPD compliance report"""
    click.echo("📊 Generating LGPD compliance report...")
    
    compliance = LGPDComplianceManager()
    report = compliance.generate_compliance_report()
    
    if report:
        click.echo(f"\n📈 Compliance Summary:")
        click.echo(f"  Total data subjects: {report['data_subjects']['total']}")
        
        for status, count in report['data_subjects']['by_consent_status'].items():
            click.echo(f"    {status}: {count}")
            
        click.echo(f"  Processing activities: {report['processing_activities']}")
        
        if report['retention_compliance']['action_required']:
            click.echo(f"⚠️  {report['retention_compliance']['expired_subjects']} subjects need data retention action")
            
        click.echo("\n💡 Recommendations:")
        for rec in report['recommendations'][:3]:
            click.echo(f"  • {rec}")
    else:
        click.echo("❌ Failed to generate report")


@cli.command()
@click.option('--user-id', default='default', help='User ID for personalized recommendations')
@click.option('--limit', type=int, default=10, help='Number of recommendations')
def daily_recommendations(user_id, limit):
    """Get AI-powered daily lead recommendations"""
    click.echo(f"🤖 Getting daily recommendations for {user_id}...")
    
    playlists_ai = ProspectPlaylistAI()
    recommendations = playlists_ai.get_daily_recommendations(user_id, limit)
    
    if recommendations:
        click.echo(f"\n📋 {len(recommendations)} Recommendations:")
        for i, rec in enumerate(recommendations, 1):
            lead = rec['lead']
            click.echo(f"\n{i}. {lead['company_name']} (Score: {rec['score']})")
            click.echo(f"   {rec['reasoning']}")
            click.echo(f"   Actions: {', '.join(rec['suggested_actions'][:2])}")
    else:
        click.echo("No recommendations available")


@cli.command()
@click.option('--user-id', default='default', help='User ID')
def playlist_recommendations(user_id):
    """Get AI-powered playlist recommendations"""
    click.echo(f"📚 Getting playlist recommendations for {user_id}...")
    
    playlists_ai = ProspectPlaylistAI()
    recommendations = playlists_ai.generate_ai_recommendations(user_id)
    
    click.echo(f"\n🎯 {len(recommendations)} Smart Playlists recommended:")
    for i, rec in enumerate(recommendations, 1):
        click.echo(f"\n{i}. {rec['name']}")
        click.echo(f"   {rec['description']}")
        click.echo(f"   Estimated leads: {rec['estimated_leads']}")
        click.echo(f"   Confidence: {rec['confidence']:.0%}")
        click.echo(f"   Reasoning: {rec['reasoning']}")


@cli.command()
@click.option('--host', default='0.0.0.0', help='Host to run API server')
@click.option('--port', type=int, default=5000, help='Port to run API server')
@click.option('--debug/--no-debug', default=False, help='Run in debug mode')
def start_api(host, port, debug):
    """Start the REST API server"""
    click.echo(f"Starting API server on {host}:{port}...")
    click.echo("API Documentation available at endpoints:")
    click.echo("  GET  /health - Health check")
    click.echo("  POST /api/v1/extract/companies - Extract companies")
    click.echo("  POST /api/v1/enrich/company - Enrich single company")
    click.echo("  POST /api/v1/score/company - Score company")
    click.echo("  POST /api/v1/pipeline/complete - Complete pipeline")
    click.echo("  POST /api/v1/hubspot/sync - Sync to HubSpot")
    
    from src.api.app import app
    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    cli()