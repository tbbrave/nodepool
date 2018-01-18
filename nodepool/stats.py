#!/usr/bin/env python
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""
Helper to create a statsd client from environment variables
"""

import os
import logging
import statsd

from nodepool import zk

log = logging.getLogger("nodepool.stats")


def get_client():
    """Return a statsd client object setup from environment variables; or
    None if they are not set
    """

    # note we're just being careful to let the default values fall
    # through to StatsClient()
    statsd_args = {}
    if os.getenv('STATSD_HOST', None):
        statsd_args['host'] = os.environ['STATSD_HOST']
    if os.getenv('STATSD_PORT', None):
        statsd_args['port'] = os.environ['STATSD_PORT']
    if statsd_args:
        return statsd.StatsClient(**statsd_args)
    else:
        return None


class StatsReporter(object):
    '''
    Class adding statsd reporting functionality.
    '''
    def __init__(self):
        super(StatsReporter, self).__init__()
        self._statsd = get_client()

    def recordLaunchStats(self, subkey, dt, image_name,
                          provider_name, node_az, requestor):
        '''
        Record node launch statistics.

        :param str subkey: statsd key
        :param int dt: Time delta in milliseconds
        :param str image_name: Name of the image used
        :param str provider_name: Name of the provider
        :param str node_az: AZ of the launched node
        :param str requestor: Identifier for the request originator
        '''
        if not self._statsd:
            return

        keys = [
            'nodepool.launch.provider.%s.%s' % (provider_name, subkey),
            'nodepool.launch.image.%s.%s' % (image_name, subkey),
            'nodepool.launch.%s' % (subkey,),
        ]

        if node_az:
            keys.append('nodepool.launch.provider.%s.%s.%s' %
                        (provider_name, node_az, subkey))

        if requestor:
            # Replace '.' which is a graphite hierarchy, and ':' which is
            # a statsd delimeter.
            requestor = requestor.replace('.', '_')
            requestor = requestor.replace(':', '_')
            keys.append('nodepool.launch.requestor.%s.%s' %
                        (requestor, subkey))

        for key in keys:
            self._statsd.timing(key, dt)
            self._statsd.incr(key)

    def updateNodeStats(self, zk_conn, provider):
        '''
        Refresh statistics for all known nodes.

        :param ZooKeeper zk_conn: A ZooKeeper connection object.
        :param Provider provider: A config Provider object.
        '''
        if not self._statsd:
            return

        states = {}

        # Initialize things we know about to zero
        for state in zk.Node.VALID_STATES:
            key = 'nodepool.nodes.%s' % state
            states[key] = 0
            key = 'nodepool.provider.%s.nodes.%s' % (provider.name, state)
            states[key] = 0

        for node in zk_conn.nodeIterator():
            # nodepool.nodes.STATE
            key = 'nodepool.nodes.%s' % node.state
            states[key] += 1

            # nodepool.label.LABEL.nodes.STATE
            key = 'nodepool.label.%s.nodes.%s' % (node.type, node.state)
            # It's possible we could see node types that aren't in our config
            if key in states:
                states[key] += 1
            else:
                states[key] = 1

            # nodepool.provider.PROVIDER.nodes.STATE
            key = 'nodepool.provider.%s.nodes.%s' % (node.provider, node.state)
            # It's possible we could see providers that aren't in our config
            if key in states:
                states[key] += 1
            else:
                states[key] = 1

        for key, count in states.items():
            self._statsd.gauge(key, count)

        # nodepool.provider.PROVIDER.max_servers
        key = 'nodepool.provider.%s.max_servers' % provider.name
        max_servers = sum([p.max_servers for p in provider.pools.values()
                           if p.max_servers])
        self._statsd.gauge(key, max_servers)
