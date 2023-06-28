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
    create_customer,
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


@httpretty.activate(allow_net_connect=False)
def test_full_ride_two_customer(client, customer, driver, monkeypatch):
    monkeypatch.setattr(go.Figure, "write_image", lambda self, path: True)
    customer_2 = create_customer(client)
    driver_location = dict(location=DRIVER_LOCATION, radius=3)
    resp = client.post(f"/driver/{driver['id']}/request", json=driver_location)
    assert resp.status_code == 200 and not resp.json
    httpretty.register_uri(
        httpretty.POST, f"{DRIVER_BOT_URL}/rpc/telegram/{driver['messenger_id']}"
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
    resp = client.post(f"/customer/{customer_2['id']}/order", json=CUSTOMER_2_LOCATIONS)
    assert resp.status_code == 200 and resp.json["order_id"]
    order_2 = resp.json["order_id"]
    body = json.loads(httpretty.latest_requests()[-1].body)
    assert body["method"] == "customer_found"
    delete_ors_keys(body)
    assert body["params"]["order_id"] == order_2
    assert body["params"]["start_latitude"] == CUSTOMER_2_LOCATIONS["start_location"]["latitude"]
    httpretty.register_uri(
        httpretty.POST, f"{CUSTOMER_BOT_URL}/rpc/telegram/{customer['messenger_id']}"
    )
    data = {"order_id": order_1}
    resp = client.post(f"/driver/{driver['id']}/confirm", json=data)
    assert resp.status_code == 200 and resp.json.get("result") == "success"
    body = json.loads(httpretty.latest_requests()[-1].body)
    assert body["method"] == "driver_found"
    assert client.post(f"/driver/{driver['id']}/arrival", json=data).status_code == 200
    resp = client.post(f"/driver/{driver['id']}/start_ride", json=data)
    assert resp.status_code == 200
    resp = client.post(f"/driver/{driver['id']}/complete_ride", json=data)
    assert resp.status_code == 200
    resp = client.post(f"/driver/{driver['id']}/request", json=driver_location)
    assert resp.status_code == 200 and resp.json["order_id"] == order_2
    assert resp.json["start_latitude"] == CUSTOMER_2_LOCATIONS["start_location"]["latitude"]
    resp = client.post(f"/driver/{driver['id']}/confirm", json=data)
    assert resp.status_code == 200 and resp.json.get("result") == "canceled"
    resp = client.post(f"/driver/{driver['id']}/decline", json=data)
    assert resp.status_code == 200 and resp.json.get("result") == "canceled"
    data = {"order_id": order_2}
    httpretty.register_uri(
        httpretty.POST, f"{CUSTOMER_BOT_URL}/rpc/telegram/{customer_2['messenger_id']}"
    )
    resp = client.post(f"/driver/{driver['id']}/confirm", json=data)
    assert resp.status_code == 200 and resp.json.get("result") == "success"
    assert json.loads(httpretty.latest_requests()[-1].body)["method"] == "driver_found"
    assert client.post(f"/driver/{driver['id']}/arrival", json=data).status_code == 200
    resp = client.post(f"/driver/{driver['id']}/start_ride", json=data)
    assert resp.status_code == 200
    resp = client.post(f"/driver/{driver['id']}/complete_ride", json=data)
    assert resp.status_code == 200
