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
import unittest.mock

import pytest
import wireless_sensor

import wireless_sensor_mqtt

# pylint: disable=protected-access,too-many-positional-arguments


@pytest.mark.parametrize(
    "mqtt_topic_prefix", ["wireless-sensor/FT017TH", "living-room/ft017th"]
)
@pytest.mark.parametrize("homeassistant_discovery_prefix", ["homeassistant"])
@pytest.mark.parametrize(
    "homeassistant_node_id", ["ft017th-living-room", "bed-room-sensor"]
)
def test__publish_homeassistant_discovery_config(
    mqtt_topic_prefix, homeassistant_discovery_prefix, homeassistant_node_id
):
    mqtt_client_mock = unittest.mock.MagicMock()
    wireless_sensor_mqtt._publish_homeassistant_discovery_config(
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
def test__run(  # pylint: disable=too-many-locals
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
        "wireless_sensor.FT017TH.receive",
        side_effect=[
            [
                wireless_sensor.Measurement(
                    decoding_timestamp=datetime.datetime(2020, 12, 7, 18, 5, 1),
                    temperature_degrees_celsius=23.1234567,
                    relative_humidity=0.501234567,
                ),
                wireless_sensor.Measurement(
                    decoding_timestamp=datetime.datetime(2020, 12, 7, 18, 6, 19),
                    temperature_degrees_celsius=24.1234567,
                    relative_humidity=0.401234567,
                ),
            ]
        ],
    ):
        mqtt_client_mock = unittest.mock.MagicMock()
        with unittest.mock.patch(
            "wireless_sensor_mqtt._init_mqtt_client"
        ) as init_mqtt_client_mock, unittest.mock.patch(
            "wireless_sensor_mqtt._publish_homeassistant_discovery_config"
        ) as hass_config_mock:
            init_mqtt_client_mock.return_value = mqtt_client_mock
            wireless_sensor_mqtt._run(
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
    # pylint: disable=duplicate-code
    init_mqtt_client_mock.assert_called_once_with(
        host=mqtt_host,
        port=mqtt_port,
        disable_tls=mqtt_disable_tls,
        username=mqtt_username,
        password=mqtt_password,
    )
    sensor_init_mock.assert_called_once_with(
        gdo0_gpio_line_name=gdo0_gpio_line_name, unlock_spi_device=unlock_spi_device
    )
    hass_config_mock.assert_called_once_with(
        mqtt_client=mqtt_client_mock,
        homeassistant_discovery_prefix=homeassistant_discovery_prefix,
        homeassistant_node_id=homeassistant_node_id,
        temperature_topic=mqtt_topic_prefix + "/temperature-degrees-celsius",
        humidity_topic=mqtt_topic_prefix + "/relative-humidity-percent",
    )
    publish_calls_args = mqtt_client_mock.publish.call_args_list
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


@pytest.mark.parametrize("mqtt_topic_prefix", ["ft017th"])
def test__run_mock_measurements(mqtt_topic_prefix):
    # pylint: disable=too-many-arguments
    mqtt_client_mock = unittest.mock.MagicMock()
    with unittest.mock.patch(
        "wireless_sensor_mqtt._init_mqtt_client"
    ) as init_mqtt_client_mock, unittest.mock.patch(
        "time.sleep"
    ) as sleep_mock, unittest.mock.patch(
        "wireless_sensor_mqtt._publish_homeassistant_discovery_config"
    ) as hass_config_mock:
        init_mqtt_client_mock.return_value = mqtt_client_mock
        wireless_sensor_mqtt._run(
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
    init_mqtt_client_mock.assert_called_once()
    hass_config_mock.assert_called_once()
    assert all(c[0][0] == 8 for c in sleep_mock.call_args_list)
    publish_calls_args = mqtt_client_mock.publish.call_args_list
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
