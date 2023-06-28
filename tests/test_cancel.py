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


def create_order(client, customer):
    resp = client.post(f"/customer/{customer['id']}/order", json=CUSTOMER_LOCATIONS)
    assert resp.status_code == 200 and resp.json["order_id"]
    return resp.json["order_id"]


@httpretty.activate(allow_net_connect=False)
def test_customer_cancel(client, customer, driver, monkeypatch):
    monkeypatch.setattr(go.Figure, "write_image", lambda self, path: True)
    data = {"order_id": 1}
    resp = client.post(f"/customer/{customer['id']}/cancel", json=data)
    assert 404 == resp.status_code and resp.json["detail"] == "Order not found"
    resp = client.post(f"/customer/{customer['id']}/order", json=CUSTOMER_LOCATIONS)
    assert resp.status_code == 200 and resp.json["order_id"]
    order_id_1 = resp.json["order_id"]
    data = {"order_id": order_id_1}
    resp = client.post(f"/customer/{customer['id']}/cancel", json=data)
    assert resp.status_code == 200
    httpretty.register_uri(
        httpretty.POST,
        f"{ORS_URL}",
        body=json.dumps(ORS_BODY),
    )
    driver_location = dict(location=DRIVER_LOCATION, radius=3)
    resp = client.post(f"/driver/{driver['id']}/request", json=driver_location)
    assert resp.status_code == 200 and not resp.json
    httpretty.register_uri(
        httpretty.POST, f"{DRIVER_BOT_URL}/rpc/telegram/{driver['messenger_id']}"
    )
    order_id_2 = create_order(client, customer)
    body = json.loads(httpretty.latest_requests()[-1].body)
    assert body["method"] == "customer_found"
    delete_ors_keys(body)
    assert body["params"]["order_id"] == order_id_2
    assert body["params"]["start_latitude"] == CUSTOMER_LOCATIONS["start_location"]["latitude"]
    data = {"order_id": order_id_2}
    resp = client.post(f"/customer/{customer['id']}/cancel", json=data)
    assert resp.status_code == 200
    resp = client.post(f"/driver/{driver['id']}/confirm", json=data)
    assert resp.status_code == 200 and resp.json.get("result") == "canceled"
    order_id_3 = create_order(client, customer)
    body = json.loads(httpretty.latest_requests()[-1].body)
    assert body["method"] == "customer_found"
    delete_ors_keys(body)
    assert body["params"]["order_id"] == order_id_3
    assert body["params"]["start_latitude"] == CUSTOMER_LOCATIONS["start_location"]["latitude"]
    httpretty.register_uri(
        httpretty.POST, f"{CUSTOMER_BOT_URL}/rpc/telegram/{customer['messenger_id']}"
    )
    data = {"order_id": order_id_3}
    resp = client.post(f"/driver/{driver['id']}/confirm", json=data)
    assert resp.status_code == 200 and resp.json.get("result") == "success"
    assert json.loads(httpretty.latest_requests()[-1].body)["method"] == "driver_found"
    client.post(f"/customer/{customer['id']}/cancel", json=data)
    assert resp.status_code == 200
    body = json.loads(httpretty.latest_requests()[-1].body)
    assert body["method"] == "customer_canceled"
    order_id_4 = create_order(client, customer)
    data = {"order_id": order_id_4}
    resp = client.post(f"/driver/{driver['id']}/request", json=driver_location)
    assert resp.status_code == 200 and resp.json["order_id"] == order_id_4
    resp = client.post(f"/driver/{driver['id']}/confirm", json=data)
    assert resp.status_code == 200 and resp.json.get("result") == "success"
    assert json.loads(httpretty.latest_requests()[-1].body)["method"] == "driver_found"
    assert client.post(f"/driver/{driver['id']}/arrival", json=data).status_code == 200
    resp = client.post(f"/customer/{customer['id']}/cancel", json=data)
    assert resp.status_code == 200
    body = json.loads(httpretty.latest_requests()[-1].body)
    assert body["method"] == "customer_canceled"
    order_id_4 = create_order(client, customer)
    data = {"order_id": order_id_4}
    resp = client.post(f"/driver/{driver['id']}/request", json=driver_location)
    assert resp.status_code == 200 and resp.json["order_id"] == order_id_4
    resp = client.post(f"/driver/{driver['id']}/confirm", json=data)
    assert resp.status_code == 200 and resp.json.get("result") == "success"
    assert json.loads(httpretty.latest_requests()[-1].body)["method"] == "driver_found"
    assert client.post(f"/driver/{driver['id']}/arrival", json=data).status_code == 200
    resp = client.post(f"/driver/{driver['id']}/start_ride", json=data)
    assert resp.status_code == 200
    resp = client.post(f"/customer/{customer['id']}/cancel", json=data)
    assert resp.status_code == 409 and resp.json["detail"] == "Order state error"
    resp = client.post(f"/driver/{driver['id']}/complete_ride", json=data)
    assert resp.status_code == 200
    order_id_5 = create_order(client, customer)
    data = {"order_id": order_id_5}
    resp = client.post(f"/driver/{driver['id']}/request", json=driver_location)
    assert resp.status_code == 200 and resp.json["order_id"] == order_id_5
    resp = client.post(f"/customer/{customer['id']}/cancel", json=data)
    assert resp.status_code == 200
    resp = client.post(f"/driver/{driver['id']}/confirm", json=data)
    assert resp.status_code == 200 and resp.json.get("result") == "canceled"
    assert 200 == client.post(f"/driver/{driver['id']}/cancel", json=data).status_code


