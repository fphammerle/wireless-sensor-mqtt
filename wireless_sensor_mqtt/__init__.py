# wireless-sensor-mqtt - MQTT client reporting measurements of FT017TH wireless thermo/hygrometers
#
# Copyright (C) 2020 Fabian Peter Hammerle <fabian@hammerle.me>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import argparse
import asyncio
import json
import logging
import pathlib
import random
import ssl
import time
import typing

import aiomqtt
import wireless_sensor

import wireless_sensor_mqtt._homeassistant

_MQTT_DEFAULT_PORT = 1883
_MQTT_DEFAULT_TLS_PORT = 8883
_MEASUREMENT_MOCKS_COUNT = 3
_MEASUREMENT_MOCKS_INTERVAL_SECONDS = 8

_LOGGER = logging.getLogger(__name__)


def _mock_measurement() -> wireless_sensor.Measurement:
    time.sleep(_MEASUREMENT_MOCKS_INTERVAL_SECONDS)
    return wireless_sensor.Measurement(
        decoding_timestamp=None,
        temperature_degrees_celsius=random.uniform(20.0, 30.0),
        relative_humidity=random.uniform(0.4, 0.6),
    )


async def _publish_homeassistant_discovery_config(
    *,
    mqtt_client: aiomqtt.Client,
    homeassistant_discovery_prefix: str,
    homeassistant_node_id: str,
    temperature_topic: str,
    humidity_topic: str,
) -> None:
    """
    https://www.home-assistant.io/docs/mqtt/discovery/
    """
    # topic format: <discovery_prefix>/<component>/[<node_id>/]<object_id>/config
    # https://www.home-assistant.io/docs/mqtt/discovery/
    # https://github.com/home-assistant/core/blob/0.117.5/homeassistant/components/mqtt/__init__.py#L274
    device_attrs = {
        # > voluptuous.error.MultipleInvalid: Device must have at least one id
        # > entifying value in 'identifiers' and/or 'connections'
        # > for dictionary value @ data['device']
        "identifiers": [f"FT017TH/{homeassistant_node_id}"],
        "model": "FT017TH",
    }
    for object_id, device_class, state_topic, unit, name_suffix in zip(
        ("temperature-degrees-celsius", "relative-humidity-percent"),
        # https://www.home-assistant.io/integrations/sensor/#device-class
        ("temperature", "humidity"),
        (temperature_topic, humidity_topic),
        ("°C", "%"),
        ("temperature", "relative humidity"),
    ):
        discovery_topic = "/".join(
            (
                homeassistant_discovery_prefix,
                "sensor",
                homeassistant_node_id,
                object_id,
                "config",
            )
        )
        unique_id = "/".join(
            (
                "fphammerle",
                "wireless-sensor-mqtt",
                "FT017TH",
                homeassistant_node_id,
                object_id,
            )
        )
        # https://www.home-assistant.io/integrations/sensor.mqtt/#configuration-variables
        # https://github.com/home-assistant/core/blob/0.117.5/homeassistant/components/mqtt/sensor.py#L50
        config = {
            "unique_id": unique_id,
            "device_class": device_class,
            # friendly_name & template for default entity_id
            "name": f"{homeassistant_node_id} {name_suffix}",
            "state_topic": state_topic,
            "unit_of_measurement": unit,
            "expire_after": 60 * 10,  # seconds
            "device": device_attrs,
        }
        await mqtt_client.publish(
            topic=discovery_topic, payload=json.dumps(config), retain=True
        )


async def _measurement_iter(
    mock_measurements: bool, gdo0_gpio_line_name: bytes, unlock_spi_device: bool
) -> typing.AsyncIterator[wireless_sensor.Measurement]:
    if mock_measurements:
        logging.warning("publishing %d mocked measurements", _MEASUREMENT_MOCKS_COUNT)
        for _ in range(_MEASUREMENT_MOCKS_COUNT):
            yield _mock_measurement()
    else:
        async for measurement in wireless_sensor.FT017TH(
            gdo0_gpio_line_name=gdo0_gpio_line_name, unlock_spi_device=unlock_spi_device
        ).receive(timeout_seconds=3600):
            yield measurement


async def _run(  # pylint: disable=too-many-locals
    *,
    mqtt_host: str,
    mqtt_port: int,
    mqtt_disable_tls: bool,
    mqtt_username: typing.Optional[str],
    mqtt_password: typing.Optional[str],
    mqtt_topic_prefix: str,
    homeassistant_discovery_prefix: str,
    homeassistant_node_id: str,
    mock_measurements: bool,
    gdo0_gpio_line_name: bytes,
    unlock_spi_device: bool,
) -> None:
    # pylint: disable=too-many-arguments
    _LOGGER.info(
        "connecting to MQTT broker %s:%d (TLS %s)",
        mqtt_host,
        mqtt_port,
        "disabled" if mqtt_disable_tls else "enabled",
    )
    if mqtt_password and not mqtt_username:
        raise ValueError("Missing MQTT username")
    async with aiomqtt.Client(
        tls_context=None if mqtt_disable_tls else ssl.create_default_context(),
        hostname=mqtt_host,
        port=mqtt_port,
        username=mqtt_username,
        password=mqtt_password,
    ) as mqtt_client:
        _LOGGER.debug("connected to MQTT broker %s:%d", mqtt_host, mqtt_port)
        temperature_topic = mqtt_topic_prefix + "/temperature-degrees-celsius"
        humidity_topic = mqtt_topic_prefix + "/relative-humidity-percent"
        _LOGGER.debug(
            "publishing measurements on topics %r and %r",
            temperature_topic,
            humidity_topic,
        )
        homeassistant_discover_config_published = False
        async for measurement in _measurement_iter(
            mock_measurements=mock_measurements,
            gdo0_gpio_line_name=gdo0_gpio_line_name,
            unlock_spi_device=unlock_spi_device,
        ):
            _LOGGER.debug("received %s", measurement)
            if not homeassistant_discover_config_published:
                await _publish_homeassistant_discovery_config(
                    mqtt_client=mqtt_client,
                    homeassistant_discovery_prefix=homeassistant_discovery_prefix,
                    homeassistant_node_id=homeassistant_node_id,
                    temperature_topic=temperature_topic,
                    humidity_topic=humidity_topic,
                )
                homeassistant_discover_config_published = True
            await mqtt_client.publish(
                topic=temperature_topic,
                payload=f"{measurement.temperature_degrees_celsius:.02f}",
                retain=False,
            )
            await mqtt_client.publish(
                topic=humidity_topic,
                # > unit_of_measurement: '%'
                # https://www.home-assistant.io/integrations/sensor.mqtt/#temperature-and-humidity-sensors
                payload=f"{(measurement.relative_humidity * 100):.02f}",
                retain=False,
            )
        raise RuntimeError("timeout waiting for packet")


