"""Implementation of simple telegram channel mixin."""

from telegram import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove


class KeyboardButtonLocationMixin:
    """Mixin for send of share-location button."""

    async def send_keyboard_button_location(self, command: dict, dialog: dict):
        """Send share-location button command, :class:`KeyboardButtonCommand`.

        See https://core.telegram.org/bots/api#sendmessage.
        See https://core.telegram.org/bots/api#keyboardbutton, param request_location

        :param dict command: A command with the payload :attr:`KeyboardButtonCommand`.
        :param dict dialog: A dialog we respond in, with the schema :class:`~maxbot.schemas.DialogSchema`.
        """
        keyboard = [
            [KeyboardButton(command["keyboard_button_location"]["title"], request_location=True)]
        ]
        await self.bot.send_message(
            dialog["user_id"],
            text=command["keyboard_button_location"]["text"],
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
        )


class KeyboardButtonListMixin:
    """Mixin for send of button list."""

    async def send_keyboard_button_list(self, command: dict, dialog: dict):
        """Send button list command, :class:`KeyboardButtonListCommand`.

        See https://core.telegram.org/bots/api#replykeyboardmarkup
        See https://core.telegram.org/bots/api#keyboardbutton

        :param dict command: A command with the payload :attr:`KeyboardButtonListCommand`.
        :param dict dialog: A dialog we respond in, with the schema :class:`~maxbot.schemas.DialogSchema`.
        """
        keyboard = [[KeyboardButton(text)] for text in command["keyboard_button_list"]["buttons"]]
        await self.bot.send_message(
            dialog["user_id"],
            text=command["keyboard_button_list"]["text"],
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
        )


class LocationMixin:
    """Mixin for send and receive location message."""

    async def receive_location(self, update):
        """Receive :class:`LocationMessage`.

        See https://core.telegram.org/bots/api#location for more information.

        :param Update update: An incoming update.
        :return dict: A message with the payload :class:`~LocationMessage`.
        """
        if update.message and update.message.location:
            return {
                "location": {
                    "longitude": update.message.location.longitude,
                    "latitude": update.message.location.latitude,
                }
            }

    async def send_location(self, command: dict, dialog: dict):
        """Send :class:`LocationCommand`.

        See https://core.telegram.org/bots/api#sendlocation for more information.

        :param dict command: A command with the payload :attr:`~LocationCommand`.
        :param dict dialog: A dialog we respond in, with the schema :class:`~maxbot.schemas.DialogSchema`.
        """
        await self.bot.send_location(
            dialog["user_id"],
            latitude=command["location"]["latitude"],
            longitude=command["location"]["longitude"],
            horizontal_accuracy=command["location"]["horizontal_accuracy"],
        )


class KeyboardButtonRemoveMixin:
    """Mixin for remove button of previous messages from client chat."""

    async def send_keyboard_button_remove(self, command: dict, dialog: dict):
        """Send empty (invisible) button.

        Send button for remove buttons of
        previous message from client chat, :class:`ReplyKeyboardRemoveCommand`.

        See https://core.telegram.org/bots/api#replykeyboardremove,

        :param dict command: A command with the payload :attr:`ReplyKeyboardRemoveCommand`.
        :param dict dialog: A dialog we respond in, with the schema :class:`~maxbot.schemas.DialogSchema`.
        """
        await self.bot.send_message(
            dialog["user_id"],
            text=command["keyboard_button_remove"]["text"],
            reply_markup=ReplyKeyboardRemove(),
        )


class KeyboardButtonContactMixin:
    """Mixin for send of contact-location button."""

    async def send_keyboard_button_contact(self, command: dict, dialog: dict):
        """Send share-contact button command, :class:`KeyboardButtonCommand`.

        See https://core.telegram.org/bots/api#keyboardbutton, param request_contact

        :param dict command: A command with the payload :attr:`KeyboardButtonCommand`.
        :param dict dialog: A dialog we respond in, with the schema :class:`~maxbot.schemas.DialogSchema`.
        """
        keyboard = [
            [KeyboardButton(command["keyboard_button_contact"]["title"], request_contact=True)]
        ]
        await self.bot.send_message(
            dialog["user_id"],
            text=command["keyboard_button_contact"]["text"],
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
        )


class ContactMixin:
    """Mixin for send and receive contact message."""

    async def receive_contact(self, update):
        """Receive contact data message, :class:`ContactMessage`.

        See https://core.telegram.org/bots/api#contact for more information.

        :param Update update: An incoming update.
        :return dict: A message with the payload :class:`~ContactMessage`.
        """
        if update.message and update.message.contact:
            contact = {
                "phone_number": update.message.contact.phone_number,
                "first_name": update.message.contact.first_name,
            }
            if update.message.contact.last_name:
                contact["last_name"] = update.message.contact.last_name
            return {"contact": contact}

    async def send_contact(self, command: dict, dialog: dict):
        """Send contact data command, :class:`ContactCommand`.

        See https://core.telegram.org/bots/api#sendcontact for more information.

        :param dict command: A command with the payload :attr:`~ContactCommand`.
        :param dict dialog: A dialog we respond in, with the schema :class:`~maxbot.schemas.DialogSchema`.
        """
        await self.bot.send_contact(
            chat_id=dialog["user_id"],
            phone_number=command["contact"]["phone_number"],
            first_name=command["contact"]["first_name"],
            last_name=command["contact"].get("last_name"),
        )
