"""Implementation of simple viber channel mixin."""
from viberbot.api.messages import contact_message, location_message, text_message
from viberbot.api.messages.keyboard_message import KeyboardMessage
from viberbot.api.viber_requests import ViberMessageRequest
from viberbot.api.viber_requests.viber_request import ViberRequest

_MIN_API_VERSION = 4


def _create_phone_keyboard(title):
    """Create share contact button.

    See https://developers.viber.com/docs/tools/keyboards/#buttons-parameters param ActionType

    require adding any text in the ActionBody parameter
    """
    button = {
        "Text": title,
        "ActionBody": "require adding any text in the ActionBody parameter",
        "ActionType": "share-phone",
        "Silent": True,
    }
    return {"Type": "keyboard", "Buttons": [button]}


def _create_button_list_keyboard(button_names, action_type="reply"):
    """Create buttons.

    See https://developers.viber.com/docs/tools/keyboards/#buttons-parameters
    """
    buttons = []
    for text in button_names:
        buttons.append({"Text": text, "ActionBody": text, "ActionType": action_type})
    return {"Type": "keyboard", "Buttons": buttons}


class KeyboardButtonLocationMixin:
    """Mixin for send of share-location button."""

    async def send_keyboard_button_location(self, command: dict, dialog: dict):
        """Send a location button command, :class:`KeyboardButtonCommand`.

        See https://developers.viber.com/docs/tools/keyboards/#buttons-parameters, ActionType=location-picker
        See https://developers.viber.com/docs/api/python-bot-api/#KeyboardMessage

        :param dict command: a command with the payload :attr:`~KeyboardButtonCommand`.
        :param dict dialog: a dialog we respond in, with the schema :class:`~maxbot.schemas.DialogSchema`
        """
        text = text_message.TextMessage(text=command["keyboard_button_location"]["text"])
        keyboard = _create_button_list_keyboard(
            [command["keyboard_button_location"]["title"]],
            action_type="location-picker",
        )
        buttons = KeyboardMessage(keyboard=keyboard, min_api_version=_MIN_API_VERSION)
        await self._api.send_message(dialog["user_id"], text)
        await self._api.send_message(dialog["user_id"], buttons)


class KeyboardButtonListMixin:
    """Mixin for send of button list."""

    async def send_keyboard_button_list(self, command: dict, dialog: dict):
        """Send buttons command, :class:`KeyboardButtonListCommand`.

        See https://developers.viber.com/docs/tools/keyboards/#buttons-parameters
        See https://developers.viber.com/docs/api/python-bot-api/#KeyboardMessage

        :param dict command: a command with the payload :attr:`~KeyboardButtonListCommand`.
        :param dict dialog: a dialog we respond in, with the schema :class:`~maxbot.schemas.DialogSchema`
        """
        text = text_message.TextMessage(text=command["keyboard_button_list"]["text"])
        keyboard = _create_button_list_keyboard(command["keyboard_button_list"]["buttons"])
        buttons = KeyboardMessage(keyboard=keyboard, min_api_version=_MIN_API_VERSION)
        await self._api.send_message(dialog["user_id"], text)
        await self._api.send_message(dialog["user_id"], buttons)


class LocationMixin:
    """Mixin for send and receive location message."""

    async def receive_location(self, request: ViberRequest):
        """Receive location data message, :class:`LocationMessage`.

        See https://developers.viber.com/docs/api/rest-bot-api/#location-message for more information.

        :param ViberRequest request: An incoming update.
        :return dict: A message with the payload :class:`~LocationMessage`.
        """
        if isinstance(request, ViberMessageRequest):
            message = request.message
            if isinstance(message, location_message.LocationMessage):
                return {
                    "location": {
                        "longitude": message.location.longitude,
                        "latitude": message.location.latitude,
                    }
                }

    async def send_location(self, command: dict, dialog: dict):
        """Send location data command, :class:`LocationCommand`.

        See https://developers.viber.com/docs/api/rest-bot-api/#location-message for more information.

        :param dict command: A command with the payload :attr:`~LocationCommand`.
        :param dict dialog: A dialog we respond in, with the schema :class:`~maxbot.schemas.DialogSchema`.
        """
        location = location_message.Location(
            command["location"]["latitude"], command["location"]["longitude"]
        )
        message = location_message.LocationMessage(location=location)
        await self._api.send_message(dialog["user_id"], message)


