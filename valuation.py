from models import VehicleValuationInput, ValuationResponse, XAIFeatureContribution

def predict_valuation_with_xai(vehicle: VehicleValuationInput) -> ValuationResponse:
    # 1. Base value based on brand segment
    brand_bases = {
        "toyota": 28000.0,
        "honda": 27000.0,
        "ford": 29000.0,
        "bmw": 48000.0,
        "mercedes": 52000.0,
        "audi": 46000.0,
        "tesla": 45000.0,
        "porsche": 75000.0
    }
    
    brand_clean = vehicle.brand.strip().lower()
    base_val = brand_bases.get(brand_clean, 25000.0)
    
    contributions = []
    
    # Brand contribution (compared to baseline of $25k)
    brand_diff = base_val - 25000.0
    contributions.append(
        XAIFeatureContribution(
            feature="brand",
            display_name="Brand Segment",
            contribution=brand_diff,
            explanation=f"{vehicle.brand} is classified as a {'premium/luxury' if brand_diff > 15000 else 'premium' if brand_diff > 0 else 'standard'} brand, establishing a starting base of ${base_val:,.0f}."
        )
    )
    
    # 2. Age Depreciation
    current_year = 2026
    age = max(0, current_year - vehicle.year)
    age_factor = 0.09 # 9% decay per year
    depreciation_rate = min(0.85, age_factor * age) # cap at 85% loss
    age_contribution = -round(base_val * depreciation_rate, 2)
    
    if age > 0:
        contributions.append(
            XAIFeatureContribution(
                feature="year",
                display_name="Vehicle Age",
                contribution=age_contribution,
                explanation=f"Being {age} year(s) old has depreciated the vehicle by {depreciation_rate * 100:.0f}% from its original value."
            )
        )
    else:
        # Brand new car gets a premium
        age_contribution = 2000.0
        contributions.append(
            XAIFeatureContribution(
                feature="year",
                display_name="Vehicle Age",
                contribution=age_contribution,
                explanation="This is a brand new model year vehicle, adding a premium of $2,000 to the baseline."
            )
        )
        
    # 3. Mileage Penalty
    mileage_penalty = -round(vehicle.mileage * 0.08, 2)
    contributions.append(
        XAIFeatureContribution(
            feature="mileage",
            display_name="Odometer Reading",
            contribution=mileage_penalty,
            explanation=f"Odometer of {vehicle.mileage:,.0f} miles reduces valuation by $0.08 per mile."
        )
    )
    
    # 4. Condition Adjustment
    cond_clean = vehicle.condition.strip().lower()
    cond_contributions = {
        "excellent": (0.15, "Excellent condition commands a premium of 15% of the base value."),
        "good": (0.0, "Good condition keeps the vehicle value stable at baseline."),
        "fair": (-0.15, "Fair condition incurs a depreciation penalty of 15% of the base value."),
        "poor": (-0.35, "Poor condition reduces the value by 35% due to expected repairs.")
    }
    
    cond_pct, cond_explanation = cond_contributions.get(cond_clean, (0.0, "Vehicle condition is standard."))
    cond_contribution = round(base_val * cond_pct, 2)
    contributions.append(
        XAIFeatureContribution(
            feature="condition",
            display_name="Physical Condition",
            contribution=cond_contribution,
            explanation=cond_explanation
        )
    )
    
    # 5. Fuel Type Contribution
    fuel_clean = vehicle.fuel_type.strip().lower()
    fuel_factors = {
        "electric": (1500.0, "Electric vehicle powertrain attracts high market demand."),
        "hybrid": (1000.0, "Hybrid powertrain reduces fuel cost, adding a green premium."),
        "petrol": (0.0, "Standard gasoline configuration has no market deviation."),
        "diesel": (-1000.0, "Diesel power plants face stricter emissions regulations, slightly lowering demand.")
    }
    fuel_val, fuel_explanation = fuel_factors.get(fuel_clean, (0.0, "Standard fuel type."))
    contributions.append(
        XAIFeatureContribution(
            feature="fuel_type",
            display_name="Fuel / Powertrain Type",
            contribution=fuel_val,
            explanation=fuel_explanation
        )
    )
        
    # Calculate final value starting from absolute benchmark $25k baseline
    running_total = 25000.0
    for c in contributions:
        running_total += c.contribution
            
    final_value = max(500.0, round(running_total, 2))
    
    # Generate justification text
    major_negative = min(contributions, key=lambda x: x.contribution)
    major_positive = max(contributions, key=lambda x: x.contribution)
    
    justification = (
        f"The predicted market value for this {vehicle.year} {vehicle.brand} {vehicle.model} is ${final_value:,.2f}. "
        f"The model established a starting segment baseline of ${base_val:,.2f}. "
    )
    
    if major_positive.contribution > 0:
        justification += f"The largest positive value driver is the '{major_positive.display_name}', which added ${major_positive.contribution:,.2f} because: {major_positive.explanation.split('.')[0].lower()}. "
    
    if major_negative.contribution < 0:
        justification += f"Conversely, the biggest depreciating factor is the '{major_negative.display_name}', which reduced the valuation by ${abs(major_negative.contribution):,.2f} because: {major_negative.explanation.split('.')[0].lower()}."
    else:
        justification += "The vehicle did not experience any major depreciative penalties."
        
    return ValuationResponse(
        estimated_value=final_value,
        base_value=base_val,
        contributions=contributions,
        justification=justification
    )
