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

import re

# https://www.home-assistant.io/docs/mqtt/discovery/#configuration-variables
NODE_ID_ALLOWED_CHARS = r"a-zA-Z0-9_-"


def validate_node_id(node_id: str) -> bool:
    return re.match(r"^[{}]+$".format(NODE_ID_ALLOWED_CHARS), node_id) is not None
