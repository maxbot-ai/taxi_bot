import json

import httpretty
import plotly.graph_objects as go
from test_utils import (
    CUSTOMER_BOT_URL,
    CUSTOMER_LOCATIONS,
    DRIVER_BOT_URL,
    DRIVER_LOCATION,
    ORS_BODY,
    ORS_URL,
    client,
    customer,
    delete_ors_keys,
    driver,
)

CUSTOMER_2_LOCATIONS = {
    "start_location": {
        "latitude": 13.749077,
        "longitude": 100.503575,
    },
    "finish_location": {"latitude": 13.749070, "longitude": 100.503570},
}

DRIVER_2_LOCATION = {"latitude": 13.749074, "longitude": 100.503572}


@httpretty.activate(allow_net_connect=False)
def test_full_ride_order_first(client, customer, driver, monkeypatch):
    monkeypatch.setattr(go.Figure, "write_image", lambda self, path: True)
    httpretty.register_uri(
        httpretty.POST, f"{CUSTOMER_BOT_URL}/rpc/telegram/{customer['messenger_id']}"
    )
    resp = client.post(f"/customer/{customer['id']}/order", json=CUSTOMER_LOCATIONS)
    assert resp.status_code == 200
    httpretty.register_uri(
        httpretty.POST,
        f"{ORS_URL}",
        body=json.dumps(ORS_BODY),
    )
    driver_location = {"location": DRIVER_LOCATION, "radius": 5}
    resp = client.post(f"/driver/{driver['id']}/request", json=driver_location)
    assert resp.status_code == 200
    assert resp.json["image_url"]
    assert resp.json["start_latitude"]
    assert resp.json["start_longitude"]
    assert resp.json["order_id"]
    assert resp.json["finish_longitude"]
    assert resp.json["finish_latitude"]
    assert resp.json["ride_summary"] and resp.json["to_customer_summary"]
    data = {"order_id": resp.json["order_id"]}
    resp = client.post(f"/driver/{driver['id']}/confirm", json=data)
    assert resp.status_code == 200 and resp.json["result"] == "success"
    params = {
        "latitude": DRIVER_LOCATION["latitude"],
        "longitude": DRIVER_LOCATION["longitude"],
        "first_name": driver["first_name"],
        "phone": driver["phone"],
        "order_id": data["order_id"],
    }
    body = json.loads(httpretty.latest_requests()[-1].body)
    delete_ors_keys(body)
    assert body["method"] == "driver_found" and body["params"] == params
    resp = client.post(f"/driver/{driver['id']}/confirm", json=data)
    assert resp.status_code == 409 and resp.json["detail"] == "Request state error"
    resp = client.post(f"/driver/{driver['id']}/start_ride", json=data)
    assert resp.status_code == 409 and resp.json["detail"] == "Order state error"
    resp = client.post(f"/driver/{driver['id']}/complete_ride", json=data)
    assert resp.status_code == 409 and resp.json["detail"] == "Order state error"
    assert client.post(f"/driver/{driver['id']}/arrival", json=data).status_code == 200
    body = json.loads(httpretty.latest_requests()[-1].body)
    assert body["method"] == "driver_arrived" and body["params"] == {"order_id": data["order_id"]}
    resp = client.post(f"/driver/{driver['id']}/arrival", json=data)
    assert resp.status_code == 409 and resp.json["detail"] == "Order state error"
    resp = client.post(f"/driver/{driver['id']}/start_ride", json=data)
    assert resp.status_code == 200
    resp = client.post(f"/driver/{driver['id']}/request", json=driver_location)
    assert resp.status_code == 409 and resp.json["detail"] == "Request already exists"
    body = json.loads(httpretty.latest_requests()[-1].body)
    assert body["method"] == "ride_started" and body["params"] == {"order_id": data["order_id"]}
    resp = client.post(f"/driver/{driver['id']}/start_ride", json=data)
    assert resp.status_code == 409 and resp.json["detail"] == "Order state error"
    resp = client.post(f"/driver/{driver['id']}/confirm", json=data)
    assert resp.status_code == 409 and resp.json["detail"] == "Request state error"
    resp = client.post(f"/driver/{driver['id']}/decline", json=data)
    assert resp.status_code == 409 and resp.json["detail"] == "Request state error"
    resp = client.post(f"/driver/{driver['id']}/arrival", json=data)
    assert resp.status_code == 409 and resp.json["detail"] == "Order state error"
    resp = client.post(f"/driver/{driver['id']}/complete_ride", json=data)
    assert resp.status_code == 200
    body = json.loads(httpretty.latest_requests()[-1].body)
    assert body["method"] == "ride_completed" and body["params"] == {"order_id": data["order_id"]}
    resp = client.post(f"/driver/{driver['id']}/arrival", json=data)
    assert resp.status_code == 404 and resp.json["detail"] == "Order not found"
    resp = client.post(f"/driver/{driver['id']}/start_ride", json=data)
    assert resp.status_code == 404 and resp.json["detail"] == "Order not found"
    resp = client.post(f"/driver/{driver['id']}/complete_ride", json=data)
    assert resp.status_code == 404 and resp.json["detail"] == "Order not found"
    resp = client.post(f"/driver/{driver['id']}/confirm", json=data)
    assert resp.status_code == 404 and resp.json["detail"] == "Driver request not found"
    resp = client.post(f"/driver/{driver['id']}/decline", json=data)
    assert resp.status_code == 404 and resp.json["detail"] == "Driver request not found"


