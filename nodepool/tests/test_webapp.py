# Copyright (C) 2014 OpenStack Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import logging
import yaml
from six.moves.urllib import request

from nodepool import tests


class TestWebApp(tests.DBTestCase):
    log = logging.getLogger("nodepool.TestWebApp")

    def test_image_list(self):
        configfile = self.setup_config('node.yaml')
        pool = self.useNodepool(configfile, watermark_sleep=1)
        self.useBuilder(configfile)
        pool.start()
        webapp = self.useWebApp(pool, port=0)
        webapp.start()
        port = webapp.server.socket.getsockname()[1]

        self.waitForImage('fake-provider', 'fake-image')
        self.waitForNodes('fake-label')

        req = request.Request(
            "http://localhost:%s/image-list" % port)
        f = request.urlopen(req)
        self.assertEqual(f.info().get('Content-Type'),
                         'text/plain; charset=UTF-8')
        data = f.read()
        self.assertTrue('fake-image' in data.decode('utf8'))

    def test_dib_image_list_json(self):
        configfile = self.setup_config('node.yaml')
        pool = self.useNodepool(configfile, watermark_sleep=1)
        self.useBuilder(configfile)
        pool.start()
        webapp = self.useWebApp(pool, port=0)
        webapp.start()
        port = webapp.server.socket.getsockname()[1]

        self.waitForImage('fake-provider', 'fake-image')
        self.waitForNodes('fake-label')

        req = request.Request(
            "http://localhost:%s/dib-image-list.json" % port)
        f = request.urlopen(req)
        self.assertEqual(f.info().get('Content-Type'),
                         'application/json')
        data = f.read()
        objs = json.loads(data.decode('utf8'))
        # make sure this is valid json and has some of the
        # non-changing keys
        self.assertDictContainsSubset({'id': 'fake-image-0000000001',
                                       'formats': ['qcow2'],
                                       'state': 'ready'}, objs[0])

    def test_webapp_config(self):
        configfile = self.setup_config('webapp.yaml')
        config = yaml.safe_load(open(configfile))
        self.assertEqual(config['webapp']['port'], 8080)
        self.assertEqual(config['webapp']['listen_address'], '127.0.0.1')
