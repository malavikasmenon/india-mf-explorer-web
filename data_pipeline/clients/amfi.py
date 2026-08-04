import requests

AMFI_URL = "https://www.amfiindia.com/spages/NAVAll.txt"


def fetch_navall() -> str:
    response = requests.get(AMFI_URL, timeout=30)
    response.raise_for_status()

    # Strip a leading UTF-8 BOM (U+FEFF), which AMFI sometimes serves.
    return response.text.lstrip("\ufeff")