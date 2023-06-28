"""Bot runner."""

from maxbot import MaxBot

from .channels import schemas, telegram_impl, viber_impl


def add_channel_mixins(builder):
    """Add simple channel mixin for telegram and viber.

     send location example:
          response: |-
            <location latitude="40.7580" longitude="-73.9855" horizontal_accuracy="100"/>
     receive location example:
        - condition: message.location
          response: |-
             latitude={{ message.location.latitude }}°, longitude={{ message.location.longitude }}°

    send location button example:
          response: |-
            <location_button text="Submit your location." title="My location" />

    send contact example:
          response:  |-
             <contact phone_number="79323055802" name="Bob" />
    receive contact example:
        - condition: message.contact
          response: |-
             name={{ message.contact.name }}, phone_number={{ message.contact.phone_number }}

    send button list example:
          response: |-
            <button_list text="Choice variants.">
              <buttons>Variants-1</buttons>
              <buttons>Variants-2</buttons>
            </button_list>

    send contact button example:
          response: |-
            <contact_button text="Submit your contact." title="My phone"/>

    send remove button command example:
          response: |-
            <remove_button text="Next message without buttons" />
    """
    builder.add_message(schemas.LocationMessage, "location")
    builder.add_command(schemas.LocationCommand, "location")
    builder.add_channel_mixin(telegram_impl.LocationMixin, "telegram")
    builder.add_channel_mixin(viber_impl.LocationMixin, "viber")

    builder.add_command(schemas.KeyboardButtonCommand, "keyboard_button_location")
    builder.add_channel_mixin(telegram_impl.KeyboardButtonLocationMixin, "telegram")
    builder.add_channel_mixin(viber_impl.KeyboardButtonLocationMixin, "viber")

    builder.add_command(schemas.KeyboardButtonListCommand, "keyboard_button_list")
    builder.add_channel_mixin(telegram_impl.KeyboardButtonListMixin, "telegram")
    builder.add_channel_mixin(viber_impl.KeyboardButtonListMixin, "viber")

    builder.add_message(schemas.ContactMessage, "contact")
    builder.add_command(schemas.ContactCommand, "contact")
    builder.add_channel_mixin(telegram_impl.ContactMixin, "telegram")
    builder.add_channel_mixin(viber_impl.ContactMixin, "viber")

    builder.add_command(schemas.KeyboardButtonCommand, "keyboard_button_contact")
    builder.add_channel_mixin(telegram_impl.KeyboardButtonContactMixin, "telegram")
    builder.add_channel_mixin(viber_impl.KeyboardButtonContactMixin, "viber")

    builder.add_command(schemas.ReplyKeyboardRemoveCommand, "keyboard_button_remove")
    builder.add_channel_mixin(telegram_impl.KeyboardButtonRemoveMixin, "telegram")
    builder.add_channel_mixin(viber_impl.KeyboardButtonRemoveMixin, "viber")


customer_builder = MaxBot.builder()
add_channel_mixins(customer_builder)
customer_builder.use_package_resources(__name__, botfile="customer.yaml")
customer = customer_builder.build()

driver_builder = MaxBot.builder()
add_channel_mixins(driver_builder)
driver_builder.use_package_resources(__name__, botfile="driver.yaml")
driver = driver_builder.build()
