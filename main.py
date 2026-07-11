import asyncio
import time
import uuid
from typing import Dict, Set, List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from models import VehicleValuationInput, ValuationResponse, AuctionCreate, BidCreate
from valuation import predict_valuation_with_xai

app = FastAPI(title="Car Valuation & Live Bidding API")

# Configure CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory database
# auction_id -> dict
auctions_db: Dict[str, dict] = {
    "demo-1": {
        "id": "demo-1",
        "brand": "Tesla",
        "model": "Model 3",
        "year": 2023,
        "mileage": 12000.0,
        "condition": "Excellent",
        "fuel_type": "Electric",
        "estimated_value": 38500.0,
        "current_price": 30000.0,
        "highest_bidder": "Initial Reserve",
        "duration_seconds": 300,
        "time_remaining": 300,
        "status": "active",
        "created_at": time.time(),
        "bids_log": [
            {"bidder": "Initial Reserve", "amount": 30000.0, "timestamp": "06:00:00"}
        ]
    }
}

# WebSocket Connection Manager
class ConnectionManager:
    def __init__(self):
        # Maps auction_id -> set of WebSocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, auction_id: str):
        await websocket.accept()
        if auction_id not in self.active_connections:
            self.active_connections[auction_id] = set()
        self.active_connections[auction_id].add(websocket)

    def disconnect(self, websocket: WebSocket, auction_id: str):
        if auction_id in self.active_connections:
            self.active_connections[auction_id].discard(websocket)
            if not self.active_connections[auction_id]:
                del self.active_connections[auction_id]

    async def broadcast(self, message: dict, auction_id: str):
        if auction_id in self.active_connections:
            for connection in self.active_connections[auction_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    # Handle disconnected clients gracefully
                    pass

manager = ConnectionManager()

# Background task to decrease auction timers and broadcast expiry
async def track_auctions():
    while True:
        await asyncio.sleep(1)
        now = time.time()
        for auction_id, auction in list(auctions_db.items()):
            if auction["status"] == "active":
                elapsed = now - auction["created_at"]
                remaining = max(0, int(auction["duration_seconds"] - elapsed))
                auction["time_remaining"] = remaining
                
                if remaining <= 0:
                    auction["status"] = "expired"
                    await manager.broadcast({
                        "type": "auction_expired",
                        "message": "The auction has ended!",
                        "data": {
                            "current_price": auction["current_price"],
                            "highest_bidder": auction["highest_bidder"],
                            "bids_log": auction["bids_log"],
                            "status": "expired"
                        }
                    }, auction_id)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(track_auctions())

# 1. Valuation Endpoints
@app.post("/api/evaluate", response_model=ValuationResponse)
def evaluate_car(vehicle: VehicleValuationInput):
    """
    Evaluates vehicle features and returns a predicted valuation along with Explainable AI data.
    """
    try:
        return predict_valuation_with_xai(vehicle)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/evaluate/pdf")
def evaluate_car_pdf(vehicle: VehicleValuationInput):
    """
    Generates a PDF Valuation Report for download.
    """
    try:
        from valuation import predict_valuation_with_xai
        valuation = predict_valuation_with_xai(vehicle)
        
        # ReportLab PDF Generation
        from io import BytesIO
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40
        )
        story = []
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle(
            'DocTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=24,
            leading=28,
            textColor=colors.HexColor('#1E293B'),
            spaceAfter=15
        )
        section_title_style = ParagraphStyle(
            'SectionTitle',
            parent=styles['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=14,
            leading=18,
            textColor=colors.HexColor('#0F172A'),
            spaceBefore=12,
            spaceAfter=8
        )
        body_style = ParagraphStyle(
            'Body',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leading=14,
            textColor=colors.HexColor('#334155')
        )
        bold_body = ParagraphStyle('BoldBody', parent=body_style, fontName='Helvetica-Bold')
        value_style = ParagraphStyle(
            'Value',
            fontName='Helvetica-Bold',
            fontSize=22,
            leading=26,
            textColor=colors.HexColor('#4F46E5'),
            spaceAfter=10
        )
        
        # Header Info
        story.append(Paragraph("Car Valuation Certificate", title_style))
        story.append(Paragraph(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}", body_style))
        story.append(Spacer(1, 15))
        
        # Main Valuation Callout
        story.append(Paragraph("Market Estimation", section_title_style))
        story.append(Paragraph(f"${valuation.estimated_value:,.2f}", value_style))
        story.append(Paragraph(f"<b>Base Segment Baseline:</b> ${valuation.base_value:,.2f}", body_style))
        story.append(Spacer(1, 15))
        
        # Specs Grid Table
        story.append(Paragraph("Vehicle Profile", section_title_style))
        spec_data = [
            [Paragraph("<b>Brand:</b>", body_style), Paragraph(vehicle.brand, body_style), 
             Paragraph("<b>Model:</b>", body_style), Paragraph(vehicle.model, body_style)],
            [Paragraph("<b>Year:</b>", body_style), Paragraph(str(vehicle.year), body_style), 
             Paragraph("<b>Mileage:</b>", body_style), Paragraph(f"{vehicle.mileage:,.0f} miles", body_style)],
            [Paragraph("<b>Condition:</b>", body_style), Paragraph(vehicle.condition.capitalize(), body_style), 
             Paragraph("<b>Fuel Type:</b>", body_style), Paragraph(vehicle.fuel_type.capitalize(), body_style)],
            [Paragraph("<b>Transmission:</b>", body_style), Paragraph(vehicle.transmission, body_style), 
             "", ""]
        ]
        t = Table(spec_data, colWidths=[100, 150, 100, 150])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ]))
        story.append(t)
        story.append(Spacer(1, 15))
        
        # XAI Explanation Table
        story.append(Paragraph("Valuation Factor Analysis (Explainable AI)", section_title_style))
        xai_headers = [[Paragraph("<b>Factor</b>", bold_body), Paragraph("<b>Contribution</b>", bold_body), Paragraph("<b>Model Justification</b>", bold_body)]]
        for c in valuation.contributions:
            c_str = f"+${c.contribution:,.2f}" if c.contribution >= 0 else f"-${abs(c.contribution):,.2f}"
            c_color = '#16A34A' if c.contribution >= 0 else '#DC2626'
            c_p = Paragraph(f"<font color='{c_color}'><b>{c_str}</b></font>", body_style)
            xai_headers.append([
                Paragraph(c.display_name, bold_body),
                c_p,
                Paragraph(c.explanation, body_style)
            ])
            
        xai_t = Table(xai_headers, colWidths=[120, 90, 310])
        xai_t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (2,0), colors.HexColor('#F1F5F9')),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
            ('TOPPADDING', (0,0), (-1,-1), 8),
        ]))
        story.append(xai_t)
        story.append(Spacer(1, 15))
        
        story.append(Paragraph("AI Valuation Justification Statement", section_title_style))
        story.append(Paragraph(valuation.justification, body_style))
        
        doc.build(story)
        pdf_data = buffer.getvalue()
        buffer.close()
        
        return Response(
            content=pdf_data,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=valuation-{vehicle.brand}-{vehicle.model}.pdf"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {str(e)}")

