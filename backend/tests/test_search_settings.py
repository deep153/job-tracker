from fastapi.testclient import TestClient

from tests.conftest import READY_SETTINGS, SEARCH_KEY, configure_search


def test_run_is_refused_until_search_settings_are_complete(client: TestClient) -> None:
    settings = client.get("/api/search-settings").json()
    assert settings["ready"] is False
    assert settings["missing"] == [
        "Add at least one role.",
        "Add a location or choose remote.",
        "Turn on at least one job board platform.",
        "Add your search API key.",
    ]

    refused = client.post("/api/runs")
    assert refused.status_code == 400
    assert refused.json()["detail"] == "Finish your search settings first: add at least one role."

    configure_search(client)
    assert client.get("/api/search-settings").json()["ready"] is True


def test_settings_round_trip_with_entries_tidied(client: TestClient) -> None:
    saved = client.put(
        "/api/search-settings",
        json={
            "roles": ["  Backend   Engineer ", "backend engineer", "", "Data Engineer"],
            "locations": ["Chicago, IL"],
            "work_modes": ["hybrid", "onsite", "hybrid"],
            "platforms": ["greenhouse"],
        },
    ).json()

    assert saved["roles"] == ["Backend Engineer", "Data Engineer"]
    assert saved["work_modes"] == ["hybrid", "onsite"]
    assert client.get("/api/search-settings").json()["roles"] == ["Backend Engineer", "Data Engineer"]


def test_remote_only_search_needs_no_location(client: TestClient) -> None:
    client.put("/api/search-settings", json={**READY_SETTINGS, "locations": [], "work_modes": ["remote"]})

    assert "Add a location or choose remote." not in client.get("/api/search-settings").json()["missing"]


def test_platforms_that_are_not_built_yet_cannot_be_turned_on(client: TestClient) -> None:
    response = client.put("/api/search-settings", json={**READY_SETTINGS, "platforms": ["greenhouse", "lever"]})

    assert response.status_code == 422
    assert response.json()["detail"] == "Lever isn't supported yet."
    available = {p["id"]: p["supported"] for p in client.get("/api/search-settings").json()["available_platforms"]}
    assert available == {"greenhouse": True, "lever": False, "ashby": False}


def test_search_api_key_is_never_sent_back(client: TestClient) -> None:
    configure_search(client)

    response = client.get("/api/search-settings")

    assert SEARCH_KEY not in response.text
    assert response.json()["search_api_key"] == {"set": True, "last4": SEARCH_KEY[-4:]}


def test_clearing_the_search_api_key_makes_settings_incomplete(client: TestClient) -> None:
    configure_search(client)

    client.put("/api/settings/search-api-key", json={"key": "  "})

    assert client.get("/api/search-settings").json()["missing"] == ["Add your search API key."]
