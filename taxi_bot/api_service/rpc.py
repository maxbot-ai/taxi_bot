"""Rpc client."""

import logging

from requests_toolbelt.sessions import BaseUrlSession

logger = logging.getLogger(__name__)

_HEADERS = {"Content-Type": "application/json"}


class _RpcClient:
    def __init__(self):
        self.driver_session = None
        self.customer_session = None

    def set_config(self, driver_bot_url, customer_bot_url):
        """Set configuration.

        :param str driver_bot_url: Driver bot url
        :param str customer_bot_url: Customer bot url
        """
        self.driver_session = BaseUrlSession(base_url=driver_bot_url)
        self.customer_session = BaseUrlSession(base_url=customer_bot_url)

    def notify_customer(self, channel, messenger_id, method, params):
        """Notify customer.

        :param str channel: Customer channel (telegram or viber)
        :param str messenger_id: Customer messenger_id
        :param str method: driver_found, driver_arrived, ride_started, ride_completed or driver_canceled
        :param dict params: Additional parameters
        """
        data = {"method": method, "params": params}
        logger.debug("notify_customer: method=%s, params=%s", method, params)
        response = self.customer_session.post(
            url=f"/rpc/{channel}/{messenger_id}", json=data, headers=_HEADERS
        )
        response.raise_for_status()

    def notify_driver(self, messenger_id, method, params):
        """Notify driver.

        :param str messenger_id: Customer messenger_id
        :param str method: customer_found or customer_canceled
        :param dict params: Additional parameters
        """
        data = {"method": method, "params": params}
        logger.debug("notify_driver: method=%s, params=%s", method, params)
        response = self.driver_session.post(
            f"/rpc/telegram/{messenger_id}", json=data, headers=_HEADERS
        )
        response.raise_for_status()


rpc_client = _RpcClient()