class KeyboardButtonRemoveMixin:
    """Mixin for remove button of previous messages from client chat."""

    async def send_keyboard_button_remove(self, command: dict, dialog: dict):
        """Send empty (invisible) button.

        Send button for remove buttons of
        previous message from client chat, :class:`ReplyKeyboardRemoveCommand`.
        See https://developers.viber.com/docs/tools/keyboards/#general-keyboard-parameters
        InputFieldState=hidden
        ActionType=none

        :param dict command: A command with the payload :attr:`ReplyKeyboardRemoveCommand`.
        :param dict dialog: A dialog we respond in, with the schema :class:`~maxbot.schemas.DialogSchema`.
        """
        empty_button = {
            "Type": "keyboard",
            "InputFieldState": "hidden",
            "Buttons": [{"Text": "", "ActionBody": "", "ActionType": "none", "Silent": True}],
        }
        keybord = KeyboardMessage(keyboard=empty_button, min_api_version=_MIN_API_VERSION)
        text = text_message.TextMessage(text=command["keyboard_button_remove"]["text"])
        await self._api.send_message(dialog["user_id"], keybord)
        await self._api.send_message(dialog["user_id"], text)


class KeyboardButtonContactMixin:
    """Mixin for send of contact-location button."""

    async def send_keyboard_button_contact(self, command: dict, dialog: dict):
        """Send share-contact button command, :class:`KeyboardButtonCommand`.

        See https://developers.viber.com/docs/tools/keyboards/#buttons-parameters, ActionType=share-phone
        See https://developers.viber.com/docs/api/python-bot-api/#KeyboardMessage

        :param dict command: A command with the payload :attr:`KeyboardButtonCommand`.
        :param dict dialog: A dialog we respond in, with the schema :class:`~maxbot.schemas.DialogSchema`.
        """
        keyboard = _create_phone_keyboard(command["keyboard_button_contact"]["title"])
        button = KeyboardMessage(keyboard=keyboard, min_api_version=_MIN_API_VERSION)
        text = text_message.TextMessage(text=command["keyboard_button_contact"]["text"])
        await self._api.send_message(dialog["user_id"], text)
        await self._api.send_message(dialog["user_id"], button)


class ContactMixin:
    """Mixin for send and receive contact message."""

    async def receive_contact(self, request: ViberRequest):
        """Receive contact data message, :class:`ContactMessage`.

        See https://developers.viber.com/docs/api/rest-bot-api/#contact-message for more information.
        :param ViberRequest request: An incoming update.
        :return dict: A message with the payload :class:`~ContactMessage`.
        """
        if isinstance(request, ViberMessageRequest):
            message = request.message
            if isinstance(message, contact_message.ContactMessage):
                contact = {
                    "phone_number": message.contact.phone_number,
                    "first_name": message.contact.name or "(no name)",
                }
                return {"contact": contact}

    async def send_contact(self, command: dict, dialog: dict):
        """Send contact data command, :class:`ContactCommand`.

        See https://developers.viber.com/docs/api/rest-bot-api/#contact-message for more information.

        :param dict command: A command with the payload :attr:`~ContactCommand`.
        :param dict dialog: A dialog we respond in, with the schema :class:`~maxbot.schemas.DialogSchema`.
        """
        name = text_message.TextMessage(text=f'{command["contact"]["first_name"]}')
        phone = text_message.TextMessage(text=f'{command["contact"]["phone_number"]}')
        await self._api.send_message(dialog["user_id"], name)
        await self._api.send_message(dialog["user_id"], phone)