# 2. Auction CRUD Endpoints
@app.get("/api/auctions")
def list_auctions():
    """
    Returns lists of all current and historical auctions.
    """
    return list(auctions_db.values())

@app.post("/api/auctions")
def create_auction(auction: AuctionCreate):
    """
    Initializes a new live auction from a valuation card.
    """
    auction_id = str(uuid.uuid4())[:8]
    now = time.time()
    new_auction = {
        "id": auction_id,
        "brand": auction.brand,
        "model": auction.model,
        "year": auction.year,
        "mileage": auction.mileage,
        "condition": auction.condition,
        "fuel_type": auction.fuel_type,
        "estimated_value": auction.estimated_value,
        "current_price": auction.starting_price,
        "highest_bidder": "Initial Reserve",
        "duration_seconds": auction.duration_seconds,
        "time_remaining": auction.duration_seconds,
        "status": "active",
        "created_at": now,
        "bids_log": [
            {"bidder": "Initial Reserve", "amount": auction.starting_price, "timestamp": time.strftime("%H:%M:%S", time.localtime(now))}
        ]
    }
    auctions_db[auction_id] = new_auction
    return new_auction

@app.get("/api/auctions/{auction_id}")
def get_auction(auction_id: str):
    """
    Gets the state of a specific auction.
    """
    if auction_id not in auctions_db:
        raise HTTPException(status_code=404, detail="Auction not found")
    
    # Update time remaining dynamically before sending response
    auction = auctions_db[auction_id]
    if auction["status"] == "active":
        elapsed = time.time() - auction["created_at"]
        remaining = max(0, int(auction["duration_seconds"] - elapsed))
        auction["time_remaining"] = remaining
        if remaining <= 0:
            auction["status"] = "expired"
            
    return auction

