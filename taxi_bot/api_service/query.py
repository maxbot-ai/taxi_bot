"""DB queries."""

from sqlalchemy import or_, select, update
from sqlalchemy.dialects.sqlite import insert

from taxi_bot.api_service.schema import (
    CANCELED_ORDER_STATE,
    COMPLETED_RIDE_ORDER_STATE,
    CONFIRMED_REQUEST_STATE,
    DRIVER_CONFIRM_ORDER_STATE,
    INIT_ORDER_STATE,
    INIT_REQUEST_STATE,
    CustomerTable,
    DriverRejectOrderTable,
    DriverRequestTable,
    DriverTable,
    OrderTable,
    db,
)


def add_customer(messenger_id, channel, phone):
    """Add new customer."""
    customer = CustomerTable(messenger_id=messenger_id, channel=channel, phone=phone)
    db.session.add(customer)
    return customer


def add_driver(messenger_id, phone, first_name, last_name):
    """Add new driver."""
    driver = DriverTable(
        messenger_id=messenger_id,
        phone=phone,
        first_name=first_name,
        last_name=last_name,
    )
    db.session.add(driver)
    return driver


def add_order_if_not_exists(
    customer_id,
    start_latitude,
    start_longitude,
    finish_latitude,
    finish_longitude,
    driver_id,
    state,
):
    """Add new order, on conflict do nothing.."""
    values = [
        {
            "customer_id": customer_id,
            "start_latitude": start_latitude,
            "start_longitude": start_longitude,
            "finish_latitude": finish_latitude,
            "finish_longitude": finish_longitude,
            "driver_id": driver_id,
            "state": state,
        }
    ]
    stmt = insert(OrderTable).values(values)
    stmt = stmt.on_conflict_do_nothing(index_where=[OrderTable.customer_active_order_idx])
    return db.session.execute(stmt)


def add_driver_request_if_not_exists(driver_id, latitude, longitude, radius, state):
    """Add new driver_request, on conflict do nothing."""
    values = [
        {
            "driver_id": driver_id,
            "latitude": latitude,
            "longitude": longitude,
            "radius": radius,
            "state": state,
        }
    ]
    stmt = insert(DriverRequestTable).values(values)
    stmt = stmt.on_conflict_do_nothing(index_where=[DriverRequestTable.driver_active_request_idx])
    return db.session.execute(stmt)


def add_driver_reject_order(driver_id, order_id):
    """Add new driver_reject_order."""
    reject = DriverRejectOrderTable(driver_id=driver_id, order_id=order_id)
    db.session.add(reject)
    return reject


def update_order_driver_id_by_order_id(order_id, driver_id):
    """Update order driver_id and set state to 'confirmed' by order_id."""
    stmt = (
        update(OrderTable)
        .where(OrderTable.order_id == order_id)
        .values(driver_id=driver_id, state=DRIVER_CONFIRM_ORDER_STATE)
    )
    db.session.execute(stmt)


def update_order_state_by_order_id(order_id, state):
    """Update order state by order_id."""
    stmt = update(OrderTable).where(OrderTable.order_id == order_id).values(state=state)
    db.session.execute(stmt)


def update_driver_request_state_by_driver_id(driver_id, current_state, new_state):
    """Update driver_request state by driver_id with current state."""
    stmt = (
        update(DriverRequestTable)
        .where(DriverRequestTable.driver_id == driver_id)
        .where(DriverRequestTable.state == current_state)
        .values(state=new_state)
    )
    db.session.execute(stmt)


def update_driver_request_summary(driver_request_id, ride_summary, to_customer_summary, image_url):
    """Update driver_request additional data by driver_request_id: image and summaries."""
    stmt = (
        update(DriverRequestTable)
        .where(DriverRequestTable.driver_request_id == driver_request_id)
        .values(
            ride_summary=ride_summary,
            to_customer_summary=to_customer_summary,
            image_url=image_url,
        )
    )
    db.session.execute(stmt)


