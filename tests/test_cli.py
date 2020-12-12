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
import typing
import unittest.mock

import pytest

import wireless_sensor_mqtt

# pylint: disable=protected-access


@pytest.mark.parametrize(
    (
        "argv",
        "expected_mqtt_host",
        "expected_mqtt_port",
        "expected_mqtt_disable_tls",
        "expected_username",
        "expected_password",
        "expected_topic_prefix",
    ),
    [
        (
            ["", "--mqtt-host", "mqtt-broker.local"],
            "mqtt-broker.local",
            8883,
            False,
            None,
            None,
            None,
        ),
        (
            ["", "--mqtt-host", "mqtt-broker.local", "--mqtt-disable-tls"],
            "mqtt-broker.local",
            1883,
            True,
            None,
            None,
            None,
        ),
        (
            ["", "--mqtt-host", "mqtt-broker.local", "--mqtt-port", "8883"],
            "mqtt-broker.local",
            8883,
            False,
            None,
            None,
            None,
        ),
        (
            ["", "--mqtt-host", "mqtt-broker.local", "--mqtt-port", "8884"],
            "mqtt-broker.local",
            8884,
            False,
            None,
            None,
            None,
        ),
        (
            [
                "",
                "--mqtt-host",
                "mqtt-broker.local",
                "--mqtt-port",
                "8884",
                "--mqtt-disable-tls",
            ],
            "mqtt-broker.local",
            8884,
            True,
            None,
            None,
            None,
        ),
        (
            ["", "--mqtt-host", "mqtt-broker.local", "--mqtt-username", "me"],
            "mqtt-broker.local",
            8883,
            False,
            "me",
            None,
            None,
        ),
        (
            [
                "",
                "--mqtt-host",
                "mqtt-broker.local",
                "--mqtt-username",
                "me",
                "--mqtt-password",
                "secret",
            ],
            "mqtt-broker.local",
            8883,
            False,
            "me",
            "secret",
            None,
        ),
        (
            [
                "",
                "--mqtt-host",
                "mqtt-broker.local",
                "--mqtt-topic-prefix",
                "system/command",
            ],
            "mqtt-broker.local",
            8883,
            False,
            None,
            None,
            "system/command",
        ),
    ],
)
def test__main(
    argv,
    expected_mqtt_host,
    expected_mqtt_port,
    expected_mqtt_disable_tls,
    expected_username,
    expected_password,
    expected_topic_prefix: typing.Optional[str],
):
    # pylint: disable=too-many-arguments
    with unittest.mock.patch(
        "wireless_sensor_mqtt._run"
    ) as run_mock, unittest.mock.patch("sys.argv", argv):
        # pylint: disable=protected-access
        wireless_sensor_mqtt._main()
    run_mock.assert_called_once_with(
        mqtt_host=expected_mqtt_host,
        mqtt_port=expected_mqtt_port,
        mqtt_disable_tls=expected_mqtt_disable_tls,
        mqtt_username=expected_username,
        mqtt_password=expected_password,
        mqtt_topic_prefix=expected_topic_prefix or "wireless-sensor/FT017TH",
        homeassistant_discovery_prefix="homeassistant",
        homeassistant_node_id="FT017TH",
        mock_measurements=False,
        unlock_spi_device=False,
    )


@pytest.mark.parametrize(
    ("password_file_content", "expected_password"),
    [
        ("secret", "secret"),
        ("secret space", "secret space"),
        ("secret   ", "secret   "),
        ("  secret ", "  secret "),
        ("secret\n", "secret"),
        ("secret\n\n", "secret\n"),
        ("secret\r\n", "secret"),
        ("secret\n\r\n", "secret\n"),
        ("你好\n", "你好"),
    ],
)
def test__main_password_file(tmpdir, password_file_content, expected_password):
    mqtt_password_path = tmpdir.join("mqtt-password")
    with mqtt_password_path.open("w") as mqtt_password_file:
        mqtt_password_file.write(password_file_content)
    with unittest.mock.patch(
        "wireless_sensor_mqtt._run"
    ) as run_mock, unittest.mock.patch(
        "sys.argv",
        [
            "",
            "--mqtt-host",
            "localhost",
            "--mqtt-username",
            "me",
            "--mqtt-password-file",
            str(mqtt_password_path),
        ],
    ):
        # pylint: disable=protected-access
        wireless_sensor_mqtt._main()
    run_mock.assert_called_once_with(
        mqtt_host="localhost",
        mqtt_port=8883,
        mqtt_disable_tls=False,
        mqtt_username="me",
        mqtt_password=expected_password,
        mqtt_topic_prefix="wireless-sensor/FT017TH",
        homeassistant_discovery_prefix="homeassistant",
        homeassistant_node_id="FT017TH",
        mock_measurements=False,
        unlock_spi_device=False,
    )


