# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2024-11-22
### Added
- declare compatibility with `python3.11`

### Changed
- migrate from [paho-mqtt](https://github.com/eclipse-paho/paho.mqtt.python)
  to its async wrapper [aiomqtt](https://github.com/empicano/aiomqtt)
- require `wireless-sensor` ≥v1.0.0 to fix frequent losses of mqtt connection
  ("aiomqtt.exceptions.MqttError: Operation timed out"
  / "RuntimeError: Message publish failed: The connection was lost.")
- quit after one hour without valid packet
- container image: upgrade alpine base image from 3.19 to 3.20
- container image: upgrade python from 3.10 to 3.11

### Removed
- compatibility with `python3.8`

## [0.4.0] - 2024-08-12
### Added
- dockerfile: support build without git history
  (by manually setting build argument `SETUPTOOLS_SCM_PRETEND_VERSION`)

### Changed
- detect arrival of new package via edge on CC1101's `GDO0` pin (instead of polling),
  adding new required command-line parameter `--gdo0-gpio-line-name`

### Removed
- compatibility with `python3.5`, `python3.6` & `python3.7`

### Fixed
- dockerfile: pin alpine version to improve reproducibility of image build
- dockerfile: `chmod` files copied from host to no longer require `o=rX` perms on host
- dockerfile: add registry to base image specifier for `podman build`
- dockerfile: add `--force` flag to `rm` invocation to avoid interactive questions while running `podman build`

## [0.3.0] - 2020-12-13
### Added
- option `--debug-cc1101`
- log MQTT messages before publishing (debug level)

### Fixed
- replace occasionally infinitely blocking `paho.mqtt.client.MQTTMessageInfo.wait_for_publish()`
  to set timeout when waiting for MQTT message to get published
- attempt to reconnect to MQTT broker after losing connection

## [0.2.0] - 2020-12-11
### Changed
- upgrade `wireless-sensor` library to acquire `flock` on SPI device file

### Added
- option `--unlock-spi-device` to release the `flock` from the SPI device file
  after configuring the transceiver

## [0.1.1] - 2020-12-08
### Fixed
- syntax errors on python3.5

## [0.1.0] - 2020-12-08
### Added
- MQTT client reporting measurements of FT017TH wireless thermo/hygrometers

[Unreleased]: https://github.com/fphammerle/wireless-sensor-mqtt/compare/v0.5.0...HEAD
[0.3.0]: https://github.com/fphammerle/wireless-sensor-mqtt/compare/v0.4.0...v0.5.0
[0.3.0]: https://github.com/fphammerle/wireless-sensor-mqtt/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/fphammerle/wireless-sensor-mqtt/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/fphammerle/wireless-sensor-mqtt/compare/v0.2.0...v0.2.0
[0.1.1]: https://github.com/fphammerle/wireless-sensor-mqtt/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/fphammerle/wireless-sensor-mqtt/releases/tag/v0.1.0
