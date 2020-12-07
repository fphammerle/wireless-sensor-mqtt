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
import json
import logging
import pathlib
import random
import time
import typing

import paho.mqtt.client
import wireless_sensor

_MQTT_DEFAULT_PORT = 1883
_MQTT_DEFAULT_TLS_PORT = 8883
_MEASUREMENT_MOCKS_COUNT = 3
_MEASUREMENT_MOCKS_INTERVAL_SECONDS = 8

_LOGGER = logging.getLogger(__name__)


def _mqtt_on_connect(
    mqtt_client: paho.mqtt.client.Client,
    userdata: None,
    flags: typing.Dict,
    return_code: int,
) -> None:
    # pylint: disable=unused-argument; callback
    # https://github.com/eclipse/paho.mqtt.python/blob/v1.5.0/src/paho/mqtt/client.py#L441
    assert return_code == 0, return_code  # connection accepted
    mqtt_broker_host, mqtt_broker_port = mqtt_client.socket().getpeername()
    _LOGGER.debug("connected to MQTT broker %s:%d", mqtt_broker_host, mqtt_broker_port)


def _init_mqtt_client(
    *,
    host: str,
    port: int,
    username: typing.Optional[str],
    password: typing.Optional[str],
    disable_tls: bool,
) -> paho.mqtt.client.Client:
    # https://pypi.org/project/paho-mqtt/
    client = paho.mqtt.client.Client()
    client.on_connect = _mqtt_on_connect
    if not disable_tls:
        client.tls_set(ca_certs=None)  # enable tls trusting default system certs
    _LOGGER.info(
        "connecting to MQTT broker %s:%d (TLS %s)",
        host,
        port,
        "disabled" if disable_tls else "enabled",
    )
    if username:
        client.username_pw_set(username=username, password=password)
    elif password:
        raise ValueError("Missing MQTT username")
    client.connect(host=host, port=port)
    return client


def _mock_measurement() -> wireless_sensor.Measurement:
    time.sleep(_MEASUREMENT_MOCKS_INTERVAL_SECONDS)
    return wireless_sensor.Measurement(
        decoding_timestamp=None,
        temperature_degrees_celsius=random.uniform(20.0, 30.0),
        relative_humidity=random.uniform(0.4, 0.6),
    )


def _publish_homeassistant_discovery_config(
    *,
    mqtt_client: paho.mqtt.client.Client,
    homeassistant_discovery_prefix: str,
    homeassistant_node_id: str,
    temperature_topic: str,
    humidity_topic: str,
) -> None:
    # topic format: <discovery_prefix>/<component>/[<node_id>/]<object_id>/config
    # https://www.home-assistant.io/docs/mqtt/discovery/
    for object_id, state_topic, unit, name_suffix in zip(
        ("temperature-degrees-celsius", "relative-humidity-percent"),
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
        # https://www.home-assistant.io/integrations/binary_sensor.mqtt/#configuration-variables
        config = {
            "unique_id": unique_id,
            # friendly_name & template for default entity_id
            "name": "{} {}".format(homeassistant_node_id, name_suffix),
            "state_topic": state_topic,
            "unit_of_measurement": unit,
            "expire_after": 60 * 10,  # seconds
            "device": {"model": "FT017TH"},
        }
        _LOGGER.debug("publishing home assistant config on %s", discovery_topic)
        mqtt_client.publish(
            topic=discovery_topic, payload=json.dumps(config), retain=True
        )


def _run(
    *,
    mqtt_host: str,
    mqtt_port: int,
    mqtt_disable_tls: bool,
    mqtt_username: typing.Optional[str],
    mqtt_password: typing.Optional[str],
    mqtt_topic_prefix: str,
    homeassistant_discovery_prefix: str,
    homeassistant_node_id: str,  # TODO validate
    mock_measurements: bool,
) -> None:
    # pylint: disable=too-many-arguments
    # https://pypi.org/project/paho-mqtt/
    mqtt_client = _init_mqtt_client(
        host=mqtt_host,
        port=mqtt_port,
        disable_tls=mqtt_disable_tls,
        username=mqtt_username,
        password=mqtt_password,
    )
    temperature_topic = mqtt_topic_prefix + "/temperature-degrees-celsius"
    humidity_topic = mqtt_topic_prefix + "/relative-humidity-percent"
    # https://www.home-assistant.io/docs/mqtt/discovery/
    if mock_measurements:
        logging.warning("publishing %d mocked measurements", _MEASUREMENT_MOCKS_COUNT)
        measurement_iter = map(
            lambda _: _mock_measurement(), range(_MEASUREMENT_MOCKS_COUNT)
        )
    else:
        measurement_iter = wireless_sensor.FT017TH().receive()
    homeassistant_discover_config_published = False
    for measurement in measurement_iter:
        if not homeassistant_discover_config_published:
            _publish_homeassistant_discovery_config(
                mqtt_client=mqtt_client,
                homeassistant_discovery_prefix=homeassistant_discovery_prefix,
                homeassistant_node_id=homeassistant_node_id,
                temperature_topic=temperature_topic,
                humidity_topic=humidity_topic,
            )
            homeassistant_discover_config_published = True
        mqtt_client.publish(
            topic=temperature_topic,
            payload="{:.02f}".format(measurement.temperature_degrees_celsius),
            retain=False,
        )
        mqtt_client.publish(
            topic=humidity_topic,
            # > unit_of_measurement: '%'
            # https://www.home-assistant.io/integrations/sensor.mqtt/#temperature-and-humidity-sensors
            payload="{:.02f}".format(measurement.relative_humidity * 100),
            retain=False,
        )


def _main() -> None:
    argparser = argparse.ArgumentParser(
        description="MQTT client reporting measurements of FT017TH wireless thermo/hygrometers",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    argparser.add_argument("--mqtt-host", type=str, required=True)
    argparser.add_argument(
        "--mqtt-port",
        type=int,
        help="default {} ({} with --mqtt-disable-tls)".format(
            _MQTT_DEFAULT_TLS_PORT, _MQTT_DEFAULT_PORT
        ),
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
    argparser.add_argument("--debug", action="store_true", help="increase verbosity")
    args = argparser.parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s:%(levelname)s:%(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )
    logging.getLogger("cc1101").setLevel(logging.INFO)
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
    )
