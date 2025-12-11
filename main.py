import requests
import os
from dotenv import load_dotenv
from typing import Dict, Optional

load_dotenv()

AUTH_TOKEN = os.getenv("AUTH_TOKEN")

BASE_URL = "https://challenge.sphinxhq.com"

headers = {
    "Authorization": f"Bearer {AUTH_TOKEN}",
    "Content-Type": "application/json",
}


def handle_response(response: requests.Response) -> Dict:
    """Handle API response and raise errors if needed."""
    try:
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error: {e}")
        print(f"Response: {response.text}")
        raise
    except requests.exceptions.RequestException as e:
        print(f"Request Error: {e}")
        raise


def start_episode() -> Dict:
    """
    Start a new episode. Initializes your escape attempt.
    
    Returns:
        dict: Response containing initial game state
        {
            "morties_in_citadel": 1000,
            "morties_on_planet_jessica": 0,
            "morties_lost": 0,
            "steps_taken": 0,
            "status_message": "..."
        }
    """
    url = f"{BASE_URL}/api/mortys/start/"
    response = requests.post(url, headers=headers)
    return handle_response(response)


def send_morties(planet: int, morty_count: int) -> Dict:
    """
    Send a group of Morties through a portal to an intermediate planet.
    
    Args:
        planet: Planet index (0="On a Cob" Planet, 1=Cronenberg World, 2=The Purge Planet)
        morty_count: Number of Morties to send (1, 2, or 3)
    
    Returns:
        dict: Response containing updated game state
        {
            "morties_sent": 3,
            "survived": true,
            "morties_in_citadel": 747,
            "morties_on_planet_jessica": 203,
            "morties_lost": 50,
            "steps_taken": 84
        }
    """
    if planet not in [0, 1, 2]:
        raise ValueError("planet must be 0, 1, or 2")
    if morty_count not in [1, 2, 3]:
        raise ValueError("morty_count must be 1, 2, or 3")
    
    url = f"{BASE_URL}/api/mortys/portal/"
    payload = {
        "planet": planet,
        "morty_count": morty_count,
    }
    response = requests.post(url, headers=headers, json=payload)
    return handle_response(response)


def get_status() -> Dict:
    """
    Get the current status of your episode.
    
    Returns:
        dict: Response containing current game state
        {
            "morties_in_citadel": 750,
            "morties_on_planet_jessica": 150,
            "morties_lost": 100,
            "steps_taken": 83,
            "status_message": "..."
        }
    """
    url = f"{BASE_URL}/api/mortys/status/"
    response = requests.get(url, headers=headers)
    return handle_response(response)


def request_token(name: str, email: str) -> Dict:
    """
    Request an API token (for reference, though token already exists).
    
    Args:
        name: Display name
        email: Email address to receive token
    
    Returns:
        dict: Response containing success message
    """
    url = f"{BASE_URL}/api/auth/request-token/"
    payload = {
        "name": name,
        "email": email,
    }
    # Note: This endpoint doesn't require authentication
    response = requests.post(url, json=payload, headers={"Content-Type": "application/json"})
    return handle_response(response)


if __name__ == "__main__":
    # Example usage
    print("Starting episode...")
    result = start_episode()
    print(f"Started: {result}")
    
    print("\nSending 3 Morties to Planet 0...")
    result = send_morties(planet=0, morty_count=3)
    print(f"Result: {result}")
    
    print("\nChecking status...")
    status = get_status()
    print(f"Status: {status}")