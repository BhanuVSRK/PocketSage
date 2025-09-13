import requests
import urllib.parse
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status

from schemas import LocationRequest, Hospital, StandardResponse, UserInDB
from auth import get_current_user

router = APIRouter(
    prefix="/hospitals",
    tags=["Hospitals"]
)

def search_overpass_api(lat: float, lon: float) -> List[dict]:
    """
    Queries the Overpass API to find medical facilities within a bounding box.
    """
    bbox = f"{lat-0.02},{lon-0.02},{lat+0.02},{lon+0.02}"
    overpass_query = f"""
    [out:json][timeout:25];
    (
      node["amenity"~"hospital|clinic|doctors"]({bbox});
      way["amenity"~"hospital|clinic|doctors"]({bbox});
      relation["amenity"~"hospital|clinic|doctors"]({bbox});
    );
    out center;
    """
    overpass_url = "https://overpass-api.de/api/interpreter"
    try:
        response = requests.get(overpass_url, params={'data': overpass_query})
        response.raise_for_status()
        return response.json().get("elements", [])
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to communicate with the location service: {e}"
        )

@router.post("/nearby", response_model=StandardResponse[List[Hospital]])
async def find_nearby_hospitals(
    location: LocationRequest,
    current_user: UserInDB = Depends(get_current_user)
):
    """
    Finds nearby hospitals, clinics, and doctors based on user's location.
    """
    raw_places = search_overpass_api(location.latitude, location.longitude)
    
    if not raw_places:
        return StandardResponse(data=[], message="No medical facilities found in the immediate vicinity.")

    hospitals = []
    for place in raw_places[:15]: # Limit to 15 results
        tags = place.get("tags", {})
        name = tags.get("name", tags.get("operator", "Unnamed Facility"))
        
        lat = place.get("lat") or place.get("center", {}).get("lat")
        lon = place.get("lon") or place.get("center", {}).get("lon")

        if not (lat and lon):
            continue

        # Create a clean Google Maps URL on the backend
        maps_query = urllib.parse.quote_plus(f"{name} @{lat},{lon}")
        maps_url = f"https://www.google.com/maps/search/?api=1&query={maps_query}"

        hospital = Hospital(
            name=name,
            type=tags.get("amenity", "facility").replace("_", " ").title(),
            latitude=lat,
            longitude=lon,
            phone=tags.get("phone"),
            address=tags.get("addr:full"),
            google_maps_url=maps_url
        )
        hospitals.append(hospital)

    return StandardResponse(data=hospitals, message=f"Found {len(hospitals)} facilities.")