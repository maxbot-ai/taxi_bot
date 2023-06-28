"""DB schema."""
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import (
    CheckConstraint,
    Column,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
db = SQLAlchemy(app)


INIT_ORDER_STATE = "init"
DRIVER_CONFIRM_ORDER_STATE = "confirm"
DRIVER_ARRIVED_ORDER_STATE = "driver_arrived"
STARTED_RIDE_ORDER_STATE = "started_ride"
COMPLETED_RIDE_ORDER_STATE = "completed_ride"
CANCELED_ORDER_STATE = "canceled"

INIT_REQUEST_STATE = "init"
CONFIRMED_REQUEST_STATE = "confirmed"
COMPLETED_REQUEST_STATE = "completed"
CANCELED_REQUEST_STATE = "canceled"


class DriverTable(db.Model):
    """Stores the information about a driver."""

    __tablename__ = "driver"

    driver_id = Column(Integer, primary_key=True)
    messenger_id = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String)

    def __repr__(self):
        """Representation."""
        return (
            f"<Driver(driver_id={self.driver_id!r}, messenger_id={self.messenger_id!r},"
            f"phone={self.phone!r}), first_name={self.first_name!r}, last_name={self.last_name!r}>"
        )

    __table_args__ = (UniqueConstraint("messenger_id"), UniqueConstraint("phone"))


class CustomerTable(db.Model):
    """Stores the information about a customer."""

    __tablename__ = "customer"

    customer_id = Column(Integer, primary_key=True)
    messenger_id = Column(String, nullable=False)
    channel = Column(Enum("telegram", "viber", name="Channel"), nullable=False)
    phone = Column(String, nullable=False)

    def __repr__(self):
        """Representation."""
        return (
            f"<Customer(customer_id={self.customer_id!r}, messenger_id={self.messenger_id!r}, "
            f"channel={self.channel!r}, phone={self.phone!r})>"
        )

    __table_args__ = (
        UniqueConstraint("messenger_id", "channel"),
        UniqueConstraint("channel", "phone"),
    )


class OrderTable(db.Model):
    """Stores information and state of a order."""

    __tablename__ = "order"

    order_id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customer.customer_id"), nullable=False)
    start_latitude = Column(Float, nullable=False)
    start_longitude = Column(Float, nullable=False)
    finish_latitude = Column(Float, nullable=False)
    finish_longitude = Column(Float, nullable=False)
    driver_id = Column(Integer, ForeignKey("driver.driver_id"))
    state = Column(
        Enum(
            INIT_ORDER_STATE,
            DRIVER_CONFIRM_ORDER_STATE,
            DRIVER_ARRIVED_ORDER_STATE,
            STARTED_RIDE_ORDER_STATE,
            COMPLETED_RIDE_ORDER_STATE,
            CANCELED_ORDER_STATE,
            name="State",
        ),
        nullable=False,
    )

    def __repr__(self):
        """Representation."""
        return (
            f"<Order(order_id={self.order_id!r}, customer_id={self.customer_id!r}, "
            f"start_latitude={self.start_latitude!r}, start_longitude={self.start_longitude!r}, "
            f"finish_latitude={self.finish_latitude!r}, finish_longitude={self.finish_longitude!r}, "
            f"driver_id={self.driver_id!r}, state={self.state!r})"
        )

    customer_active_order_idx = Index(
        "customer_active_order",
        customer_id,
        unique=True,
        sqlite_where=state.in_(
            [
                INIT_ORDER_STATE,
                DRIVER_CONFIRM_ORDER_STATE,
                DRIVER_ARRIVED_ORDER_STATE,
                STARTED_RIDE_ORDER_STATE,
            ]
        ),
    )

    __table_args__ = (
        CheckConstraint("-90 < start_latitude AND start_latitude < 90"),
        CheckConstraint("-180 < start_longitude AND start_longitude < 180"),
        CheckConstraint("-90 < finish_latitude AND finish_latitude < 90"),
        CheckConstraint("-180 < finish_longitude AND finish_longitude < 180"),
        CheckConstraint(
            "start_latitude != finish_latitude OR start_longitude != finish_longitude"
        ),
        customer_active_order_idx,
    )


class DriverRequestTable(db.Model):
    """Stores information and state of a driver order request."""

    __tablename__ = "driver_request"

    driver_request_id = Column(Integer, primary_key=True)
    driver_id = Column(Integer, ForeignKey("driver.driver_id"), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    radius = Column(Integer, nullable=False)
    ride_summary = Column(String)
    to_customer_summary = Column(String)
    image_url = Column(String)
    state = Column(
        Enum(
            INIT_REQUEST_STATE,
            CONFIRMED_REQUEST_STATE,
            COMPLETED_REQUEST_STATE,
            CANCELED_REQUEST_STATE,
            name="State",
        ),
        nullable=False,
    )

    def __repr__(self):
        """Representation."""
        return (
            f"< DriverRequest(driver_request_id={self.driver_request_id!r}, driver_id={self.driver_id!r}, "
            f"latitude={self.latitude!r})>, longitude={self.longitude!r}, "
            f"radius={self.radius!r})>, state={self.state!r}"
        )

    driver_active_request_idx = Index(
        "driver_active_request",
        driver_id,
        unique=True,
        sqlite_where=state.in_([INIT_REQUEST_STATE, CONFIRMED_REQUEST_STATE]),
    )

    __table_args__ = (
        CheckConstraint("-90 < latitude AND latitude < 90"),
        CheckConstraint("-180 < longitude AND longitude < 180"),
        CheckConstraint("0 < radius AND radius <= 300"),
        driver_active_request_idx,
    )


class DriverRejectOrderTable(db.Model):
    """Stores driver reject from order."""

    __tablename__ = "driver_reject_order"

    driver_reject_order_id = Column(Integer, primary_key=True)
    driver_id = Column(Integer, ForeignKey("driver.driver_id"), nullable=False)
    order_id = Column(Integer, ForeignKey("order.order_id"), nullable=False)

    def __repr__(self):
        """Representation."""
        return (
            f"<DriverReject(driver_reject_order_id={self.driver_reject_order_id!r}, "
            f"driver_id={self.driver_id!r}, order_id={self.order_id!r})>"
        )

    __table_args__ = (UniqueConstraint("driver_id", "order_id"),)