@httpretty.activate(allow_net_connect=False)
def test_full_ride_request_first(client, customer, driver, monkeypatch):
    monkeypatch.setattr(go.Figure, "write_image", lambda self, path: True)
    driver_location = dict(location=DRIVER_LOCATION, radius=3)
    resp = client.post(f"/driver/{driver['id']}/request", json=driver_location)
    assert resp.status_code == 200 and not resp.json
    httpretty.register_uri(
        httpretty.POST, f"{DRIVER_BOT_URL}/rpc/telegram/{driver['messenger_id']}"
    )
    httpretty.register_uri(
        httpretty.POST, f"{CUSTOMER_BOT_URL}/rpc/telegram/{customer['messenger_id']}"
    )
    httpretty.register_uri(
        httpretty.POST,
        f"{ORS_URL}",
        body=json.dumps(ORS_BODY),
    )
    resp = client.post(f"/customer/{customer['id']}/order", json=CUSTOMER_LOCATIONS)
    assert resp.status_code == 200 and resp.json.get("order_id")
    body = json.loads(httpretty.latest_requests()[-1].body)
    assert body["method"] == "customer_found"
    delete_ors_keys(body)
    assert body["params"]["order_id"] == resp.json["order_id"]
    assert body["params"]["start_latitude"] == CUSTOMER_LOCATIONS["start_location"]["latitude"]
    assert body["params"]["finish_longitude"] == CUSTOMER_LOCATIONS["finish_location"]["longitude"]
    data = {"order_id": resp.json["order_id"]}
    resp = client.post(f"/driver/{driver['id']}/confirm", json=data)
    assert resp.status_code == 200 and resp.json["result"] == "success"
    resp = client.post(f"/driver/{driver['id']}/confirm", json=data)
    assert resp.status_code == 409 and resp.json["detail"] == "Request state error"
    resp = client.post(f"/driver/{driver['id']}/decline", json=data)
    assert resp.status_code == 409 and resp.json["detail"] == "Request state error"
    resp = client.post(f"/driver/{driver['id']}/start_ride", json=data)
    assert resp.status_code == 409 and resp.json["detail"] == "Order state error"
    resp = client.post(f"/driver/{driver['id']}/complete_ride", json=data)
    assert resp.status_code == 409
    assert client.post(f"/driver/{driver['id']}/arrival", json=data).status_code == 200
    assert client.post(f"/driver/{driver['id']}/confirm", json=data).status_code == 409
    assert client.post(f"/driver/{driver['id']}/decline", json=data).status_code == 409
    resp = client.post(f"/driver/{driver['id']}/complete_ride", json=data)
    assert resp.status_code == 409
    resp = client.post(f"/driver/{driver['id']}/start_ride", json=data)
    assert resp.status_code == 200
    resp = client.post(f"/driver/{driver['id']}/start_ride", json=data)
    assert resp.status_code == 409
    resp = client.post(f"/driver/{driver['id']}/complete_ride", json=data)
    assert resp.status_code == 200
    resp = client.post(f"/driver/{driver['id']}/arrival", json=data)
    assert resp.status_code == 404
