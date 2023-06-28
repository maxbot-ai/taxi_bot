"""Driver bot api."""
import json

from webargs import fields, validate

from taxi_bot.api_service import query
from taxi_bot.api_service.common import (
    LocationField,
    calculate_price,
    conflict,
    not_found,
    resp,
    use_body,
)
from taxi_bot.api_service.route import route_client
from taxi_bot.api_service.rpc import rpc_client
from taxi_bot.api_service.schema import (
    CANCELED_ORDER_STATE,
    CANCELED_REQUEST_STATE,
    COMPLETED_REQUEST_STATE,
    COMPLETED_RIDE_ORDER_STATE,
    CONFIRMED_REQUEST_STATE,
    DRIVER_ARRIVED_ORDER_STATE,
    DRIVER_CONFIRM_ORDER_STATE,
    INIT_REQUEST_STATE,
    STARTED_RIDE_ORDER_STATE,
    app,
    db,
)


@app.route("/driver/<string:messenger_id>", methods=["POST"])
@use_body(
    {
        "phone": fields.Str(required=True),
        "first_name": fields.Str(required=True),
        "last_name": fields.Str(),
    }
)
def post_driver(body, messenger_id):
    """Add new driver.

    :param dict body: Contains phone key
    :param str messenger_id: driver identifier in telegram
    :return Flask.Response: status=200 on success,
                            status=409 on duplicate
    """
    driver = query.add_driver(
        messenger_id, body["phone"], body["first_name"], body.get("last_name")
    )
    db.session.commit()
    return resp(data={"driver_id": driver.driver_id})


@app.route("/driver/<string:messenger_id>", methods=["GET"])
def get_driver(messenger_id):
    """Get driver.

    :param str messenger_id: driver identifier in telegram
    :return Flask.Response: status=200 with driver data if driver exists
    """
    driver = query.find_driver_by_messenger_id(messenger_id)
    data = {}
    if driver:
        data = {
            "phone": driver.phone,
            "first_name": driver.first_name,
            "driver_id": driver.driver_id,
        }
        if driver.last_name:
            data["last_name"] = driver.last_name
    return resp(data=data)


@app.route("/driver/<int:driver_id>/request", methods=["POST"])
@use_body(
    {
        "location": fields.Nested(LocationField, required=True),
        "radius": fields.Integer(required=True, validate=[validate.Range(min=1, max=300)]),
    }
)
def post_driver_request(body, driver_id):
    """Add new driver request for search customer order.

    # Maximum radius 300 km.

    :param dict body: Contains location and radius keys
    :param str driver_id: db.driver.driver_id
    :return Flask.Response: status=200 on success,
                            status=409 on duplicate
    """
    query.add_driver_request_if_not_exists(
        driver_id,
        body["location"]["latitude"],
        body["location"]["longitude"],
        body["radius"],
        state=INIT_REQUEST_STATE,
    )
    driver_request = query.find_driver_request_by_driver_id_for_update(driver_id)
    if not driver_request:
        return conflict("Driver_request race condition")
    if driver_request.state != INIT_REQUEST_STATE:
        return conflict("Request already exists")
    data = {}
    orders = query.find_all_active_orders(driver_id)
    # Use task queue for long procedures, for example Celery
    # See https://docs.celeryq.dev/en/stable/
    # But necessary not in_memory db for work with other os processes
    orders_with_radius = []
    for order in orders:
        ors_result = route_client.get_ors_route(
            body["location"]["latitude"],
            body["location"]["longitude"],
            order.start_latitude,
            order.start_longitude,
        )
        # Skip if received ORS error.
        if not ors_result:
            continue
        to_customer_route, to_customer_summary = ors_result
        distance = to_customer_summary.get("distance", 0)
        orders_with_radius.append((distance, order, to_customer_route, to_customer_summary))
    orders_with_radius = sorted(orders_with_radius, key=lambda x: x[0])
    if orders_with_radius:
        radius, order, to_customer_route, to_customer_summary = orders_with_radius[0]
        if radius < body["radius"]:
            ors_result = route_client.get_ors_route(
                order.start_latitude,
                order.start_longitude,
                order.finish_latitude,
                order.finish_longitude,
            )
            # Skip if received ORS error.
            if ors_result:
                ride_route, ride_summary = ors_result
                ride_summary["price"] = calculate_price(ride_summary["distance"])
                image_url = route_client.create_route_image(to_customer_route, ride_route)
                data = {
                    "order_id": order.order_id,
                    "start_latitude": order.start_latitude,
                    "start_longitude": order.start_longitude,
                    "finish_latitude": order.finish_latitude,
                    "finish_longitude": order.finish_longitude,
                    "ride_summary": ride_summary,
                    "to_customer_summary": to_customer_summary,
                    "image_url": image_url,
                }
                query.update_driver_request_summary(
                    driver_request.driver_request_id,
                    json.dumps(ride_summary),
                    json.dumps(to_customer_summary),
                    image_url,
                )
    db.session.commit()
    return resp(data=data)