def _main() -> None:
    argparser = argparse.ArgumentParser(
        description="MQTT client reporting measurements of FT017TH wireless thermo/hygrometers",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    argparser.add_argument("--mqtt-host", type=str, required=True)
    argparser.add_argument(
        "--mqtt-port",
        type=int,
        help=f"default {_MQTT_DEFAULT_TLS_PORT} ({_MQTT_DEFAULT_PORT} with --mqtt-disable-tls)",
    )
    argparser.add_argument("--mqtt-username", type=str)
    argparser.add_argument("--mqtt-disable-tls", action="store_true")
    password_argument_group = argparser.add_mutually_exclusive_group()
    password_argument_group.add_argument("--mqtt-password", type=str)
    password_argument_group.add_argument(
        "--mqtt-password-file",
        type=pathlib.Path,
        metavar="PATH",
        dest="mqtt_password_path",
        help="stripping trailing newline",
    )
    argparser.add_argument(
        "--mqtt-topic-prefix",
        type=str,
        default="wireless-sensor/FT017TH",
        help=" ",  # show default
    )
    # https://www.home-assistant.io/docs/mqtt/discovery/#discovery_prefix
    argparser.add_argument(
        "--homeassistant-discovery-prefix", type=str, default="homeassistant", help=" "
    )
    argparser.add_argument(
        "--homeassistant-node-id",
        type=str,
        # pylint: disable=protected-access
        default="FT017TH",
        help=" ",
    )
    argparser.add_argument(
        "--mock-measurements",
        action="store_true",
        help="publish random values to test MQTT connection",
    )
    argparser.add_argument(
        "--gdo0-gpio-line-name",
        type=str,
        required=True,
        # GPIO24 recommended at
        # https://github.com/fphammerle/python-cc1101/tree/v2.7.3#wiring-raspberry-pi
        help="Name of GPIO pin that CC1101's GDO0 pin is connected to."
        " Run command `gpioinfo` to get a list of all available GPIO lines."
        " Recommended: GPIO24",
    )
    # https://github.com/fphammerle/wireless-sensor/blob/v0.3.0/wireless_sensor/_cli.py#L28
    argparser.add_argument(
        "--unlock-spi-device",
        action="store_true",
        help="Release flock from SPI device file after configuring the transceiver."
        " Useful if another process (infrequently) accesses the transceiver simultaneously.",
    )
    argparser.add_argument("--debug", action="store_true", help="increase verbosity")
    argparser.add_argument(
        "--debug-cc1101",
        action="store_true",
        help="increase verbosity of cc1101 library",
    )
    args = argparser.parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s:%(levelname)s:%(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )
    logging.getLogger("cc1101").setLevel(
        logging.DEBUG if args.debug_cc1101 else logging.INFO
    )
    if args.mqtt_port:
        mqtt_port = args.mqtt_port
    elif args.mqtt_disable_tls:
        mqtt_port = _MQTT_DEFAULT_PORT
    else:
        mqtt_port = _MQTT_DEFAULT_TLS_PORT
    if args.mqtt_password_path:
        # .read_text() replaces \r\n with \n
        mqtt_password = args.mqtt_password_path.read_bytes().decode()
        if mqtt_password.endswith("\r\n"):
            mqtt_password = mqtt_password[:-2]
        elif mqtt_password.endswith("\n"):
            mqtt_password = mqtt_password[:-1]
    else:
        mqtt_password = args.mqtt_password
    # pylint: disable=protected-access; false positive for validate_node_id
    if not wireless_sensor_mqtt._homeassistant.validate_node_id(
        args.homeassistant_node_id
    ):
        raise ValueError(
            f"invalid home assistant node id {args.homeassistant_node_id!r}"
            " (length >= 1, allowed characters:"
            f" {wireless_sensor_mqtt._homeassistant.NODE_ID_ALLOWED_CHARS})"
            "\nchange argument of --homeassistant-node-id"
        )
    asyncio.run(
        _run(
            mqtt_host=args.mqtt_host,
            mqtt_port=mqtt_port,
            mqtt_disable_tls=args.mqtt_disable_tls,
            mqtt_username=args.mqtt_username,
            mqtt_password=mqtt_password,
            mqtt_topic_prefix=args.mqtt_topic_prefix,
            homeassistant_discovery_prefix=args.homeassistant_discovery_prefix,
            homeassistant_node_id=args.homeassistant_node_id,
            mock_measurements=args.mock_measurements,
            gdo0_gpio_line_name=args.gdo0_gpio_line_name.encode(),
            unlock_spi_device=args.unlock_spi_device,
        )
    )
