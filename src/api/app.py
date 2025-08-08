from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import logging
from typing import Dict, Any, List
import json
import traceback

from src.models.lead import Lead
from src.extractors.google_maps_extractor import GoogleMapsExtractor
from src.extractors.contact_extractor import ContactExtractor
from src.enrichers.cnpj_enricher import CNPJEnricher
from src.enrichers.technographics_enricher import TechnographicsEnricher
from src.scorers.lead_scorer import LeadScorer
from src.integrations.hubspot_integration import HubSpotIntegration
from src.monitors.job_change_monitor import JobChangeMonitor
from src.compliance.lgpd_compliance import LGPDComplianceManager

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    })


@app.route('/api/v1/extract/companies', methods=['POST'])
def extract_companies():
    """Extract companies from various sources"""
    try:
        data = request.get_json()
        
        # Validate input
        if not data or not data.get('query'):
            return jsonify({"error": "Query parameter is required"}), 400
            
        query = data.get('query')
        location = data.get('location', 'Brasil')
        sector = data.get('sector')
        limit = min(data.get('limit', 50), 200)  # Cap at 200
        
        # Extract from Google Maps
        extractor = GoogleMapsExtractor()
        leads = extractor.search_companies(
            query=query,
            location=location,
            sector=sector,
            limit=limit
        )
        
        # Convert to dict for response
        result = {
            "query": query,
            "location": location,
            "sector": sector,
            "total_found": len(leads),
            "companies": [lead.to_dict() for lead in leads],
            "extracted_at": datetime.now().isoformat()
        }
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error extracting companies: {e}")
        return jsonify({
            "error": "Internal server error",
            "details": str(e)
        }), 500


