"""Schemas for channel mixin."""

from marshmallow import Schema, fields, validate


class LocationMessage(Schema):
    """A point on the map received from the user."""

    # Longitude as defined by receiver
    longitude = fields.Float(required=True)

    # Latitude as defined by receiver
    latitude = fields.Float(required=True)


class LocationCommand(Schema):
    """A point on the map to send to the user."""

    # Longitude as defined by sender
    longitude = fields.Float(required=True)

    # Latitude as defined by sender
    latitude = fields.Float(required=True)

    # The radius of uncertainty for the location, measured in meters
    horizontal_accuracy = fields.Float(validate=validate.Range(0, 1500))


class KeyboardButtonCommand(Schema):
    """A single button to send to the user."""

    # Text message with button by sender
    text = fields.String(required=True)

    # Button title by sender
    title = fields.String(required=True)


class KeyboardButtonListCommand(Schema):
    """A button list to send to the user."""

    # Text message with buttons by sender
    text = fields.String(required=True)

    # Button titles by sender
    buttons = fields.List(fields.String)


class ReplyKeyboardRemoveCommand(Schema):
    """A remove button message to send to the user.

    For remove buttons of previous message from client chat.
    """

    # Text message with button by sender
    text = fields.String(required=True)


class ContactMessage(Schema):
    """A contact message received from the user."""

    # Contact phone number as defined by receiver
    phone_number = fields.String(required=True)

    # Contact name as defined by receiver
    first_name = fields.String(required=True)

    # Contact last_name as defined by receiver
    last_name = fields.String()


class ContactCommand(Schema):
    """A contact message to send to the user."""

    # Contact phone number as defined by sender
    phone_number = fields.String(required=True)

    # Contact first_name as defined by sender
    first_name = fields.String(required=True)

    # Contact last_name as defined by sender
    last_name = fields.String()