def find_driver_by_messenger_id(messenger_id):
    """Select driver by messenger_id."""
    stmt = select(DriverTable).where(DriverTable.messenger_id == messenger_id)
    return db.session.scalars(stmt).one_or_none()


def find_customer_by_messenger_id(messenger_id, channel):
    """Select customer by messenger_id and channel."""
    stmt = (
        select(CustomerTable)
        .where(CustomerTable.messenger_id == messenger_id)
        .where(CustomerTable.channel == channel)
    )
    return db.session.scalars(stmt).one_or_none()


def find_active_customer_order_by_customer_id_for_update(customer_id):
    """Select order with active state (not equals completed_ride and canceled) by customer_id."""
    stmt = (
        select(OrderTable)
        .where(OrderTable.customer_id == customer_id)
        .where(OrderTable.state.not_in([COMPLETED_RIDE_ORDER_STATE, CANCELED_ORDER_STATE]))
        .with_for_update()
    )
    return db.session.scalars(stmt).one_or_none()


def find_order_by_order_id_for_update(order_id):
    """Select order with active state (not equals completed_ride and canceled) by order_id."""
    query = (
        db.session.query(
            OrderTable.order_id,
            OrderTable.driver_id,
            OrderTable.state,
            CustomerTable.messenger_id,
            OrderTable.customer_id,
            CustomerTable.channel,
            DriverTable.messenger_id.label("driver_messenger_id"),
        )
        .join(CustomerTable, CustomerTable.customer_id == OrderTable.customer_id)
        .join(DriverTable, DriverTable.driver_id == OrderTable.driver_id, isouter=True)
        .where(OrderTable.order_id == order_id)
        .where(OrderTable.state.not_in([COMPLETED_RIDE_ORDER_STATE, CANCELED_ORDER_STATE]))
        .with_for_update()
    )
    return query.one_or_none()


def find_driver_request_by_driver_id_for_update(driver_id):
    """Select driver_request and driver info by driver_id."""
    query = (
        db.session.query(
            DriverRequestTable.driver_request_id,
            DriverRequestTable.state,
            DriverRequestTable.driver_id,
            DriverRequestTable.latitude,
            DriverRequestTable.longitude,
            DriverRequestTable.ride_summary,
            DriverRequestTable.to_customer_summary,
            DriverRequestTable.image_url,
            DriverTable.phone,
            DriverTable.first_name,
            DriverTable.last_name,
        )
        .join(DriverTable, DriverTable.driver_id == DriverRequestTable.driver_id)
        .where(DriverRequestTable.driver_id == driver_id)
        .where(DriverRequestTable.state.in_([INIT_REQUEST_STATE, CONFIRMED_REQUEST_STATE]))
        .with_for_update()
    )
    return query.one_or_none()


def find_all_active_orders(driver_id):
    """Select all orders for driver_id with state=INIT_ORDER_STAT."""
    stmt = (
        select(OrderTable)
        .join(
            DriverRejectOrderTable,
            DriverRejectOrderTable.order_id == OrderTable.order_id,
            isouter=True,
        )
        .where(OrderTable.state == INIT_ORDER_STATE)
        .where(
            or_(
                DriverRejectOrderTable.driver_reject_order_id.is_(None),
                DriverRejectOrderTable.driver_id != driver_id,
            )
        )
        .distinct()
    )
    return db.session.scalars(stmt).all()


def find_all_driver_requests():
    """Select all driver requests with state=INIT_REQUEST_STATE."""
    query = (
        db.session.query(
            DriverRequestTable.driver_request_id,
            DriverRequestTable.latitude,
            DriverRequestTable.longitude,
            DriverRequestTable.radius,
            DriverTable.messenger_id,
            DriverTable.phone,
            DriverTable.first_name,
            DriverTable.last_name,
        )
        .join(DriverTable, DriverTable.driver_id == DriverRequestTable.driver_id)
        .where(DriverRequestTable.state == INIT_REQUEST_STATE)
    )
    return query.all()