@app.route('/api/v1/enrich/company', methods=['POST'])
def enrich_company():
    """Enrich a single company with additional data"""
    try:
        data = request.get_json()
        
        if not data or not data.get('company'):
            return jsonify({"error": "Company data is required"}), 400
            
        # Create Lead object
        lead = Lead.from_dict(data['company'])
        
        # Enrichment options
        enrich_cnpj = data.get('enrich_cnpj', True)
        enrich_contacts = data.get('enrich_contacts', True)
        enrich_technographics = data.get('enrich_technographics', True)
        
        enrichment_log = []
        
        # CNPJ enrichment
        if enrich_cnpj:
            cnpj_enricher = CNPJEnricher()
            lead = cnpj_enricher.enrich_lead(lead)
            enrichment_log.append("CNPJ data enriched")
            
        # Contact extraction
        if enrich_contacts:
            contact_extractor = ContactExtractor()
            lead = contact_extractor.enrich_lead_contacts(lead)
            enrichment_log.append("Contact information extracted")
            
        # Technographics
        if enrich_technographics:
            tech_enricher = TechnographicsEnricher()
            lead = tech_enricher.enrich_lead_technographics(lead)
            enrichment_log.append("Technographics analyzed")
            
        return jsonify({
            "company": lead.to_dict(),
            "enrichment_log": enrichment_log,
            "enriched_at": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error enriching company: {e}")
        return jsonify({
            "error": "Internal server error",
            "details": str(e)
        }), 500


@app.route('/api/v1/score/company', methods=['POST'])
def score_company():
    """Score a company's AWS fit"""
    try:
        data = request.get_json()
        
        if not data or not data.get('company'):
            return jsonify({"error": "Company data is required"}), 400
            
        # Create Lead object
        lead = Lead.from_dict(data['company'])
        
        # Score the lead
        scorer = LeadScorer()
        scored_lead = scorer.score_lead(lead)
        
        # Get recommendations
        recommendations = scorer.get_recommendations(scored_lead)
        
        return jsonify({
            "company": scored_lead.to_dict(),
            "score": scored_lead.score,
            "priority": scored_lead.calculate_priority(),
            "score_details": scored_lead.score_details,
            "recommendations": recommendations,
            "scored_at": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error scoring company: {e}")
        return jsonify({
            "error": "Internal server error",
            "details": str(e)
        }), 500


@app.route('/api/v1/pipeline/complete', methods=['POST'])
def complete_pipeline():
    """Run complete lead processing pipeline"""
    try:
        data = request.get_json()
        
        if not data or not data.get('query'):
            return jsonify({"error": "Query parameter is required"}), 400
            
        # Pipeline parameters
        query = data.get('query')
        location = data.get('location', 'Brasil')
        sector = data.get('sector')
        limit = min(data.get('limit', 20), 50)  # Lower limit for full pipeline
        sync_hubspot = data.get('sync_hubspot', False)
        
        pipeline_log = []
        
        # Step 1: Extract
        extractor = GoogleMapsExtractor()
        leads = extractor.search_companies(
            query=query,
            location=location,
            sector=sector,
            limit=limit
        )
        pipeline_log.append(f"Extracted {len(leads)} companies")
        
        if not leads:
            return jsonify({
                "message": "No companies found",
                "query": query,
                "pipeline_log": pipeline_log
            })
            
        # Step 2: Enrich
        cnpj_enricher = CNPJEnricher()
        contact_extractor = ContactExtractor()
        tech_enricher = TechnographicsEnricher()
        
        enriched_leads = []
        for lead in leads:
            # CNPJ
            lead = cnpj_enricher.enrich_lead(lead)
            # Contacts (selective to avoid rate limits)
            if len(enriched_leads) < 10:  # Only first 10 for contacts
                lead = contact_extractor.enrich_lead_contacts(lead)
            # Technographics
            lead = tech_enricher.enrich_lead_technographics(lead)
            enriched_leads.append(lead)
            
        pipeline_log.append(f"Enriched {len(enriched_leads)} companies")
        
        # Step 3: Score
        scorer = LeadScorer()
        scored_leads = scorer.score_batch(enriched_leads)
        pipeline_log.append(f"Scored {len(scored_leads)} companies")
        
        # Step 4: HubSpot sync (optional)
        sync_results = None
        if sync_hubspot:
            qualified_leads = [lead for lead in scored_leads if lead.score >= 60]
            if qualified_leads:
                hubspot = HubSpotIntegration()
                sync_results = hubspot.sync_batch(qualified_leads, create_deals=True)
                pipeline_log.append(f"Synced {len(qualified_leads)} qualified leads to HubSpot")
                
        # Prepare response
        result = {
            "pipeline_summary": {
                "query": query,
                "total_extracted": len(leads),
                "total_enriched": len(enriched_leads),
                "total_scored": len(scored_leads),
                "high_priority": len([l for l in scored_leads if l.calculate_priority() == "HOT"]),
                "medium_priority": len([l for l in scored_leads if l.calculate_priority() == "WARM"]),
            },
            "top_leads": [lead.to_dict() for lead in scored_leads[:10]],
            "hubspot_sync": sync_results,
            "pipeline_log": pipeline_log,
            "processed_at": datetime.now().isoformat()
        }
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in complete pipeline: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            "error": "Internal server error",
            "details": str(e)
        }), 500


@app.route('/api/v1/hubspot/sync', methods=['POST'])
def sync_to_hubspot():
    """Sync companies to HubSpot CRM"""
    try:
        data = request.get_json()
        
        if not data or not data.get('companies'):
            return jsonify({"error": "Companies data is required"}), 400
            
        # Convert to Lead objects
        leads = [Lead.from_dict(company) for company in data['companies']]
        
        # Filter by minimum score
        min_score = data.get('min_score', 60.0)
        qualified_leads = [lead for lead in leads if lead.score >= min_score]
        
        if not qualified_leads:
            return jsonify({
                "message": "No qualified leads to sync",
                "min_score": min_score,
                "total_leads": len(leads)
            })
            
        # Sync to HubSpot
        hubspot = HubSpotIntegration()
        
        # Test connection first
        if not hubspot.test_connection():
            return jsonify({
                "error": "Failed to connect to HubSpot. Check API key."
            }), 400
            
        create_deals = data.get('create_deals', True)
        results = hubspot.sync_batch(qualified_leads, create_deals)
        
        # Summary
        successful = sum(1 for r in results if r["success"])
        failed = len(results) - successful
        
        return jsonify({
            "sync_summary": {
                "total_leads": len(leads),
                "qualified_leads": len(qualified_leads),
                "successful_syncs": successful,
                "failed_syncs": failed,
                "min_score_used": min_score
            },
            "sync_results": results,
            "synced_at": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error syncing to HubSpot: {e}")
        return jsonify({
            "error": "Internal server error",
            "details": str(e)
        }), 500


@app.route('/api/v1/job-changes/recent', methods=['GET'])
def get_recent_job_changes():
    """Get recent job changes"""
    try:
        days = request.args.get('days', 7, type=int)
        min_score = request.args.get('min_score', 60.0, type=float)
        
        monitor = JobChangeMonitor()
        changes = monitor.get_recent_changes(days=days, min_score=min_score)
        
        # Generate alerts
        alerts = monitor.generate_opportunity_alerts(changes)
        
        return jsonify({
            "period_days": days,
            "min_score": min_score,
            "total_changes": len(changes),
            "job_changes": changes,
            "opportunity_alerts": alerts,
            "retrieved_at": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting job changes: {e}")
        return jsonify({
            "error": "Internal server error",
            "details": str(e)
        }), 500


@app.route('/api/v1/compliance/report', methods=['GET'])
def get_compliance_report():
    """Get LGPD compliance report"""
    try:
        compliance = LGPDComplianceManager()
        report = compliance.generate_compliance_report()
        
        return jsonify(report)
        
    except Exception as e:
        logger.error(f"Error generating compliance report: {e}")
        return jsonify({
            "error": "Internal server error",
            "details": str(e)
        }), 500


@app.route('/api/v1/compliance/consent', methods=['POST'])
def update_consent():
    """Update consent status for a data subject"""
    try:
        data = request.get_json()
        
        if not data or not data.get('email'):
            return jsonify({"error": "Email is required"}), 400
            
        email = data['email']
        new_status = data.get('status', 'revoked')
        source = data.get('source', 'api')
        
        compliance = LGPDComplianceManager()
        success = compliance.update_consent(email, new_status, source)
        
        if success:
            return jsonify({
                "message": "Consent updated successfully",
                "email": email,
                "new_status": new_status,
                "updated_at": datetime.now().isoformat()
            })
        else:
            return jsonify({
                "error": "Failed to update consent",
                "email": email
            }), 400
            
    except Exception as e:
        logger.error(f"Error updating consent: {e}")
        return jsonify({
            "error": "Internal server error",
            "details": str(e)
        }), 500


@app.route('/api/v1/compliance/delete-request', methods=['POST'])
def process_deletion_request():
    """Process data deletion request"""
    try:
        data = request.get_json()
        
        if not data or not data.get('email'):
            return jsonify({"error": "Email is required"}), 400
            
        email = data['email']
        
        compliance = LGPDComplianceManager()
        success = compliance.process_deletion_request(email)
        
        if success:
            return jsonify({
                "message": "Deletion request processed successfully",
                "email": email,
                "processed_at": datetime.now().isoformat()
            })
        else:
            return jsonify({
                "error": "Failed to process deletion request",
                "email": email
            }), 400
            
    except Exception as e:
        logger.error(f"Error processing deletion request: {e}")
        return jsonify({
            "error": "Internal server error",
            "details": str(e)
        }), 500


@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "error": "Endpoint not found",
        "available_endpoints": {
            "GET /health": "Health check",
            "POST /api/v1/extract/companies": "Extract companies",
            "POST /api/v1/enrich/company": "Enrich single company",
            "POST /api/v1/score/company": "Score company AWS fit",
            "POST /api/v1/pipeline/complete": "Complete pipeline",
            "POST /api/v1/hubspot/sync": "Sync to HubSpot",
            "GET /api/v1/job-changes/recent": "Get recent job changes",
            "GET /api/v1/compliance/report": "LGPD compliance report",
            "POST /api/v1/compliance/consent": "Update consent",
            "POST /api/v1/compliance/delete-request": "Process deletion request"
        }
    }), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        "error": "Internal server error",
        "message": "An unexpected error occurred"
    }), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)