@httpretty.activate(allow_net_connect=False)
def test_driver_cancel(client, customer, driver, monkeypatch):
    monkeypatch.setattr(go.Figure, "write_image", lambda self, path: True)
    resp = client.post(f"/driver/{driver['id']}/cancel")
    assert 404 == resp.status_code and resp.json["detail"] == "Driver request not found"
    httpretty.register_uri(
        httpretty.POST,
        f"{ORS_URL}",
        body=json.dumps(ORS_BODY),
    )
    driver_location = dict(location=DRIVER_LOCATION, radius=3)
    resp = client.post(f"/driver/{driver['id']}/request", json=driver_location)
    assert resp.status_code == 200 and not resp.json
    assert 200 == client.post(f"/driver/{driver['id']}/cancel").status_code
    order_id_1 = create_order(client, customer)
    resp = client.post(f"/driver/{driver['id']}/request", json=driver_location)
    assert resp.status_code == 200 and resp.json["order_id"] == order_id_1
    data = {"order_id": order_id_1}
    httpretty.register_uri(
        httpretty.POST, f"{CUSTOMER_BOT_URL}/rpc/telegram/{customer['messenger_id']}"
    )
    resp = client.post(f"/driver/{driver['id']}/confirm", json=data)
    assert resp.status_code == 200 and resp.json.get("result") == "success"
    resp = client.post(f"/driver/{driver['id']}/cancel", json={"order_id": -1})
    assert 404 == resp.status_code and resp.json["detail"] == "Order not found"
    params = {
        "latitude": DRIVER_LOCATION["latitude"],
        "longitude": DRIVER_LOCATION["longitude"],
        "first_name": driver["first_name"],
        "phone": driver["phone"],
        "order_id": order_id_1,
    }
    body = json.loads(httpretty.latest_requests()[-1].body)
    delete_ors_keys(body)
    assert body["method"] == "driver_found" and body["params"] == params
    resp = client.post(f"/driver/{driver['id']}/cancel")
    assert 400 == resp.status_code and resp.json["detail"] == "No order_id param"
    assert 200 == client.post(f"/driver/{driver['id']}/cancel", json=data).status_code
    body = json.loads(httpretty.latest_requests()[-1].body)
    assert body["method"] == "driver_canceled"
    assert body["params"]["order_id"] == order_id_1

    order_id_2 = create_order(client, customer)
    data = {"order_id": order_id_2}
    resp = client.post(f"/driver/{driver['id']}/request", json=driver_location)
    assert resp.status_code == 200 and resp.json["order_id"] == order_id_2
    resp = client.post(f"/driver/{driver['id']}/confirm", json=data)
    assert resp.status_code == 200 and resp.json.get("result") == "success"
    assert json.loads(httpretty.latest_requests()[-1].body)["method"] == "driver_found"
    assert client.post(f"/driver/{driver['id']}/arrival", json=data).status_code == 200
    body = json.loads(httpretty.latest_requests()[-1].body)
    assert body["method"] == "driver_arrived"

    assert 200 == client.post(f"/driver/{driver['id']}/cancel", json=data).status_code
    resp = client.post(f"/driver/{driver['id']}/cancel", json=data)
    assert 404 == resp.status_code and resp.json["detail"] == "Driver request not found"