def test__main_password_file_collision(capsys):
    with unittest.mock.patch(
        "sys.argv",
        [
            "",
            "--mqtt-host",
            "localhost",
            "--mqtt-username",
            "me",
            "--mqtt-password",
            "secret",
            "--mqtt-password-file",
            "/var/lib/secrets/mqtt/password",
        ],
    ):
        with pytest.raises(SystemExit):
            # pylint: disable=protected-access
            wireless_sensor_mqtt._main()
    out, err = capsys.readouterr()
    assert not out
    assert (
        "argument --mqtt-password-file: not allowed with argument --mqtt-password\n"
        in err
    )


@pytest.mark.parametrize(
    ("args", "discovery_prefix"),
    [
        ([], "homeassistant"),
        (["--homeassistant-discovery-prefix", "home/assistant"], "home/assistant"),
    ],
)
def test__main_homeassistant_discovery_prefix(args, discovery_prefix):
    with unittest.mock.patch(
        "wireless_sensor_mqtt._run"
    ) as run_mock, unittest.mock.patch(
        "sys.argv", ["", "--mqtt-host", "mqtt-broker.local"] + args
    ):
        wireless_sensor_mqtt._main()
    assert run_mock.call_count == 1
    assert run_mock.call_args[1]["homeassistant_discovery_prefix"] == discovery_prefix


@pytest.mark.parametrize(
    ("args", "node_id"),
    [
        ([], "FT017TH"),
        (["--homeassistant-node-id", "ft017th-living-room"], "ft017th-living-room"),
    ],
)
def test__main_homeassistant_node_id(args, node_id):
    with unittest.mock.patch(
        "wireless_sensor_mqtt._run"
    ) as run_mock, unittest.mock.patch(
        "sys.argv", ["", "--mqtt-host", "mqtt-broker.local"] + args
    ):
        wireless_sensor_mqtt._main()
    assert run_mock.call_count == 1
    assert run_mock.call_args[1]["homeassistant_node_id"] == node_id


@pytest.mark.parametrize(
    "args", [["--homeassistant-node-id", "no pe"], ["--homeassistant-node-id", ""]]
)
def test__main_homeassistant_node_id_invalid(args):
    with unittest.mock.patch(
        "sys.argv", ["", "--mqtt-host", "mqtt-broker.local"] + args
    ):
        with pytest.raises(ValueError):
            wireless_sensor_mqtt._main()


@pytest.mark.parametrize(
    ("additional_argv", "root_log_level"),
    [([], logging.INFO), (["--debug"], logging.DEBUG)],
)
def test__main_log_level(additional_argv, root_log_level):
    with unittest.mock.patch("wireless_sensor_mqtt._run"), unittest.mock.patch(
        "logging.basicConfig"
    ) as logging_basic_config_mock, unittest.mock.patch(
        "sys.argv", ["", "--mqtt-host", "mqtt-broker.local"] + additional_argv
    ):
        wireless_sensor_mqtt._main()
    assert logging_basic_config_mock.call_count == 1
    assert logging_basic_config_mock.call_args[1]["level"] == root_log_level
    assert logging.getLogger("cc1101").getEffectiveLevel() == logging.INFO


@pytest.mark.parametrize(
    ("additional_argv", "log_level"),
    [([], logging.INFO), (["--debug-cc1101"], logging.DEBUG)],
)
def test__main_log_level_cc1101(additional_argv, log_level):
    with unittest.mock.patch("wireless_sensor_mqtt._run"), unittest.mock.patch(
        "logging.basicConfig"
    ) as logging_basic_config_mock, unittest.mock.patch(
        "sys.argv", ["", "--mqtt-host", "mqtt-broker.local"] + additional_argv
    ):
        wireless_sensor_mqtt._main()
    assert logging_basic_config_mock.call_count == 1
    assert logging_basic_config_mock.call_args[1]["level"] == logging.INFO
    assert logging.getLogger("cc1101").getEffectiveLevel() == log_level


@pytest.mark.parametrize(
    ("additional_argv", "mock_measurements"),
    [([], False), (["--mock-measurements"], True)],
)
def test__main_mock_measurements(additional_argv, mock_measurements):
    with unittest.mock.patch(
        "wireless_sensor_mqtt._run"
    ) as main_mock, unittest.mock.patch(
        "sys.argv", ["", "--mqtt-host", "mqtt-broker.local"] + additional_argv
    ):
        wireless_sensor_mqtt._main()
    assert main_mock.call_args[1]["mock_measurements"] == mock_measurements


@pytest.mark.parametrize(
    ("additional_argv", "unlock_spi_device"),
    [([], False), (["--unlock-spi-device"], True)],
)
def test__main_unlock_spi_device(additional_argv, unlock_spi_device):
    with unittest.mock.patch(
        "wireless_sensor_mqtt._run"
    ) as main_mock, unittest.mock.patch(
        "sys.argv", ["", "--mqtt-host", "mqtt-broker.local"] + additional_argv
    ):
        wireless_sensor_mqtt._main()
    assert main_mock.call_args[1]["unlock_spi_device"] == unlock_spi_device
