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

import datetime
import json
import logging
import ssl
import typing
import unittest.mock

import _pytest
import pytest
import wireless_sensor

import wireless_sensor_mqtt

# pylint: disable=protected-access,too-many-positional-arguments


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mqtt_topic_prefix", ["wireless-sensor/FT017TH", "living-room/ft017th"]
)
@pytest.mark.parametrize("homeassistant_discovery_prefix", ["homeassistant"])
@pytest.mark.parametrize(
    "homeassistant_node_id", ["ft017th-living-room", "bed-room-sensor"]
)
async def test__publish_homeassistant_discovery_config(
    mqtt_topic_prefix, homeassistant_discovery_prefix, homeassistant_node_id
):
    mqtt_client_mock = unittest.mock.AsyncMock()
    await wireless_sensor_mqtt._publish_homeassistant_discovery_config(
        mqtt_client=mqtt_client_mock,
        homeassistant_discovery_prefix=homeassistant_discovery_prefix,
        homeassistant_node_id=homeassistant_node_id,
        temperature_topic=mqtt_topic_prefix + "/temp",
        humidity_topic=mqtt_topic_prefix + "/rel-humidity",
    )
    publish_calls_args = mqtt_client_mock.publish.call_args_list
    assert len(publish_calls_args) == 2
    for call_args in publish_calls_args:
        assert not call_args[0]  # positional args
        assert set(call_args[1].keys()) == {"topic", "payload", "retain"}
        assert call_args[1]["retain"] is True
    assert (
        publish_calls_args[0][1]["topic"]
        == f"homeassistant/sensor/{homeassistant_node_id}/temperature-degrees-celsius/config"
    )
    assert (
        publish_calls_args[1][1]["topic"]
        == f"homeassistant/sensor/{homeassistant_node_id}/relative-humidity-percent/config"
    )
    device_attrs = {
        "identifiers": ["FT017TH/" + homeassistant_node_id],
        "model": "FT017TH",
    }
    assert json.loads(publish_calls_args[0][1]["payload"]) == {
        "unique_id": f"fphammerle/wireless-sensor-mqtt/FT017TH/{homeassistant_node_id}"
        "/temperature-degrees-celsius",
        "name": f"{homeassistant_node_id} temperature",
        "state_topic": mqtt_topic_prefix + "/temp",
        "device_class": "temperature",
        "unit_of_measurement": "°C",
        "expire_after": 600,
        "device": device_attrs,
    }
    assert json.loads(publish_calls_args[1][1]["payload"]) == {
        "unique_id": f"fphammerle/wireless-sensor-mqtt/FT017TH/{homeassistant_node_id}"
        "/relative-humidity-percent",
        "name": f"{homeassistant_node_id} relative humidity",
        "state_topic": mqtt_topic_prefix + "/rel-humidity",
        "device_class": "humidity",
        "unit_of_measurement": "%",
        "expire_after": 600,
        "device": device_attrs,
    }


