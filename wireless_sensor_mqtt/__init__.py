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

import wireless_sensor_mqtt._homeassistant

_MQTT_DEFAULT_PORT = 1883
_MQTT_DEFAULT_TLS_PORT = 8883
_MQTT_PUBLISH_TIMEOUT_SECONDS = 16
_MQTT_PUBLISH_STATUS_POLL_INTERVAL_SECONDS = 1
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
    # *, SyntaxError on python3.5
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


def _mqtt_publish(
    *, client: paho.mqtt.client.Client, topic: str, payload: str, **kwargs
) -> None:
    _LOGGER.debug("publishing mqtt msg: topic=%s payload=%s", topic, payload)
    msg_info = client.publish(
        topic=topic, payload=payload, **kwargs
    )  # type: paho.mqtt.client.MQTTMessageInfo
    # MQTTMessageInfo.wait_for_publish() calls threading.Condition.wait() without timeout
    # https://github.com/eclipse/paho.mqtt.python/blob/v1.5.1/src/paho/mqtt/client.py#L338
    poll_start_time = time.time()
    while (
        not msg_info.is_published()
        and (time.time() - poll_start_time) < _MQTT_PUBLISH_TIMEOUT_SECONDS
    ):
        time.sleep(_MQTT_PUBLISH_STATUS_POLL_INTERVAL_SECONDS)
    # https://github.com/eclipse/paho.mqtt.python/blob/v1.5.1/src/paho/mqtt/client.py#L147
    if msg_info.rc != paho.mqtt.client.MQTT_ERR_SUCCESS:
        _LOGGER.error(
            "failed to publish on topic %s (return code %d)", topic, msg_info.rc
        )
    elif not msg_info.is_published():
        _LOGGER.warning(
            "reached timeout of %d seconds"
            " while waiting for MQTT message on topic %s to get published",
            _MQTT_PUBLISH_TIMEOUT_SECONDS,
            topic,
        )


def _publish_homeassistant_discovery_config(
    # *, SyntaxError on python3.5
    mqtt_client: paho.mqtt.client.Client,
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
        "identifiers": ["FT017TH/{}".format(homeassistant_node_id)],
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
            "name": "{} {}".format(homeassistant_node_id, name_suffix),
            "state_topic": state_topic,
            "unit_of_measurement": unit,
            "expire_after": 60 * 10,  # seconds
            "device": device_attrs,
        }
        _mqtt_publish(
            client=mqtt_client,
            topic=discovery_topic,
            payload=json.dumps(config),
            retain=True,
        )


def _measurement_iter(
    mock_measurements: bool, unlock_spi_device: bool
) -> typing.Iterator[wireless_sensor.Measurement]:
    if mock_measurements:
        logging.warning("publishing %d mocked measurements", _MEASUREMENT_MOCKS_COUNT)
        return map(lambda _: _mock_measurement(), range(_MEASUREMENT_MOCKS_COUNT))
    return wireless_sensor.FT017TH(unlock_spi_device=unlock_spi_device).receive()


def _run(
    # *, SyntaxError on python3.5
    mqtt_host: str,
    mqtt_port: int,
    mqtt_disable_tls: bool,
    mqtt_username: typing.Optional[str],
    mqtt_password: typing.Optional[str],
    mqtt_topic_prefix: str,
    homeassistant_discovery_prefix: str,
    homeassistant_node_id: str,
    mock_measurements: bool,
    unlock_spi_device: bool,
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
    _LOGGER.debug(
        "publishing measurements on topics %r and %r", temperature_topic, humidity_topic
    )
    homeassistant_discover_config_published = False
    for measurement in _measurement_iter(
        mock_measurements=mock_measurements, unlock_spi_device=unlock_spi_device
    ):
        _LOGGER.debug("received %s", measurement)
        if not homeassistant_discover_config_published:
            _publish_homeassistant_discovery_config(
                mqtt_client=mqtt_client,
                homeassistant_discovery_prefix=homeassistant_discovery_prefix,
                homeassistant_node_id=homeassistant_node_id,
                temperature_topic=temperature_topic,
                humidity_topic=humidity_topic,
            )
            homeassistant_discover_config_published = True
        _mqtt_publish(
            client=mqtt_client,
            topic=temperature_topic,
            payload="{:.02f}".format(measurement.temperature_degrees_celsius),
            retain=False,
        )
        _mqtt_publish(
            client=mqtt_client,
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
            "invalid home assistant node id {!r} (length >= 1, allowed characters: {})".format(
                args.homeassistant_node_id,
                # pylint: disable=protected-access; false positive
                wireless_sensor_mqtt._homeassistant.NODE_ID_ALLOWED_CHARS,
            )
            + "\nchange argument of --homeassistant-node-id"
        )
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
        unlock_spi_device=args.unlock_spi_device,
    )
