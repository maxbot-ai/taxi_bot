import random

from test_utils import client, customer, driver, rand_phone_number


def test_customer(client):
    messenger_id = random.randint(1000000, 10000000000)
    channel = "telegram"
    phone = rand_phone_number()
    assert client.get("/customer/unknown/1").status_code == 405
    uri = f"/customer/{channel}/{messenger_id}"
    resp = client.get(uri)
    assert resp.status_code == 200 and not resp.json
    resp = client.post(uri, json={"phone": phone})
    assert resp.status_code == 200
    customer_id = resp.json["customer_id"]
    resp = client.get(uri)
    assert resp.status_code == 200 and resp.json == {
        "phone": phone,
        "customer_id": customer_id,
    }
    resp = client.post(uri, json={"phone": phone})
    assert resp.status_code == 409
    assert "UNIQUE constraint failed: customer.channel" in resp.json["detail"]


def test_driver(client):
    messenger_id = random.randint(1000000, 10000000000)
    phone = rand_phone_number()
    resp = client.get(f"/driver/{messenger_id}")
    assert resp.status_code == 200 and not resp.json
    resp = client.post(f"/driver/{messenger_id}", json={"phone": phone, "first_name": "john"})
    assert resp.status_code == 200
    driver_id = resp.json["driver_id"]
    resp = client.get(f"/driver/{messenger_id}")
    assert resp.status_code == 200 and resp.json == {
        "phone": phone,
        "first_name": "john",
        "driver_id": driver_id,
    }
    resp = client.post(f"/driver/{messenger_id}", json={"phone": phone, "first_name": "john"})
    assert resp.status_code == 409
    assert "UNIQUE constraint failed: driver.phone" in resp.json["detail"]


def test_order(client, customer):
    data = {
        "start_location": {"latitude": 1, "longitude": 2},
        "finish_location": {
            "latitude": 1,
            "longitude": 2,
        },
    }
    resp = client.post(f"/customer/{customer['id']}/order", json=data)
    assert resp.status_code == 409
    data = {
        "start_location": {"latitude": 91.0, "longitude": 33.074749},
        "finish_location": {
            "latitude": 59.921135,
            "longitude": 38.317834,
        },
    }
    resp = client.post(f"/customer/{customer['id']}/order", json=data)
    assert resp.status_code == 400
    data["start_location"]["latitude"] = 68.970606
    resp = client.post(f"/customer/{customer['id']}/order", json=data)
    assert resp.status_code == 200
    resp = client.post(f"/customer/{customer['id']}/order", json=data)
    assert resp.status_code == 200


def test_driver_request(client, driver):
    data = {"location": {"latitude": 2, "longitude": 3}, "radius": 1}
    resp = client.post(f"/driver/{driver['id']}/request", json=data)
    assert resp.status_code == 200
    resp = client.post(f"/driver/{driver['id']}/request", json=data)
    assert resp.status_code == 200
