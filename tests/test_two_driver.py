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
    create_driver,
    customer,
    delete_ors_keys,
    driver,
)

DRIVER_2_LOCATION = {"latitude": 13.749074, "longitude": 100.503572}


@httpretty.activate(allow_net_connect=False)
def test_full_ride_two_driver(client, customer, driver, monkeypatch):
    monkeypatch.setattr(go.Figure, "write_image", lambda self, path: True)
    driver_2 = create_driver(client)
    driver_location = dict(location=DRIVER_LOCATION, radius=3)
    driver_2_location = dict(location=DRIVER_2_LOCATION, radius=10)
    resp = client.post(f"/driver/{driver['id']}/request", json=driver_location)
    assert resp.status_code == 200 and not resp.json
    resp = client.post(f"/driver/{driver_2['id']}/request", json=driver_2_location)
    assert resp.status_code == 200 and not resp.json
    httpretty.register_uri(
        httpretty.POST, f"{DRIVER_BOT_URL}/rpc/telegram/{driver['messenger_id']}"
    )
    httpretty.register_uri(
        httpretty.POST, f"{DRIVER_BOT_URL}/rpc/telegram/{driver_2['messenger_id']}"
    )
    httpretty.register_uri(
        httpretty.POST,
        f"{ORS_URL}",
        body=json.dumps(ORS_BODY),
    )
    resp = client.post(f"/customer/{customer['id']}/order", json=CUSTOMER_LOCATIONS)
    assert resp.status_code == 200 and resp.json["order_id"]
    order_1 = resp.json["order_id"]
    body = json.loads(httpretty.latest_requests()[-1].body)
    assert body["method"] == "customer_found"
    delete_ors_keys(body)
    assert body["params"]["order_id"] == order_1
    assert body["params"]["start_latitude"] == CUSTOMER_LOCATIONS["start_location"]["latitude"]
    body = json.loads(httpretty.latest_requests()[-1].body)
    assert body["method"] == "customer_found"
    delete_ors_keys(body)
    assert body["params"]["order_id"] == order_1
    assert body["params"]["start_latitude"] == CUSTOMER_LOCATIONS["start_location"]["latitude"]
    data = {"order_id": order_1}
    httpretty.register_uri(
        httpretty.POST, f"{CUSTOMER_BOT_URL}/rpc/telegram/{customer['messenger_id']}"
    )
    resp = client.post(f"/driver/{driver['id']}/confirm", json=data)
    assert resp.status_code == 200 and resp.json.get("result") == "success"
    body = json.loads(httpretty.latest_requests()[-1].body)
    params = {
        "latitude": DRIVER_LOCATION["latitude"],
        "longitude": DRIVER_LOCATION["longitude"],
        "first_name": driver["first_name"],
        "phone": driver["phone"],
        "order_id": order_1,
    }
    delete_ors_keys(body)
    assert body["method"] == "driver_found" and body["params"] == params
    resp = client.post(f"/driver/{driver_2['id']}/confirm", json=data)
    assert resp.status_code == 200 and resp.json.get("result") == "busy"
    resp = client.post(f"/driver/{driver_2['id']}/decline", json=data)
    assert resp.status_code == 200
    resp = client.post(f"/driver/{driver['id']}/decline", json=data)
    assert resp.status_code == 409 and resp.json["detail"] == "Request state error"
    assert client.post(f"/driver/{driver['id']}/arrival", json=data).status_code == 200
    body = json.loads(httpretty.latest_requests()[-1].body)
    assert body["method"] == "driver_arrived"
    resp = client.post(f"/driver/{driver['id']}/start_ride", json=data)
    assert resp.status_code == 200
    body = json.loads(httpretty.latest_requests()[-1].body)
    assert body["method"] == "ride_started"
    resp = client.post(f"/driver/{driver['id']}/complete_ride", json=data)
    assert resp.status_code == 200
    body = json.loads(httpretty.latest_requests()[-1].body)
    assert body["method"] == "ride_completed"

    resp = client.post(f"/driver/{driver['id']}/request", json=driver_location)
    assert resp.status_code == 200 and not resp.json
    resp = client.post(f"/customer/{customer['id']}/order", json=CUSTOMER_LOCATIONS)
    assert resp.status_code == 200 and resp.json["order_id"]
    order_2 = resp.json["order_id"]
    assert order_1 != order_2
    data = {"order_id": order_2}
    body = json.loads(httpretty.latest_requests()[-1].body)
    assert body["method"] == "customer_found"
    delete_ors_keys(body)
    assert body["params"]["order_id"] == order_2
    assert body["params"]["start_latitude"] == CUSTOMER_LOCATIONS["start_location"]["latitude"]
    body = json.loads(httpretty.latest_requests()[-1].body)
    assert body["method"] == "customer_found"
    delete_ors_keys(body)
    assert body["params"]["order_id"] == order_2
    assert body["params"]["start_latitude"] == CUSTOMER_LOCATIONS["start_location"]["latitude"]
    assert client.post(f"/driver/{driver['id']}/decline", json=data).status_code == 200
    resp = client.post(f"/driver/{driver_2['id']}/confirm", json=data)
    assert resp.status_code == 200 and resp.json.get("result") == "success"
    resp = client.post(f"/driver/{driver['id']}/arrival", json=data)
    assert resp.status_code == 404 and resp.json["detail"] == "Order not found"
    resp = client.post(f"/driver/{driver_2['id']}/arrival", json=data)
    assert resp.status_code == 200
    resp = client.post(f"/driver/{driver_2['id']}/start_ride", json=data)
    assert resp.status_code == 200
    resp = client.post(f"/driver/{driver_2['id']}/complete_ride", json=data)
    assert resp.status_code == 200
    resp = client.post(f"/customer/{customer['id']}/order", json=CUSTOMER_LOCATIONS)
    assert resp.status_code == 200 and resp.json["order_id"]
    order_3 = resp.json["order_id"]
    assert order_3 != order_1 and order_3 != order_2
    data = {"order_id": order_3}
    resp = client.post(f"/driver/{driver['id']}/confirm", json=data)
    assert resp.status_code == 200 and resp.json.get("result") == "success"
    assert client.post(f"/driver/{driver['id']}/arrival", json=data).status_code == 200
    resp = client.post(f"/driver/{driver['id']}/start_ride", json=data)
    assert resp.status_code == 200
    resp = client.post(f"/driver/{driver['id']}/complete_ride", json=data)
    assert resp.status_code == 200