@app.route("/driver/<int:driver_id>/confirm", methods=["POST"])
@use_body({"order_id": fields.Integer(required=False)})
def confirm_order(body, driver_id):
    """Confirm order and update order state=confirmed.

    :param dict body: Contains order_id key
    :param str driver_id: db.driver.driver_id
    :return Flask.Response: status=200 and parameter 'result' with values 'canceled', 'busy' or 'success',
                            status=404 if order does not exist,
                            status=409 on state error
    """
    driver_request = query.find_driver_request_by_driver_id_for_update(driver_id)
    if not driver_request:
        return not_found("Driver request not found")
    if driver_request.state != INIT_REQUEST_STATE:
        return conflict("Request state error")
    order = query.find_order_by_order_id_for_update(body["order_id"])
    if not order:
        return resp(data={"result": "canceled"})
    if order.driver_id:
        return resp(data={"result": "busy"})
    query.update_order_driver_id_by_order_id(body["order_id"], driver_request.driver_id)
    query.update_driver_request_state_by_driver_id(
        driver_request.driver_id,
        current_state=INIT_REQUEST_STATE,
        new_state=CONFIRMED_REQUEST_STATE,
    )
    params = {
        "phone": driver_request.phone,
        "first_name": driver_request.first_name,
        "latitude": driver_request.latitude,
        "longitude": driver_request.longitude,
        "order_id": order.order_id,
        "ride_summary": json.loads(driver_request.ride_summary),
        "to_customer_summary": json.loads(driver_request.to_customer_summary),
        "image_url": driver_request.image_url,
    }
    if driver_request.last_name:
        params["last_name"] = driver_request.last_name
    rpc_client.notify_customer(order.channel, order.messenger_id, "driver_found", params)
    db.session.commit()
    return resp(data={"result": "success"})


@app.route("/driver/<int:driver_id>/decline", methods=["POST"])
@use_body({"order_id": fields.Integer(required=True)})
def decline_order(body, driver_id):
    """Deny order.

    :param dict body: Contains order_id key
    :param str driver_id: db.driver.driver_id
    :return Flask.Response: status=200 and optional parameter 'result' with value 'canceled',
                            status=404 if order does not exist,
                            status=409 on state error
    """
    driver_request = query.find_driver_request_by_driver_id_for_update(driver_id)
    if not driver_request:
        return not_found("Driver request not found")
    if driver_request.state != INIT_REQUEST_STATE:
        return conflict("Request state error")
    order = query.find_order_by_order_id_for_update(body["order_id"])
    if not order:
        return resp(data={"result": "canceled"})
    if order.driver_id:
        return resp()
    query.add_driver_reject_order(driver_request.driver_id, body["order_id"])
    db.session.commit()
    return resp()


@app.route("/driver/<int:driver_id>/arrival", methods=["POST"])
@use_body({"order_id": fields.Integer(required=True)})
def arrival(body, driver_id):
    """Update order state=arrival and notify customer about driver arrival.

    :param dict body: Contains order_id key
    :param str driver_id: db.driver.driver_id
    :return Flask.Response: status=200 on success,
                            status=409 on state error,
                            status=404 if order does not exist
    """
    order = query.find_order_by_order_id_for_update(body["order_id"])
    if not order or order.driver_id != driver_id:
        return not_found("Order not found")
    if order.state != DRIVER_CONFIRM_ORDER_STATE:
        return conflict("Order state error")
    query.update_order_state_by_order_id(order.order_id, DRIVER_ARRIVED_ORDER_STATE)
    params = {"order_id": order.order_id}
    rpc_client.notify_customer(order.channel, order.messenger_id, "driver_arrived", params)
    db.session.commit()
    return resp()