# 3. WebSocket Real-time Bidding Endpoint
@websocket_route := app.websocket("/ws/auction/{auction_id}")
async def websocket_auction(websocket: WebSocket, auction_id: str):
    """
    WebSocket endpoint handling active bidder rooms. Broadcasts real-time bids and timer expires.
    """
    if auction_id not in auctions_db:
        await websocket.close(code=1008)
        return
        
    await manager.connect(websocket, auction_id)
    
    # Send the current auction snapshot on connection
    auction = auctions_db[auction_id]
    await websocket.send_json({
        "type": "init",
        "data": {
            "id": auction["id"],
            "brand": auction["brand"],
            "model": auction["model"],
            "year": auction["year"],
            "estimated_value": auction["estimated_value"],
            "current_price": auction["current_price"],
            "highest_bidder": auction["highest_bidder"],
            "time_remaining": auction["time_remaining"],
            "status": auction["status"],
            "bids_log": auction["bids_log"]
        }
    })
    
    try:
        while True:
            # Wait for incoming messages from client
            data = await websocket.receive_json()
            
            if data.get("type") == "place_bid":
                bidder = data.get("bidder", "Anonymous").strip()
                amount = float(data.get("amount", 0.0))
                
                # Fetch fresh status
                auction = auctions_db[auction_id]
                
                # Dynamic timing checks
                elapsed = time.time() - auction["created_at"]
                remaining = max(0, int(auction["duration_seconds"] - elapsed))
                auction["time_remaining"] = remaining
                
                if remaining <= 0 or auction["status"] == "expired":
                    auction["status"] = "expired"
                    await websocket.send_json({
                        "type": "error",
                        "message": "Bid rejected. The auction has already expired."
                    })
                    continue
                    
                if amount <= auction["current_price"]:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Bid rejected. Must exceed current price of ${auction['current_price']:,.2f}"
                    })
                    continue
                
                # Accept Bid
                timestamp_str = time.strftime("%H:%M:%S")
                auction["current_price"] = amount
                auction["highest_bidder"] = bidder
                auction["bids_log"].insert(0, {
                    "bidder": bidder,
                    "amount": amount,
                    "timestamp": timestamp_str
                })
                
                # Broadcast updated bid status to all users in room
                await manager.broadcast({
                    "type": "bid_update",
                    "data": {
                        "current_price": auction["current_price"],
                        "highest_bidder": auction["highest_bidder"],
                        "bids_log": auction["bids_log"]
                    }
                }, auction_id)
                
    except WebSocketDisconnect:
        manager.disconnect(websocket, auction_id)
    except Exception as e:
        manager.disconnect(websocket, auction_id)
