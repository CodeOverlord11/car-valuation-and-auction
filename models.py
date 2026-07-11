from pydantic import BaseModel, Field
from typing import List, Optional

class VehicleValuationInput(BaseModel):
    brand: str = Field(..., description="Brand/Make of the car (e.g., Toyota, BMW, Tesla)")
    model: str = Field(..., description="Model of the car (e.g., Camry, 3 Series, Model Y)")
    year: int = Field(..., ge=1900, le=2028, description="Manufacturing year")
    mileage: float = Field(..., ge=0, description="Mileage in miles or kilometers")
    condition: str = Field(..., description="Condition of the car (e.g., Excellent, Good, Fair, Poor)")
    fuel_type: str = Field(..., description="Fuel type (e.g., Petrol, Diesel, Electric, Hybrid)")
    transmission: str = Field("Automatic", description="Transmission type (e.g., Automatic, Manual)")

class XAIFeatureContribution(BaseModel):
    feature: str = Field(..., description="The feature name (e.g., mileage, year)")
    display_name: str = Field(..., description="Human-readable feature name")
    contribution: float = Field(..., description="The positive/negative monetary contribution of the feature in USD")
    explanation: str = Field(..., description="Brief explanation of why this feature modified the valuation")

class ValuationResponse(BaseModel):
    estimated_value: float = Field(..., description="The final predicted market value of the vehicle")
    base_value: float = Field(..., description="The initial average value starting point for the brand")
    contributions: List[XAIFeatureContribution] = Field(..., description="The impact of individual features")
    justification: str = Field(..., description="A detailed textual explanation of the model's prediction")

class BidCreate(BaseModel):
    bidder: str = Field(..., description="Name/ID of the bidder")
    amount: float = Field(..., description="Bid amount")

class AuctionCreate(BaseModel):
    brand: str
    model: str
    year: int
    mileage: float
    condition: str
    fuel_type: str
    estimated_value: float
    starting_price: float
    duration_seconds: int = Field(120, description="Auction duration in seconds")