@app.route("/driver/<int:driver_id>/start_ride", methods=["POST"])
@use_body({"order_id": fields.Integer(required=True)})
def start_ride(body, driver_id):
    """Update order state=start_ride and notify customer about driver started ride.

    :param dict body: Contains order_id key
    :param str driver_id: db.driver.driver_id
    :return Flask.Response: status=200 on success,
                            status=409 on state error,
                            status=404 if order does not exist
    """
    order = query.find_order_by_order_id_for_update(body["order_id"])
    if not order or order.driver_id != driver_id:
        return not_found("Order not found")
    if order.state != DRIVER_ARRIVED_ORDER_STATE:
        return conflict("Order state error")
    query.update_order_state_by_order_id(order.order_id, STARTED_RIDE_ORDER_STATE)
    params = {"order_id": order.order_id}
    rpc_client.notify_customer(order.channel, order.messenger_id, "ride_started", params)
    db.session.commit()
    return resp()


@app.route("/driver/<int:driver_id>/complete_ride", methods=["POST"])
@use_body({"order_id": fields.Integer(required=True)})
def complete_ride(body, driver_id):
    """Update order state=complete_ride and notify customer about driver completed ride.

    :param dict body: Contains order_id key
    :param str driver_id: db.driver.driver_id
    :return Flask.Response: status=200 on success,
                            status=409 on state error,
                            status=404 if order does not exist
    """
    order = query.find_order_by_order_id_for_update(body["order_id"])
    if not order or order.driver_id != driver_id:
        return not_found("Order not found")
    if order.state != STARTED_RIDE_ORDER_STATE:
        return conflict("Order state error")
    query.update_order_state_by_order_id(order.order_id, COMPLETED_RIDE_ORDER_STATE)
    query.update_driver_request_state_by_driver_id(
        order.driver_id,
        current_state=CONFIRMED_REQUEST_STATE,
        new_state=COMPLETED_REQUEST_STATE,
    )
    params = {"order_id": order.order_id}
    rpc_client.notify_customer(order.channel, order.messenger_id, "ride_completed", params)
    db.session.commit()
    return resp()


@app.route("/driver/<int:driver_id>/cancel", methods=["POST"])
@use_body({"order_id": fields.Integer()})
def driver_cancel(body, driver_id):
    """Update order state=canceled and notify customer about driver canceled order.

    :param dict body: Contains order_id key
    :param str driver_id: db.driver.driver_id
    :return Flask.Response: status=200 on success,
                            status=404 if order for driver does not exist
                            status=400 on state='confirmed' and not specify parameter order_id
    """
    driver_request = query.find_driver_request_by_driver_id_for_update(driver_id)
    if not driver_request:
        return not_found("Driver request not found")
    if driver_request.state == CONFIRMED_REQUEST_STATE:
        if not body or not body.get("order_id"):
            return resp(status=400, data={"detail": "No order_id param"})
        order = query.find_order_by_order_id_for_update(body["order_id"])
        if not order or order.driver_id != driver_id:
            return not_found("Order not found")
        query.update_driver_request_state_by_driver_id(
            order.driver_id,
            current_state=CONFIRMED_REQUEST_STATE,
            new_state=CANCELED_REQUEST_STATE,
        )
        query.update_order_state_by_order_id(order.order_id, CANCELED_ORDER_STATE)
        params = {"order_id": order.order_id}
        rpc_client.notify_customer(order.channel, order.messenger_id, "driver_canceled", params)
    elif driver_request.state == INIT_REQUEST_STATE:
        query.update_driver_request_state_by_driver_id(
            driver_id,
            current_state=INIT_REQUEST_STATE,
            new_state=CANCELED_REQUEST_STATE,
        )
    db.session.commit()
    return resp()
