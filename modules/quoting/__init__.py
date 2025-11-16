"""
Quoting Module - instant quoting system-style instant quotes

This module provides instant, automated quoting for sign projects:
- Customer uploads design or provides specs
- AI analyzes requirements
- Historical knowledge retrieved via Gemini RAG
- Structural validation via SignX-Studio
- Cost estimation via SignX-Intel
- Professional quote generated in <5 minutes

Status: 🚀 Core of the instant quoting system transformation
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from platform.registry import registry, ModuleDefinition
from platform.events import event_bus, Event
from typing import List, Optional, Dict, Any
import asyncio
from datetime import datetime, timedelta
import uuid
import logging

logger = logging.getLogger(__name__)


# Module definition
module_def = ModuleDefinition(
    name="quoting",
    version="1.0.0",
    display_name="Quoting",
    description="Instant automated quotes - instant quoting system for signs",
    api_prefix="/api/v1/quoting",
    ui_routes=["/quote", "/quote/:id"],
    nav_order=1,
    icon="dollar-sign",
    events_consumed=["project.created"],
    events_published=["quote.generated", "quote.accepted", "quote.expired"]
)

# API router
router = APIRouter(prefix="/api/v1/quoting", tags=["quoting"])


# Request/Response models
class InstantQuoteRequest(BaseModel):
    """
    Request for instant quote - instant quoting system style
    
    Customer provides minimal information, AI figures out the rest.
    """
    # Customer information
    customer_name: str
    customer_email: str
    customer_phone: Optional[str] = None
    
    # Project basics
    project_name: str
    location: str  # City, State
    
    # Sign specifications (flexible - AI will ask follow-ups if needed)
    sign_type: str = Field(..., description="monument, pole, channel letters, cabinet, etc.")
    approximate_size: Optional[str] = Field(None, description="e.g., '10ft x 4ft', 'letters 24 inches tall'")
    mounting_type: Optional[str] = Field(None, description="ground mount, wall mount, roof mount, etc.")
    
    # Optional details
    materials: Optional[List[str]] = None
    lighting: Optional[str] = Field(None, description="none, LED, neon, backlit, etc.")
    special_requirements: Optional[str] = None
    
    # Attached files
    design_files: Optional[List[str]] = Field(None, description="URLs to uploaded design files")
    photos: Optional[List[str]] = Field(None, description="URLs to site photos")
    
    # Timeline
    desired_completion: Optional[str] = None  # "as soon as possible", "by December 2025", etc.
    
    
class QuoteResponse(BaseModel):
    """Instant quote response"""
    quote_id: str
    status: str  # "instant", "needs_review", "complex"
    
    # Pricing
    estimated_cost: float
    cost_range: tuple[float, float]  # Low and high estimate
    confidence: float  # 0.0-1.0
    
    # Breakdown
    cost_breakdown: Dict[str, float]  # materials, labor, permits, installation, etc.
    
    # Timeline
    estimated_lead_time: str  # "2-3 weeks", "4-6 weeks", etc.
    lead_time_days: int
    
    # Details
    similar_projects: List[Dict]  # From Gemini RAG
    technical_notes: List[str]
    assumptions: List[str]
    
    # Next steps
    valid_until: datetime
    quote_pdf_url: Optional[str] = None
    requires_site_visit: bool = False
    requires_engineer_review: bool = False
    
    # Contact
    contact_person: str = "Brady at Eagle Sign"
    contact_email: str = "brady@eaglesign.net"
    contact_phone: str = "(515) 555-0100"  # Update with real number


class QuoteService:
    """
    instant quoting system-style instant quote generation
    
    Orchestrates multiple AI systems to generate quotes in <5 minutes:
    1. Gemini RAG: Find similar historical projects
    2. SignX-Studio: Validate structural requirements
    3. SignX-Intel: Predict costs
    4. Claude: Synthesize professional quote
    """
    
    def __init__(self):
        self.model = "gemini-2.0-flash-exp"
        
    async def generate_instant_quote(
        self,
        request: InstantQuoteRequest,
        background_tasks: BackgroundTasks
    ) -> QuoteResponse:
        """
        Generate instant quote using multi-AI pipeline
        
        instant quoting system generates quotes in seconds. We aim for <5 minutes for complex signs.
        """
        quote_id = str(uuid.uuid4())
        
        # Run analyses in parallel (instant quoting system speed optimization)
        try:
            results = await asyncio.gather(
                self._analyze_requirements(request),
                self._find_similar_projects(request),
                self._estimate_costs(request),
                self._check_structural_feasibility(request),
                self._determine_timeline(request)
            )
            
            analysis, similar_projects, cost_estimate, structural_check, timeline = results
            
            # Synthesize quote
            quote = await self._synthesize_quote(
                quote_id=quote_id,
                request=request,
                analysis=analysis,
                similar_projects=similar_projects,
                cost_estimate=cost_estimate,
                structural_check=structural_check,
                timeline=timeline
            )
            
            # Generate PDF in background
            background_tasks.add_task(
                self._generate_quote_pdf,
                quote_id,
                quote
            )
            
            # Publish event
            await event_bus.publish(Event(
                type="quote.generated",
                source="quoting",
                project_id=quote_id,
                data={
                    "customer": request.customer_name,
                    "estimated_cost": quote.estimated_cost,
                    "confidence": quote.confidence
                }
            ))
            
            return quote
            
        except Exception as e:
            # Fallback: Mark for manual review
            return QuoteResponse(
                quote_id=quote_id,
                status="needs_review",
                estimated_cost=0,
                cost_range=(0, 0),
                confidence=0.0,
                cost_breakdown={},
                estimated_lead_time="TBD",
                lead_time_days=0,
                similar_projects=[],
                technical_notes=[f"Auto-quote failed: {str(e)}. Manual review required."],
                assumptions=["Quote will be manually prepared within 24 hours"],
                valid_until=datetime.utcnow() + timedelta(days=30),
                requires_engineer_review=True
            )
    
    async def _analyze_requirements(self, request: InstantQuoteRequest) -> Dict:
        """
        Analyze customer requirements using Gemini
        
        Extracts structured data from free-form input.
        """
        # TODO: Use Gemini to parse and clarify requirements
        return {
            "sign_type": request.sign_type,
            "dimensions_parsed": self._parse_dimensions(request.approximate_size),
            "clarity_score": 0.8,
            "missing_info": []
        }
    
    async def _find_similar_projects(self, request: InstantQuoteRequest) -> List[Dict]:
        """
        Find similar historical projects via Gemini RAG
        
        This is where your 95-year knowledge base creates competitive advantage.
        """
        from modules.rag import rag_service
        
        try:
            result = await rag_service.search_similar_projects({
                "sign_type": request.sign_type,
                "dimensions": self._parse_dimensions(request.approximate_size or ""),
                "mounting_type": request.mounting_type or "unknown",
                "location": request.location
            })
            return result.get("similar_projects", [])
        except Exception as e:
            logger.warning(
                "Failed to retrieve similar projects from RAG service: %s",
                str(e),
                exc_info=True
            )
            return []
    
    async def _estimate_costs(self, request: InstantQuoteRequest) -> Dict:
        """
        Estimate costs using SignX-Intel + Gemini RAG historical data
        
        Combines ML prediction with historical actuals.
        """
        # TODO: Call SignX-Intel cost prediction
        # For now, use simple calculation based on sign type
        
        base_costs = {
            "monument": 8000,
            "pole": 12000,
            "channel letters": 3500,
            "cabinet": 4500,
            "pylon": 25000
        }
        
        base = base_costs.get(request.sign_type.lower(), 10000)
        
        return {
            "estimated_cost": base,
            "cost_range": (base * 0.85, base * 1.15),
            "confidence": 0.75,
            "breakdown": {
                "materials": base * 0.45,
                "labor": base * 0.30,
                "permits": base * 0.08,
                "installation": base * 0.12,
                "contingency": base * 0.05
            }
        }
    
    async def _check_structural_feasibility(self, request: InstantQuoteRequest) -> Dict:
        """
        Quick structural feasibility check via SignX-Studio
        
        Flags if project needs engineer review.
        """
        # Simple heuristics for now
        requires_engineer = False
        
        # Large signs need review
        dims = self._parse_dimensions(request.approximate_size or "")
        if dims.get("area_sqft", 0) > 200:
            requires_engineer = True
        
        # Pole signs over 30ft need review
        if "pole" in request.sign_type.lower():
            requires_engineer = True
        
        return {
            "feasible": True,
            "requires_engineer_review": requires_engineer,
            "concerns": []
        }
    
    async def _determine_timeline(self, request: InstantQuoteRequest) -> Dict:
        """
        Determine realistic timeline
        
        Factors: complexity, materials lead time, permit timeline, installation weather
        """
        # Base timeline by sign type
        base_weeks = {
            "monument": 4,
            "pole": 6,
            "channel letters": 3,
            "cabinet": 3,
            "pylon": 8
        }
        
        weeks = base_weeks.get(request.sign_type.lower(), 5)
        
        # Add permit time (varies by location)
        if "iowa" in request.location.lower():
            weeks += 2  # Iowa permits typically 2-3 weeks
        
        return {
            "estimated_weeks": weeks,
            "estimated_days": weeks * 7,
            "description": f"{weeks-1}-{weeks+1} weeks",
            "breakdown": {
                "engineering": "1 week",
                "permits": "2-3 weeks",
                "fabrication": f"{weeks-3} weeks",
                "installation": "3-5 days"
            }
        }
    
    async def _synthesize_quote(
        self,
        quote_id: str,
        request: InstantQuoteRequest,
        analysis: Dict,
        similar_projects: List[Dict],
        cost_estimate: Dict,
        structural_check: Dict,
        timeline: Dict
    ) -> QuoteResponse:
        """
        Synthesize all analyses into final quote
        
        Could use Claude here for natural language synthesis.
        """
        return QuoteResponse(
            quote_id=quote_id,
            status="instant" if cost_estimate["confidence"] > 0.7 else "needs_review",
            estimated_cost=cost_estimate["estimated_cost"],
            cost_range=cost_estimate["cost_range"],
            confidence=cost_estimate["confidence"],
            cost_breakdown=cost_estimate["breakdown"],
            estimated_lead_time=timeline["description"],
            lead_time_days=timeline["estimated_days"],
            similar_projects=similar_projects[:3],  # Top 3
            technical_notes=[
                f"Based on {len(similar_projects)} similar past projects",
                f"Typical {request.sign_type} in this region",
                "Pricing includes materials, labor, permits, and installation"
            ],
            assumptions=[
                "Site is accessible for standard equipment",
                "No underground utilities requiring relocation",
                "Standard soil conditions",
                "Permits obtainable within typical timeline"
            ],
            valid_until=datetime.utcnow() + timedelta(days=30),
            requires_site_visit=False,
            requires_engineer_review=structural_check["requires_engineer_review"]
        )
    
    async def _generate_quote_pdf(self, quote_id: str, quote: QuoteResponse):
        """
        Generate professional quote PDF in background
        
        Uses SignX-Studio PDF generation or custom template.
        """
        # TODO: Generate PDF
        logger.info(f"📄 Generating PDF for quote {quote_id}")
    
    def _parse_dimensions(self, size_text: Optional[str]) -> Dict[str, float]:
        """Parse free-form size text into structured dimensions"""
        if not size_text:
            return {}
        
        # Simple parser - could use Gemini for better parsing
        # "10ft x 4ft" -> {"width": 10, "height": 4, "area_sqft": 40}
        import re
        
        numbers = re.findall(r'(\d+\.?\d*)', size_text)
        if len(numbers) >= 2:
            width = float(numbers[0])
            height = float(numbers[1])
            return {
                "width_ft": width,
                "height_ft": height,
                "area_sqft": width * height
            }
        
        return {}


# Initialize service
quote_service = QuoteService()


# API Endpoints
@router.post("/instant", response_model=QuoteResponse)
async def generate_instant_quote(
    request: InstantQuoteRequest,
    background_tasks: BackgroundTasks
):
    """
    Generate instant quote - instant quoting system style
    
    The magic endpoint that makes Eagle Sign competitive with instant quoting system.
    
    Customer uploads specs → AI analyzes → Quote in <5 minutes
    
    Uses:
    - Gemini RAG for historical knowledge (95 years of projects)
    - SignX-Intel for cost prediction
    - SignX-Studio for structural validation
    - Claude for synthesis
    
    Free tier: 1,500 quotes/day (50 quotes/day usage = 3% of limit)
    """
    return await quote_service.generate_instant_quote(request, background_tasks)


@router.get("/{quote_id}")
async def get_quote(quote_id: str):
    """
    Retrieve quote by ID
    
    Returns quote details and current status.
    """
    # TODO: Retrieve from database
    return {"quote_id": quote_id, "status": "retrieving"}


@router.post("/{quote_id}/accept")
async def accept_quote(quote_id: str):
    """
    Customer accepts quote
    
    Converts quote to project and triggers production workflow.
    """
    # Publish event
    await event_bus.publish(Event(
        type="quote.accepted",
        source="quoting",
        project_id=quote_id,
        data={"quote_id": quote_id}
    ))
    
    return {"status": "accepted", "next_steps": "Engineering review scheduled"}


@router.post("/upload/design")
async def upload_design_file(file: UploadFile = File(...)):
    """
    Upload design file for quote
    
    Accepts: PDF, DXF, DWG, images
    Processes via documents module (CatScale parser)
    """
    # TODO: Upload to MinIO, trigger parser
    return {"file_url": f"/uploads/{file.filename}"}


@router.get("/status/capacity")
async def get_capacity_status():
    """
    Current capacity and lead times
    
    instant quoting system shows real-time capacity. This provides transparency to customers.
    """
    return {
        "current_backlog": "2-3 weeks",
        "rush_available": True,
        "rush_premium": "50%",
        "next_available_slot": "2025-12-01"
    }


# Register with platform
registry.register(module_def, router)

