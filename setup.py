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

import pathlib

import setuptools

_REPO_URL = "https://github.com/fphammerle/wireless-sensor-mqtt"

setuptools.setup(
    name="wireless-sensor-mqtt",
    use_scm_version={
        "git_describe_command": "git describe --dirty --tags --long --match v*"
    },
    packages=setuptools.find_packages(),
    description="MQTT client reporting measurements of FT017TH wireless thermo/hygrometers",
    long_description=pathlib.Path(__file__).parent.joinpath("README.md").read_text(),
    long_description_content_type="text/markdown",
    author="Fabian Peter Hammerle",
    author_email="fabian@hammerle.me",
    url=_REPO_URL,
    project_urls={"Changelog": _REPO_URL + "/blob/master/CHANGELOG.md"},
    license="GPLv3+",
    keywords=[
        "FT017TH",
        "IoT",
        "automation",
        "climate",
        "home-assistant",
        "home-automation",
        "humidity",
        "hygrometer",
        "mqtt",
        "raspberry-pi",
        "sensor",
        "thermometer",
        "wireless",
    ],
    classifiers=[
        # https://pypi.org/classifiers/
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: End Users/Desktop",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Operating System :: POSIX :: Linux",
        # .github/workflows/python.yml
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Topic :: Home Automation",
        "Topic :: Utilities",
    ],
    entry_points={
        "console_scripts": ["wireless-sensor-mqtt = wireless_sensor_mqtt:_main"]
    },
    install_requires=[
        "wireless-sensor>=0.3.0,<0.4",  # >=0.3.0 for FT017TH(unlock_spi_device=True)
        "paho-mqtt<2",
    ],
    setup_requires=["setuptools_scm"],
    tests_require=["pytest"],
)
