"""Command line client."""

import logging

import click
import click_config_file

from taxi_bot.api_service import (  # noqa: F401, pylint: disable=unused-import
    common,
    customer,
    driver,
)
from taxi_bot.api_service.route import route_client
from taxi_bot.api_service.rpc import rpc_client
from taxi_bot.api_service.schema import app, db

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


@click.command()
@click.option("--bind-port", "bind_port", type=int, required=True, help="Bind port")
@click.option("--driver-bot-url", "driver_bot_url", type=str, required=True, help="Driver bot url")
@click.option(
    "--customer-bot-url",
    "customer_bot_url",
    type=str,
    required=True,
    help="Customer bot url",
)
@click.option(
    "--openrouteservice-token",
    "openrouteservice_token",
    type=str,
    required=True,
    help="Openrouteservice service token",
)
@click.option(
    "--upload-file-path",
    "upload_file_path",
    type=str,
    required=True,
    help="Upload file path",
)
@click.option(
    "--image-storage-url",
    "image_storage_url",
    type=str,
    required=True,
    help="Image storage url",
)
@click_config_file.configuration_option()
def main(
    bind_port,
    driver_bot_url,
    customer_bot_url,
    openrouteservice_token,
    upload_file_path,
    image_storage_url,
):
    """Run taxi_bot applications.

    Provides command to run taxi_bot
    """
    rpc_client.set_config(driver_bot_url, customer_bot_url)
    route_client.set_config(
        upload_file_path, f"{image_storage_url}/images", openrouteservice_token
    )
    with app.app_context():
        app.config["UPLOAD_FOLDER"] = upload_file_path
        db.create_all()
        app.run(port=bind_port)
