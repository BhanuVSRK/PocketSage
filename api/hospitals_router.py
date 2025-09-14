# api/hospitals_router.py

import requests
import urllib.parse
import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status

from schemas import LocationRequest, Hospital, StandardResponse, UserInDB
from auth import get_current_user

router = APIRouter(
    prefix="/hospitals",
    tags=["Hospitals"]
)

logger = logging.getLogger(__name__)

def search_overpass_api(lat: float, lon: float, radius: float = 0.02) -> List[dict]:
    """
    Queries the Overpass API to find medical facilities within a bounding box.
    """
    bbox = f"{lat-radius},{lon-radius},{lat+radius},{lon+radius}"
    overpass_query = f"""
    [out:json][timeout:30];
    (
      node["amenity"~"hospital|clinic|doctors|pharmacy"]({bbox});
      way["amenity"~"hospital|clinic|doctors|pharmacy"]({bbox});
      relation["amenity"~"hospital|clinic|doctors|pharmacy"]({bbox});
    );
    out center;
    """
    overpass_url = "https://overpass-api.de/api/interpreter"
    
    logger.info(f"Searching for hospitals near {lat}, {lon} with radius {radius}")
    logger.info(f"Overpass query: {overpass_query}")
    
    try:
        response = requests.get(overpass_url, params={'data': overpass_query}, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        elements = data.get("elements", [])
        
        logger.info(f"Overpass API returned {len(elements)} results")
        return elements
        
    except requests.exceptions.Timeout:
        logger.error("Overpass API request timed out")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Location service timed out. Please try again."
        )
    except requests.exceptions.RequestException as e:
        logger.error(f"Overpass API request failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to communicate with the location service: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error in Overpass API call: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while searching for facilities."
        )

@router.post("/nearby", response_model=StandardResponse[List[Hospital]])
async def find_nearby_hospitals(
    location: LocationRequest,
    current_user: UserInDB = Depends(get_current_user)
):
    """
    Finds nearby hospitals, clinics, and doctors based on user's location.
    """
    logger.info(f"Hospital search request from user {current_user.email} for location {location.latitude}, {location.longitude}")
    
    # Try with default radius first
    raw_places = search_overpass_api(location.latitude, location.longitude, radius=0.02)
    
    # If no results found, expand search radius
    if not raw_places:
        logger.info("No results found with default radius, expanding search")
        raw_places = search_overpass_api(location.latitude, location.longitude, radius=0.05)
    
    if not raw_places:
        logger.warning(f"No medical facilities found near {location.latitude}, {location.longitude}")
        return StandardResponse(
            data=[], 
            message="No medical facilities found in the area. Try a different location or expand your search."
        )

    hospitals = []
    processed_count = 0
    
    for place in raw_places[:20]:  # Increased limit to 20
        tags = place.get("tags", {})
        name = tags.get("name", tags.get("operator", "Unnamed Facility"))
        
        # Skip facilities without names
        if name == "Unnamed Facility" and not tags.get("operator"):
            continue
        
        lat = place.get("lat") or place.get("center", {}).get("lat")
        lon = place.get("lon") or place.get("center", {}).get("lon")

        if not (lat and lon):
            continue

        # Create a clean Google Maps URL
        maps_query = urllib.parse.quote_plus(f"{name} @{lat},{lon}")
        maps_url = f"https://www.google.com/maps/search/?api=1&query={maps_query}"

        # Enhanced address handling
        address_parts = []
        if tags.get("addr:housenumber"):
            address_parts.append(tags.get("addr:housenumber"))
        if tags.get("addr:street"):
            address_parts.append(tags.get("addr:street"))
        if tags.get("addr:city"):
            address_parts.append(tags.get("addr:city"))
        
        full_address = tags.get("addr:full") or ", ".join(address_parts) if address_parts else None

        hospital = Hospital(
            name=name,
            type=tags.get("amenity", "facility").replace("_", " ").title(),
            latitude=lat,
            longitude=lon,
            phone=tags.get("phone") or tags.get("contact:phone"),
            address=full_address,
            google_maps_url=maps_url
        )
        hospitals.append(hospital)
        processed_count += 1

    logger.info(f"Processed {processed_count} facilities, returning {len(hospitals)} results")
    
    return StandardResponse(
        data=hospitals, 
        message=f"Found {len(hospitals)} facilities within search area."
    )

# Add a debug endpoint for testing
@router.get("/debug/test")
async def debug_hospital_search(
    lat: float = 40.7128,  # Default to NYC
    lon: float = -74.0060,
    current_user: UserInDB = Depends(get_current_user)
):
    """
    Debug endpoint to test hospital search functionality
    """
    logger.info(f"Debug hospital search from user {current_user.email}")
    
    try:
        raw_places = search_overpass_api(lat, lon, radius=0.02)
        return {
            "status": True,
            "message": f"Debug search successful. Found {len(raw_places)} raw results.",
            "raw_count": len(raw_places),
            "sample_data": raw_places[:3] if raw_places else [],
            "search_coordinates": {"lat": lat, "lon": lon}
        }
    except Exception as e:
        logger.error(f"Debug search failed: {e}")
        return {
            "status": False,
            "error": str(e),
            "search_coordinates": {"lat": lat, "lon": lon}
        }