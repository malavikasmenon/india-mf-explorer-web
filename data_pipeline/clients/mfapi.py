import requests

BASE_URL = "https://api.mfapi.in"


def fetch_latest():
    response = requests.get(
        f"{BASE_URL}/mf/latest",
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def fetch_history(scheme_code):
    response = requests.get(
        f"{BASE_URL}/mf/{scheme_code}",
        timeout=30,
    )
    response.raise_for_status()
    return response.json()