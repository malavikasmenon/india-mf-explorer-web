import requests

AMFI_URL = "https://www.amfiindia.com/spages/NAVAll.txt"
AVERAGE_AUM_URL = "https://www.amfiindia.com/api/average-aum-schemewise"
TER_URL = "https://www.amfiindia.com/api/populate-te-rdata-revised"

# The endpoint's own cap - a larger pageSize is silently clamped to this
# rather than honoured or rejected.
_TER_PAGE_SIZE = 100


def fetch_navall() -> str:
    response = requests.get(AMFI_URL, timeout=30)
    response.raise_for_status()

    # Strip a leading UTF-8 BOM (U+FEFF), which AMFI sometimes serves.
    return response.text.lstrip("\ufeff")


# strType picks how AMFI's own UI groups the response (by scheme type or by
# SEBI category); it does not change which schemes or figures come back, so
# it is fixed here rather than exposed as a parameter. MF_ID=0 is AMFI's
# code for "every fund house", which returns every scheme in one call rather
# than requiring one request per AMC.
_TYPEWISE_ALL_FUNDS = {"strType": "Typewise", "MF_ID": 0}


def fetch_average_aum_financial_years() -> list[dict]:
    """Financial years AMFI has published scheme-wise average AUM for, newest first."""
    response = requests.get(AVERAGE_AUM_URL, params=_TYPEWISE_ALL_FUNDS, timeout=30)
    response.raise_for_status()
    return response.json()["data"]


def fetch_average_aum_periods(fy_id: int) -> list[dict]:
    """The quarters published within one financial year, newest first."""
    response = requests.get(
        AVERAGE_AUM_URL,
        params={**_TYPEWISE_ALL_FUNDS, "fyId": fy_id},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["data"]["periods"]


def fetch_average_aum_schemewise(fy_id: int, period_id: int) -> list[dict]:
    """Scheme-wise average AUM for one quarter - every AMC, one response."""
    response = requests.get(
        AVERAGE_AUM_URL,
        params={**_TYPEWISE_ALL_FUNDS, "fyId": fy_id, "periodId": period_id},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["data"]


def fetch_ter_month(month: str) -> list[dict]:
    """Every TER row AMFI has published for one calendar month - every
    scheme, every day disclosed so far. month is "MM-YYYY", the API's own
    format. There is no day-level filter (checked directly against the live
    endpoint), so a caller wanting just one day still has to page through
    the whole month and pick that day's rows back out."""
    rows: list[dict] = []
    page = 1

    while True:
        response = requests.get(
            TER_URL,
            params={
                "MF_ID": "All",
                "Month": month,
                "strCat": -1,
                "strType": -1,
                "page": page,
                "pageSize": _TER_PAGE_SIZE,
            },
            timeout=30,
        )
        response.raise_for_status()
        body = response.json()
        rows.extend(body["data"])

        if page >= body["meta"]["pageCount"]:
            break
        page += 1

    return rows