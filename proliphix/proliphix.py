# -*- coding: utf-8 -*-
#
# Copyright 2016 Sean Dague
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Proliphix Network Thermostat

The Proliphix NT10e Thermostat is an ethernet connected thermostat. It
has a local HTTP interface that is based on get/set of OID values. A
complete collection of the API is available in this API doc:

https://github.com/sdague/thermostat.rb/blob/master/docs/PDP_API_R1_11.pdf
"""

import logging
import requests
from urllib.parse import urlencode

logger = logging.getLogger(__name__)


# The subset of oids which are useful for home-assistant, this might
# be expanded over time.
OIDS = {
    '1.2': 'DevName',
    '4.1.13': 'AverageTemp',
    '4.1.4': 'FanState',
    '4.1.5': 'SetbackHeat',
    '4.1.6': 'SetbackCool',
    '4.1.2': 'HvacState',
    '4.1.11': 'CurrentClass',
    '4.5.1': 'Heat1Usage',
    '4.5.3': 'Cool1Usage',
    '4.5.5': 'FanUsage',
    '4.5.6': 'LastUsageReset'
}


def _get_oid(name):
    """Get OID by name/value."""
    for oid, value in OIDS.items():
        if value == name:
            return oid
    return None


def _all_oids():
    """Build a query string for all the OIDS we have."""
    return "&".join([("OID" + x + "=") for x in OIDS.keys()])


class PDP(object):
    """PDP class for interacting with Proliphix thermostat.

    OID states come back largely as enumerations, temp values come
    back as an int which is in decidegrees.

    The manual says don't make API calls more than once a minute for
    prolonged periods of time, so we only refresh the data on update,
    then fetch everything out of the cached data when needed.

    """
    def __init__(self, host, user, passwd):
        self._host = host
        self._user = user
        self._passwd = passwd
        self._data = {}

    def update(self):
        url = "http://%s/get" % self._host
        data = _all_oids()
        r = requests.post(url, auth=(self._user, self._passwd), data=data)
        for line in r.text.split('&'):
            if line:
                oid, value = line.split('=')
                const = OIDS.get(oid[3:])
                if const:
                    self._data[const] = value
        logger.debug("PDP collected data %s" % self._data)

    def _set(self, **kwargs):
        data = {}
        for key, value in kwargs.items():
            oid = _get_oid(key)
            if oid:
                data["OID%s" % oid] = value
        url = "http://%s/pdp" % self._host
        form_data = urlencode(data)
        form_data += "&submit=Submit"
        requests.post(url, auth=(self._user, self._passwd), data=form_data)

    @property
    def cur_temp(self):
        return float(self._data['AverageTemp']) / 10

    @property
    def setback_heat(self):
        return float(self._data['SetbackHeat']) / 10

    @setback_heat.setter
    def setback_heat(self, val):
        self._data['SetbackHeat'] = int(val * 10)
        self._set(SetbackHeat=self._data['SetbackHeat'])

    @property
    def hvac_state(self):
        return int(self._data['HvacState'])

    @property
    def name(self):
        return self._data['DevName']

    @property
    def fan_state(self):
        if self._data['FanState'] == "2":
            return "On"
        else:
            return "Off"
