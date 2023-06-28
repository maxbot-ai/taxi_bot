import random
import string

import pytest

from taxi_bot.api_service import common, customer, driver
from taxi_bot.api_service.route import route_client
from taxi_bot.api_service.rpc import rpc_client
from taxi_bot.api_service.schema import app, db

# All this urls not really used, all request is mocking with HTTPretty.
IMAGE_STORAGE_URL = "http://localhost:5010"
DRIVER_BOT_URL = "http://127.0.0.1:5001"
CUSTOMER_BOT_URL = "http://127.0.0.1:5001"
ORS_KEY = "ORS_KEY"
ORS_URL = "https://api.openrouteservice.org/v2/directions/driving-car/json"


ORS_BODY = {
    "routes": [
        {
            "summary": {"distance": 2755.2, "duration": 295.9},
            "geometry": "iovlJwfcxDqDyLCKq@yBC[AWFGPWt@aAz@gAFI`@i@PSLQzAmBNO`ByBX]EOCIAMKc@o@sAiAyBACi@eA_@w@KQgA}BGK}A{CMYMYe@{@aAoBk@kAg@aAKS{@iBUc@wAqCOYUa@}@gBAEi@cAg@eACGi@eAo@sAOIWAe@C[Ac@Cy@C[A]AM?w@GOEEAMC[OSGSA]E]Cc@EE?MAMAQ?UAq@A_@C{ACiACu@CyAGOAQEkEGU?U?UAsAEo@AaACy@CyAEkCG[AcACc@AWA[Ao@CoBGc@AyACI?uAE]??j@?b@?dB?`B?F?`A?rA",
        }
    ]
}
CUSTOMER_LOCATIONS = {
    "start_location": {
        "latitude": 13.749079,
        "longitude": 100.503572,
    },
    "finish_location": {
        "latitude": 13.749071,
        "longitude": 100.503577,
    },
}
CUSTOMER_2_LOCATIONS = {
    "start_location": {
        "latitude": 13.749077,
        "longitude": 100.503575,
    },
    "finish_location": {"latitude": 13.749070, "longitude": 100.503570},
}
DRIVER_LOCATION = {"latitude": 13.749069, "longitude": 100.503581}
DRIVER_2_LOCATION = {"latitude": 13.749074, "longitude": 100.503572}

rpc_client.set_config(DRIVER_BOT_URL, CUSTOMER_BOT_URL)
route_client.set_config("/tmp", f"{IMAGE_STORAGE_URL}/images", ORS_KEY)


def rand_phone_number():
    return "".join(random.choices(string.digits, k=10))


def rand_messenger_id():
    return str(random.randint(1000000, 10000000000))


@pytest.fixture
def client():
    random.seed()
    with app.app_context():
        db.drop_all()
        db.create_all()
    return app.test_client()


def create_customer(client):
    messenger_id, phone = rand_messenger_id(), rand_phone_number()
    channel = "telegram"
    resp = client.post(f"/customer/{channel}/{messenger_id}", json={"phone": phone})
    assert resp.status_code == 200
    return {
        "id": resp.json["customer_id"],
        "messenger_id": messenger_id,
        "phone": phone,
    }


def delete_ors_keys(body):
    assert "distance" in body["params"]["ride_summary"]
    assert "duration" in body["params"]["ride_summary"]
    assert "distance" in body["params"]["to_customer_summary"]
    assert "duration" in body["params"]["to_customer_summary"]
    assert body["params"]["image_url"].startswith(f"{IMAGE_STORAGE_URL}/images")
    assert body["params"]["image_url"].endswith("png")
    del body["params"]["ride_summary"]
    del body["params"]["to_customer_summary"]
    del body["params"]["image_url"]


def create_driver(client):
    messenger_id, phone = rand_messenger_id(), rand_phone_number()
    resp = client.post(f"/driver/{messenger_id}", json={"phone": phone, "first_name": "john"})
    assert resp.status_code == 200
    return {
        "id": resp.json["driver_id"],
        "messenger_id": messenger_id,
        "phone": phone,
        "first_name": "john",
    }


@pytest.fixture
def driver(client):
    return create_driver(client)


@pytest.fixture
def customer(client):
    return create_customer(client)
