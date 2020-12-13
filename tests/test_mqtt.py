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

import itertools
import logging
import unittest.mock

import paho.mqtt.client
import pytest

import wireless_sensor_mqtt

# pylint: disable=protected-access


@pytest.mark.parametrize("host", ["mqtt-broker.local"])
@pytest.mark.parametrize("port", [8883, 1234])
def test__init_mqtt_client(caplog, host, port):
    # pylint: disable=too-many-locals,too-many-arguments
    caplog.set_level(logging.DEBUG)
    with unittest.mock.patch(
        "socket.create_connection"
    ) as create_socket_mock, unittest.mock.patch(
        "ssl.SSLContext.wrap_socket", autospec=True
    ) as ssl_wrap_socket_mock:
        ssl_wrap_socket_mock.return_value.send = len
        mqtt_client = wireless_sensor_mqtt._init_mqtt_client(
            host=host, port=port, username=None, password=None, disable_tls=False
        )
    assert caplog.records[0].levelno == logging.INFO
    assert caplog.records[0].message == (
        "connecting to MQTT broker {}:{} (TLS enabled)".format(host, port)
    )
    # correct remote?
    assert create_socket_mock.call_count == 1
    create_socket_args, _ = create_socket_mock.call_args
    assert create_socket_args[0] == (host, port)
    # ssl enabled?
    assert ssl_wrap_socket_mock.call_count == 1
    ssl_context = ssl_wrap_socket_mock.call_args[0][0]  # self
    assert ssl_context.check_hostname is True
    assert ssl_wrap_socket_mock.call_args[1]["server_hostname"] == host
    assert mqtt_client._tls_insecure is False
    # credentials
    assert mqtt_client._username is None
    assert mqtt_client._password is None
    # connect callback
    caplog.clear()
    mqtt_client.socket().getpeername.return_value = (host, port)
    # pylint: disable=not-callable; false positive
    mqtt_client.on_connect(mqtt_client, mqtt_client._userdata, {}, 0)
    assert caplog.records[0].levelno == logging.DEBUG
    assert caplog.records[0].message == "connected to MQTT broker {}:{}".format(
        host, port
    )


@pytest.mark.parametrize("host", ["mqtt-broker.local"])
@pytest.mark.parametrize("port", [1833])
@pytest.mark.parametrize("disable_tls", [True, False])
def test__init_mqtt_client_tls(caplog, host, port, disable_tls):
    caplog.set_level(logging.INFO)
    with unittest.mock.patch("paho.mqtt.client.Client") as mqtt_client_class:
        wireless_sensor_mqtt._init_mqtt_client(
            host=host, port=port, disable_tls=disable_tls, username=None, password=None
        )
    assert caplog.records[0].levelno == logging.INFO
    assert caplog.records[0].message == (
        "connecting to MQTT broker {}:{} (TLS {})".format(
            host, port, "disabled" if disable_tls else "enabled"
        )
    )
    if disable_tls:
        mqtt_client_class().tls_set.assert_not_called()
    else:
        mqtt_client_class().tls_set.assert_called_once_with(ca_certs=None)


@pytest.mark.parametrize("host", ["mqtt-broker.local"])
@pytest.mark.parametrize("port", [1833])
@pytest.mark.parametrize("username", ["me"])
@pytest.mark.parametrize("password", [None, "secret"])
def test__init_mqtt_client_authentication(host, port, username, password):
    with unittest.mock.patch("socket.create_connection"), unittest.mock.patch(
        "ssl.SSLContext.wrap_socket"
    ) as ssl_wrap_socket_mock:
        ssl_wrap_socket_mock.return_value.send = len
        mqtt_client = wireless_sensor_mqtt._init_mqtt_client(
            host=host,
            port=port,
            username=username,
            password=password,
            disable_tls=False,
        )
    assert mqtt_client._username.decode() == username
    if password:
        assert mqtt_client._password.decode() == password
    else:
        assert mqtt_client._password is None


@pytest.mark.parametrize("mqtt_host", ["mqtt-broker.local"])
@pytest.mark.parametrize("mqtt_port", [1833])
def test__init_mqtt_client_authentication_missing_username(mqtt_host, mqtt_port):
    with unittest.mock.patch("paho.mqtt.client.Client"):
        with pytest.raises(ValueError, match=r"^Missing MQTT username$"):
            wireless_sensor_mqtt._init_mqtt_client(
                host=mqtt_host,
                port=mqtt_port,
                disable_tls=False,
                username=None,
                password="secret",
            )


def test__mqtt_publish(caplog):
    client_mock = unittest.mock.MagicMock()
    msg_info_mock = unittest.mock.MagicMock()
    msg_info_mock.rc = paho.mqtt.client.MQTT_ERR_SUCCESS
    msg_info_mock.is_published.side_effect = [False, False, False, True, True]
    client_mock.publish.return_value = msg_info_mock
    with unittest.mock.patch("time.sleep") as sleep_mock, caplog.at_level(
        logging.DEBUG
    ):
        wireless_sensor_mqtt._mqtt_publish(
            client=client_mock, topic="/some/topic", payload="test", retain=False
        )
    client_mock.publish.assert_called_once_with(
        topic="/some/topic", payload="test", retain=False
    )
    assert sleep_mock.call_args_list == [unittest.mock.call(1)] * 3
    assert caplog.record_tuples == [
        (
            "wireless_sensor_mqtt",
            logging.DEBUG,
            "publishing mqtt msg: topic=/some/topic payload=test",
        )
    ]


def test__mqtt_publish_timeout(caplog):
    client_mock = unittest.mock.MagicMock()
    msg_info_mock = unittest.mock.MagicMock()
    msg_info_mock.rc = paho.mqtt.client.MQTT_ERR_SUCCESS  # default
    msg_info_mock.is_published.return_value = False
    client_mock.publish.return_value = msg_info_mock
    with unittest.mock.patch(
        "time.time", side_effect=itertools.count()
    ), unittest.mock.patch("time.sleep") as sleep_mock, caplog.at_level(logging.DEBUG):
        wireless_sensor_mqtt._mqtt_publish(
            client=client_mock, topic="/some/topic", payload="test", retain=False
        )
    client_mock.publish.assert_called_once_with(
        topic="/some/topic", payload="test", retain=False
    )
    assert sleep_mock.call_args_list == [unittest.mock.call(1)] * 15
    assert caplog.record_tuples == [
        (
            "wireless_sensor_mqtt",
            logging.DEBUG,
            "publishing mqtt msg: topic=/some/topic payload=test",
        ),
        (
            "wireless_sensor_mqtt",
            logging.WARNING,
            "reached timeout of 16 seconds while waiting for MQTT message on topic"
            " /some/topic to get published",
        ),
    ]


def test__mqtt_publish_fail(caplog):
    client_mock = unittest.mock.MagicMock()
    msg_info_mock = unittest.mock.MagicMock()
    msg_info_mock.rc = 42
    msg_info_mock.is_published.return_value = False
    client_mock.publish.return_value = msg_info_mock
    with unittest.mock.patch(
        "time.time", side_effect=itertools.count()
    ), unittest.mock.patch("time.sleep"), caplog.at_level(logging.ERROR):
        wireless_sensor_mqtt._mqtt_publish(
            client=client_mock, topic="/some/topic", payload="test", retain=False
        )
    assert caplog.record_tuples == [
        (
            "wireless_sensor_mqtt",
            logging.ERROR,
            "failed to publish on topic /some/topic (return code 42)",
        )
    ]
