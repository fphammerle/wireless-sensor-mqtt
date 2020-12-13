# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Added
- option `--debug-cc1101`
- log MQTT messages before publishing (debug level)

### Fixed
- replace occasionally infinitely blocking `paho.mqtt.client.MQTTMessageInfo.wait_for_publish()`
  to set timeout when waiting for MQTT message to get published

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

[Unreleased]: https://github.com/fphammerle/wireless-sensor-mqtt/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/fphammerle/wireless-sensor-mqtt/compare/v0.2.0...v0.2.0
[0.1.1]: https://github.com/fphammerle/wireless-sensor-mqtt/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/fphammerle/wireless-sensor-mqtt/releases/tag/v0.1.0
