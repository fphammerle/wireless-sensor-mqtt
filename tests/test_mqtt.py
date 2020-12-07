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

import logging
import unittest.mock

import pytest

import wireless_sensor_mqtt

# pylint: disable=protected-access


@pytest.mark.parametrize("mqtt_host", ["mqtt-broker.local"])
@pytest.mark.parametrize("mqtt_port", [8883, 1234])
def test__init_mqtt_client(caplog, mqtt_host, mqtt_port):
    # pylint: disable=too-many-locals,too-many-arguments
    caplog.set_level(logging.DEBUG)
    with unittest.mock.patch(
        "socket.create_connection"
    ) as create_socket_mock, unittest.mock.patch(
        "ssl.SSLContext.wrap_socket", autospec=True
    ) as ssl_wrap_socket_mock:
        ssl_wrap_socket_mock.return_value.send = len
        mqtt_client = wireless_sensor_mqtt._init_mqtt_client(
            mqtt_host=mqtt_host,
            mqtt_port=mqtt_port,
            mqtt_username=None,
            mqtt_password=None,
            mqtt_disable_tls=False,
        )
    assert caplog.records[0].levelno == logging.INFO
    assert caplog.records[0].message == (
        "connecting to MQTT broker {}:{} (TLS enabled)".format(mqtt_host, mqtt_port)
    )
    # correct remote?
    assert create_socket_mock.call_count == 1
    create_socket_args, _ = create_socket_mock.call_args
    assert create_socket_args[0] == (mqtt_host, mqtt_port)
    # ssl enabled?
    assert ssl_wrap_socket_mock.call_count == 1
    ssl_context = ssl_wrap_socket_mock.call_args[0][0]  # self
    assert ssl_context.check_hostname is True
    assert ssl_wrap_socket_mock.call_args[1]["server_hostname"] == mqtt_host
    assert mqtt_client._tls_insecure is False
    # credentials
    assert mqtt_client._username is None
    assert mqtt_client._password is None
    # connect callback
    caplog.clear()
    mqtt_client.socket().getpeername.return_value = (mqtt_host, mqtt_port)
    mqtt_client.on_connect(mqtt_client, mqtt_client._userdata, {}, 0)
    assert caplog.records[0].levelno == logging.DEBUG
    assert caplog.records[0].message == "connected to MQTT broker {}:{}".format(
        mqtt_host, mqtt_port
    )


@pytest.mark.parametrize("mqtt_host", ["mqtt-broker.local"])
@pytest.mark.parametrize("mqtt_port", [1833])
@pytest.mark.parametrize("mqtt_disable_tls", [True, False])
def test__init_mqtt_client_tls(caplog, mqtt_host, mqtt_port, mqtt_disable_tls):
    caplog.set_level(logging.INFO)
    with unittest.mock.patch("paho.mqtt.client.Client") as mqtt_client_class:
        wireless_sensor_mqtt._init_mqtt_client(
            mqtt_host=mqtt_host,
            mqtt_port=mqtt_port,
            mqtt_disable_tls=mqtt_disable_tls,
            mqtt_username=None,
            mqtt_password=None,
        )
    assert caplog.records[0].levelno == logging.INFO
    assert caplog.records[0].message == (
        "connecting to MQTT broker {}:{} (TLS {})".format(
            mqtt_host, mqtt_port, "disabled" if mqtt_disable_tls else "enabled"
        )
    )
    if mqtt_disable_tls:
        mqtt_client_class().tls_set.assert_not_called()
    else:
        mqtt_client_class().tls_set.assert_called_once_with(ca_certs=None)


@pytest.mark.parametrize("mqtt_host", ["mqtt-broker.local"])
@pytest.mark.parametrize("mqtt_port", [1833])
@pytest.mark.parametrize("mqtt_username", ["me"])
@pytest.mark.parametrize("mqtt_password", [None, "secret"])
def test__init_mqtt_client_authentication(
    mqtt_host, mqtt_port, mqtt_username, mqtt_password
):
    with unittest.mock.patch("socket.create_connection"), unittest.mock.patch(
        "ssl.SSLContext.wrap_socket"
    ) as ssl_wrap_socket_mock:
        ssl_wrap_socket_mock.return_value.send = len
        mqtt_client = wireless_sensor_mqtt._init_mqtt_client(
            mqtt_host=mqtt_host,
            mqtt_port=mqtt_port,
            mqtt_username=mqtt_username,
            mqtt_password=mqtt_password,
            mqtt_disable_tls=False,
        )
    assert mqtt_client._username.decode() == mqtt_username
    if mqtt_password:
        assert mqtt_client._password.decode() == mqtt_password
    else:
        assert mqtt_client._password is None
