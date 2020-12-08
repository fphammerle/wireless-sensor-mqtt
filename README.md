# wireless-sensor-mqtt 🌡

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![CI Pipeline Status](https://github.com/fphammerle/wireless-sensor-mqtt/workflows/tests/badge.svg)](https://github.com/fphammerle/wireless-sensor-mqtt/actions)
[![Coverage Status](https://coveralls.io/repos/github/fphammerle/wireless-sensor-mqtt/badge.svg?branch=master)](https://coveralls.io/github/fphammerle/wireless-sensor-mqtt?branch=master)
[![Last Release](https://img.shields.io/pypi/v/wireless-sensor-mqtt.svg)](https://pypi.org/project/wireless-sensor-mqtt/#history)
[![Compatible Python Versions](https://img.shields.io/pypi/pyversions/wireless-sensor-mqtt.svg)](https://pypi.org/project/wireless-sensor-mqtt/)
[![DOI](https://zenodo.org/badge/319636053.svg)](https://zenodo.org/badge/latestdoi/319636053)

MQTT client reporting measurements of FT017TH wireless thermo/hygrometers

## Requirements

* MQTT broker
* [FT017TH](https://github.com/fphammerle/FT017TH-wireless-thermometer-hygrometer-signal#product-details) sensor
* [CC1101 transceiver](https://www.ti.com/product/CC1101)
* Linux machine with CC1101 connected to SPI port
  ([wiring instructions](https://github.com/fphammerle/python-cc1101#wiring-raspberry-pi)
  for raspberry pi)

## Setup

```sh
$ pip3 install --user --upgrade wireless-sensor-mqtt
```

## Usage

```sh
$ wireless-sensor-mqtt --mqtt-host HOSTNAME_OR_IP_ADDRESS \
    --mqtt-topic-prefix MQTT_TOPIC_PREFIX
```

Measurements will be published on topics
`MQTT_TOPIC_PREFIX/temperature-degrees-celsius`
and `MQTT_TOPIC_PREFIX/relative-humidity-percent`
(e.g., `living-room/temperature-degrees-celsius`
with `--mqtt-topic-prefix living-room`).

Add `--debug` to get debug logs.

### MQTT via TLS

TLS is enabled by default.
Run `wireless-sensor-mqtt --mqtt-disable-tls …` to disable TLS.

### MQTT Authentication

```sh
wireless-sensor-mqtt --mqtt-username me --mqtt-password secret …
# or
wireless-sensor-mqtt --mqtt-username me --mqtt-password-file /var/lib/secrets/mqtt/password …
```

## Home Assistant 🏡

[Home Assistant](https://www.home-assistant.io/) will detect two new sensors automatically,
if connected to the same MQTT broker
and [MQTT discovery](https://www.home-assistant.io/docs/mqtt/discovery/) is enabled
(enabled by default since version [0.117.0](https://github.com/home-assistant/core/commit/306ee305747a4f7ba758352503f99f221f0ad85a)).

![homeassistant: discovered sensors](docs/homeassistant/developer-tools-states-v0.117.5-20201208.png)

When using a custom `discovery_prefix`, run `wireless-sensor-mqtt --homeassistant-discovery-prefix custom-prefix …`.

## Docker 🐳

Pre-built docker images are available at https://hub.docker.com/r/fphammerle/wireless-sensor-mqtt/tags

```sh
$ sudo docker run --name wireless_sensor_mqtt \
    --device /dev/spidev0.0 fphammerle/wireless-sensor-mqtt \
    wireless-sensor-mqtt --mqtt-host HOSTNAME_OR_IP_ADDRESS …
```

Optionally add `--read-only --cap-drop ALL --security-opt no-new-privileges` before image specifier.

Annotation of signed tags `docker/*` contains docker image digests: https://github.com/fphammerle/wireless-sensor-mqtt/tags

### Docker Compose 🐙

1. Clone this repository.
2. Edit `docker-compose.yml`.
3. `sudo docker-compose up --build`
