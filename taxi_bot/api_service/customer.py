"""Customer bot api."""
import enum
import json

from webargs import fields
from werkzeug.routing import BaseConverter, ValidationError

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
    CONFIRMED_REQUEST_STATE,
    INIT_ORDER_STATE,
    STARTED_RIDE_ORDER_STATE,
    app,
    db,
)


@enum.unique
class ChannelType(str, enum.Enum):
    """Enum ChannelType: [telegram, viber]."""

    telegram = "telegram"
    viber = "viber"


class ChannelConverter(BaseConverter):
    """Enum ChannelType converter to url path.

    See https://werkzeug.palletsprojects.com/en/2.0.x/routing/#custom-converters
    """

    def to_python(self, value):
        """Convert ChannelType to python structure."""
        try:
            request_type = ChannelType(value)
            return request_type
        except ValueError as e:
            raise ValidationError() from e

    def to_url(self, value):
        """Convert ChannelType to url part."""
        return value.value


app.url_map.converters.update(channel_type=ChannelConverter)


@app.route("/customer/<channel_type:channel>/<string:messenger_id>", methods=["POST"])
@use_body({"phone": fields.Str(required=True)})
def post_customer(body, channel, messenger_id):
    """Add new customer.

    :param dict body: Contains phone key
    :param str channel: viber or telegram
    :param str messenger_id: customer identifier in telegram or viber
    :return Flask.Response: status=200 on success,
                            status=409 on duplicate
    """
    customer = query.add_customer(messenger_id, channel.value, body["phone"])
    db.session.commit()
    return resp(data={"customer_id": customer.customer_id})


@app.route("/customer/<channel_type:channel>/<string:messenger_id>", methods=["GET"])
def get_customer(channel, messenger_id):
    """Get customer.

    :param str channel: viber or telegram
    :param str messenger_id: customer identifier in telegram or viber
    :return Flask.Response: status=200 with customer data if customer exists
    """
    customer = query.find_customer_by_messenger_id(messenger_id, channel)
    data = {}
    if customer:
        data = {"phone": customer.phone, "customer_id": customer.customer_id}
    return resp(data=data)


@app.route("/customer/<int:customer_id>/order", methods=["POST"])
@use_body(
    {
        "start_location": fields.Nested(LocationField, required=True),
        "finish_location": fields.Nested(LocationField, required=True),
    }
)
def post_order(body, customer_id):
    """Add new order and notify all drivers with appropriate request params.

    :param dict body: Contains start_location and finish_location keys
    :param str customer_id: db.customer.customer_id
    :return Flask.Response: status=200 on success,
                            status=409 on duplicate
    """
    query.add_order_if_not_exists(
        customer_id=customer_id,
        start_latitude=body["start_location"]["latitude"],
        start_longitude=body["start_location"]["longitude"],
        finish_latitude=body["finish_location"]["latitude"],
        finish_longitude=body["finish_location"]["longitude"],
        driver_id=None,
        state=INIT_ORDER_STATE,
    )
    order = query.find_active_customer_order_by_customer_id_for_update(customer_id)
    if not order:
        return conflict("Order race condition")
    if order.driver_id:
        return conflict("Order exists")
    driver_requests = query.find_all_driver_requests()
    for driver_request in driver_requests:
        # Use task queue for long procedures, for example Celery
        # See https://docs.celeryq.dev/en/stable/
        # But necessary not in_memory db for work with other os processes
        ors_result = route_client.get_ors_route(
            driver_request.latitude,
            driver_request.longitude,
            body["start_location"]["latitude"],
            body["start_location"]["longitude"],
        )
        # Skip if received ORS error.
        if not ors_result:
            continue
        to_customer_route, to_customer_summary = ors_result
        if to_customer_summary.get("distance", 0) < driver_request.radius:
            ors_result = route_client.get_ors_route(
                body["start_location"]["latitude"],
                body["start_location"]["longitude"],
                body["finish_location"]["latitude"],
                body["finish_location"]["longitude"],
            )
            # Skip if received ORS error.
            if ors_result:
                ride_route, ride_summary = ors_result
                image_url = route_client.create_route_image(to_customer_route, ride_route)
                distance = ride_summary["distance"]
                ride_summary["price"] = calculate_price(distance)
                params = {
                    "order_id": order.order_id,
                    "start_latitude": body["start_location"]["latitude"],
                    "start_longitude": body["start_location"]["longitude"],
                    "finish_latitude": body["finish_location"]["latitude"],
                    "finish_longitude": body["finish_location"]["longitude"],
                    "ride_summary": ride_summary,
                    "to_customer_summary": to_customer_summary,
                    "image_url": image_url,
                }
                rpc_client.notify_driver(driver_request.messenger_id, "customer_found", params)
                query.update_driver_request_summary(
                    driver_request.driver_request_id,
                    json.dumps(ride_summary),
                    json.dumps(to_customer_summary),
                    image_url,
                )
    db.session.commit()
    return resp(data={"order_id": order.order_id})


@app.route("/customer/<int:customer_id>/cancel", methods=["POST"])
@use_body({"order_id": fields.Integer(required=True)})
def customer_cancel(body, customer_id):
    """Update order state=canceled and notify driver about customer canceled order.

    :param dict body: Contains order_id key
    :param str customer_id: db.customer.customer_id
    :return Flask.Response: status=200 on success,
                            status=409 state error.
                            status=404 if order does not exist
    """
    order = query.find_order_by_order_id_for_update(body["order_id"])
    if not order or order.customer_id != customer_id:
        return not_found("Order not found")
    if order.state == STARTED_RIDE_ORDER_STATE:
        return conflict("Order state error")
    query.update_order_state_by_order_id(order.order_id, CANCELED_ORDER_STATE)
    if order.driver_id:
        query.update_driver_request_state_by_driver_id(
            order.driver_id,
            current_state=CONFIRMED_REQUEST_STATE,
            new_state=CANCELED_REQUEST_STATE,
        )
        rpc_client.notify_driver(
            order.driver_messenger_id,
            "customer_canceled",
            params={"order_id": order.order_id},
        )
    db.session.commit()
    return resp()