async def _ft017th_receive_mock(
    sensor: wireless_sensor.FT017TH, timeout_seconds: int
) -> typing.AsyncIterator[wireless_sensor.Measurement]:
    assert isinstance(sensor, wireless_sensor.FT017TH)
    assert timeout_seconds == 60 * 60
    yield wireless_sensor.Measurement(
        decoding_timestamp=datetime.datetime(2020, 12, 7, 18, 5, 1),
        temperature_degrees_celsius=23.1234567,
        relative_humidity=0.501234567,
    )
    yield wireless_sensor.Measurement(
        decoding_timestamp=datetime.datetime(2020, 12, 7, 18, 6, 19),
        temperature_degrees_celsius=24.1234567,
        relative_humidity=0.401234567,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("mqtt_host", ["mqtt-broker.local"])
@pytest.mark.parametrize("mqtt_port", [1234])
@pytest.mark.parametrize("mqtt_disable_tls", [True, False])
@pytest.mark.parametrize(
    ("mqtt_username", "mqtt_password"),
    [(None, None), ("user", None), ("username", "secret")],
)
@pytest.mark.parametrize(
    "mqtt_topic_prefix", ["wireless-sensor/FT017TH", "living-room/ft017th"]
)
@pytest.mark.parametrize("homeassistant_discovery_prefix", ["homeassistant"])
@pytest.mark.parametrize("homeassistant_node_id", ["ft017th-living-room"])
@pytest.mark.parametrize("gdo0_gpio_line_name", [b"GPIO42"])
@pytest.mark.parametrize("unlock_spi_device", [True, False])
async def test__run(  # pylint: disable=too-many-locals
    caplog: _pytest.logging.LogCaptureFixture,
    mqtt_host,
    mqtt_port,
    mqtt_disable_tls,
    mqtt_username,
    mqtt_password,
    mqtt_topic_prefix,
    homeassistant_discovery_prefix,
    homeassistant_node_id,
    gdo0_gpio_line_name: bytes,
    unlock_spi_device,
):
    # pylint: disable=too-many-arguments
    with unittest.mock.patch(
        "wireless_sensor.FT017TH.__init__", return_value=None
    ) as sensor_init_mock, unittest.mock.patch(
        "wireless_sensor.FT017TH.receive", _ft017th_receive_mock
    ):
        with unittest.mock.patch(
            "aiomqtt.Client"
        ) as mqtt_client_class_mock, unittest.mock.patch(
            "wireless_sensor_mqtt._publish_homeassistant_discovery_config"
        ) as hass_config_mock, pytest.raises(
            RuntimeError, match=r"^timeout waiting for packet$"
        ):
            caplog.set_level(logging.DEBUG)
            await wireless_sensor_mqtt._run(
                mqtt_host=mqtt_host,
                mqtt_port=mqtt_port,
                mqtt_disable_tls=mqtt_disable_tls,
                mqtt_username=mqtt_username,
                mqtt_password=mqtt_password,
                mqtt_topic_prefix=mqtt_topic_prefix,
                homeassistant_discovery_prefix=homeassistant_discovery_prefix,
                homeassistant_node_id=homeassistant_node_id,
                mock_measurements=False,
                gdo0_gpio_line_name=gdo0_gpio_line_name,
                unlock_spi_device=unlock_spi_device,
            )
    mqtt_client_class_mock.assert_called_once()
    assert not mqtt_client_class_mock.call_args[0]  # args
    mqtt_client_init_kwargs = mqtt_client_class_mock.call_args[1]
    assert set(mqtt_client_init_kwargs.keys()) == {
        "tls_context",
        "hostname",
        "port",
        "username",
        "password",
    }
    if mqtt_disable_tls:
        assert mqtt_client_init_kwargs["tls_context"] is None
    else:
        assert isinstance(mqtt_client_init_kwargs["tls_context"], ssl.SSLContext)
    assert mqtt_client_init_kwargs["hostname"] == mqtt_host
    assert mqtt_client_init_kwargs["port"] == mqtt_port
    assert mqtt_client_init_kwargs["username"] == mqtt_username
    assert mqtt_client_init_kwargs["password"] == mqtt_password
    mqtt_client_class_mock.return_value.__aenter__.assert_called_once_with()
    assert caplog.records[0].levelno == logging.INFO
    assert caplog.records[0].message == (
        # pylint: disable=consider-using-f-string
        "connecting to MQTT broker {}:{} (TLS {})".format(
            mqtt_host, mqtt_port, "disabled" if mqtt_disable_tls else "enabled"
        )
    )
    assert caplog.records[1].levelno == logging.DEBUG
    assert caplog.records[1].message == (
        f"connected to MQTT broker {mqtt_host}:{mqtt_port}"
    )
    assert caplog.records[2].levelno == logging.DEBUG
    assert caplog.records[2].message == (
        "publishing measurements on topics"
        f" '{mqtt_topic_prefix}/temperature-degrees-celsius'"
        f" and '{mqtt_topic_prefix}/relative-humidity-percent'"
    )
    sensor_init_mock.assert_called_once_with(
        gdo0_gpio_line_name=gdo0_gpio_line_name, unlock_spi_device=unlock_spi_device
    )
    mqtt_client_instance_mock = (
        mqtt_client_class_mock.return_value.__aenter__.return_value
    )
    hass_config_mock.assert_called_once_with(
        mqtt_client=mqtt_client_instance_mock,
        homeassistant_discovery_prefix=homeassistant_discovery_prefix,
        homeassistant_node_id=homeassistant_node_id,
        temperature_topic=mqtt_topic_prefix + "/temperature-degrees-celsius",
        humidity_topic=mqtt_topic_prefix + "/relative-humidity-percent",
    )
    publish_calls_args = mqtt_client_instance_mock.publish.call_args_list
    assert len(publish_calls_args) == 2 * 2
    for call_args in publish_calls_args:
        assert not call_args[0]  # positional args
        assert set(call_args[1].keys()) == {"topic", "payload", "retain"}
        assert call_args[1]["retain"] is False
    assert (
        publish_calls_args[0][1]["topic"]
        == publish_calls_args[2][1]["topic"]
        == mqtt_topic_prefix + "/temperature-degrees-celsius"
    )
    assert (
        publish_calls_args[1][1]["topic"]
        == publish_calls_args[3][1]["topic"]
        == mqtt_topic_prefix + "/relative-humidity-percent"
    )
    assert publish_calls_args[0][1]["payload"] == "23.12"
    assert publish_calls_args[1][1]["payload"] == "50.12"
    assert publish_calls_args[2][1]["payload"] == "24.12"
    assert publish_calls_args[3][1]["payload"] == "40.12"
    assert caplog.records[3].levelno == logging.DEBUG
    assert caplog.records[3].message == (
        "received Measurement("
        "decoding_timestamp=datetime.datetime(2020, 12, 7, 18, 5, 1)"
        ", temperature_degrees_celsius=23.1234567"
        ", relative_humidity=0.501234567)"
    )
    assert caplog.records[4].levelno == logging.DEBUG
    assert caplog.records[4].message == (
        "received Measurement("
        "decoding_timestamp=datetime.datetime(2020, 12, 7, 18, 6, 19)"
        ", temperature_degrees_celsius=24.1234567"
        ", relative_humidity=0.401234567)"
    )
    assert not caplog.records[5:]


@pytest.mark.asyncio
@pytest.mark.parametrize("mqtt_disable_tls", [True, False])
async def test__run_mqtt_client_authentication_missing_username(mqtt_disable_tls):
    with unittest.mock.patch("aiomqtt.Client") as mqtt_client_class_mock, pytest.raises(
        ValueError, match=r"^Missing MQTT username$"
    ):
        await wireless_sensor_mqtt._run(
            mqtt_host="mqtt-broker.local",
            mqtt_port=1883,
            mqtt_disable_tls=mqtt_disable_tls,
            mqtt_username=None,
            mqtt_password="secret",
            mqtt_topic_prefix="wireless-sensor/FT017TH",
            homeassistant_discovery_prefix="homeassistant",
            homeassistant_node_id="ft017th-living-room",
            mock_measurements=False,
            gdo0_gpio_line_name=b"GPIO42",
            unlock_spi_device=False,
        )
    mqtt_client_class_mock.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("mqtt_topic_prefix", ["ft017th"])
async def test__run_mock_measurements(mqtt_topic_prefix):
    # pylint: disable=too-many-arguments
    with unittest.mock.patch(
        "aiomqtt.Client"
    ) as mqtt_client_class_mock, unittest.mock.patch(
        "time.sleep"
    ) as sleep_mock, unittest.mock.patch(
        "wireless_sensor_mqtt._publish_homeassistant_discovery_config"
    ) as hass_config_mock, pytest.raises(
        RuntimeError, match=r"^timeout waiting for packet$"
    ):
        await wireless_sensor_mqtt._run(
            mqtt_host="mqtt-broker.local",
            mqtt_port=1234,
            mqtt_disable_tls=True,
            mqtt_username=None,
            mqtt_password=None,
            mqtt_topic_prefix=mqtt_topic_prefix,
            homeassistant_discovery_prefix="homeassistant",
            homeassistant_node_id="ft017th-living-room",
            mock_measurements=True,
            gdo0_gpio_line_name=b"GPIO24",
            unlock_spi_device=False,
        )
    hass_config_mock.assert_called_once()
    assert all(c[0][0] == 8 for c in sleep_mock.call_args_list)
    mqtt_client_instance_mock = (
        mqtt_client_class_mock.return_value.__aenter__.return_value
    )
    publish_calls_args = mqtt_client_instance_mock.publish.call_args_list
    assert len(publish_calls_args) == 2 * 3
    for call_args in publish_calls_args:
        assert not call_args[0]  # positional args
        assert set(call_args[1].keys()) == {"topic", "payload", "retain"}
        assert call_args[1]["retain"] is False
        assert float(call_args[1]["payload"]) > 0
    assert (
        publish_calls_args[0][1]["topic"]
        == publish_calls_args[2][1]["topic"]
        == publish_calls_args[4][1]["topic"]
        == mqtt_topic_prefix + "/temperature-degrees-celsius"
    )
    assert (
        publish_calls_args[1][1]["topic"]
        == publish_calls_args[3][1]["topic"]
        == publish_calls_args[5][1]["topic"]
        == mqtt_topic_prefix + "/relative-humidity-percent"
    )
