# Copyright 2014: Mirantis Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import mock

from rally.benchmark.context import secgroup
from tests.unit import fakes
from tests.unit import test


class SecGroupContextTestCase(test.TestCase):

    def setUp(self):
        super(SecGroupContextTestCase, self).setUp()
        self.users = 2
        task = mock.MagicMock()
        self.ctx_without_keys = {
            "admin": {"endpoint": "endpoint"},
            "users": [{"tenant_id": "uuid1",
                       "endpoint": mock.MagicMock()}] * self.users,
            "tenants": {"uuid1": {"id": "uuid1", "name": "uuid1"}},
            "task": task
        }

    @mock.patch('rally.benchmark.context.secgroup.osclients.Clients')
    def test_prep_ssh_sec_group(self, mock_osclients):
        fake_nova = fakes.FakeNovaClient()
        self.assertEqual(len(fake_nova.security_groups.list()), 1)
        mock_cl = mock.MagicMock()
        mock_cl.nova.return_value = fake_nova
        mock_osclients.return_value = mock_cl

        secgroup._prepare_open_secgroup('endpoint')

        self.assertEqual(len(fake_nova.security_groups.list()), 2)
        self.assertTrue(
            secgroup.SSH_GROUP_NAME in [
                sg.name for sg in fake_nova.security_groups.list()
            ])

        # run prep again, check that another security group is not created
        secgroup._prepare_open_secgroup('endpoint')
        self.assertEqual(len(fake_nova.security_groups.list()), 2)

    @mock.patch('rally.benchmark.context.secgroup.osclients.Clients')
    def test_prep_ssh_sec_group_rules(self, mock_osclients):
        fake_nova = fakes.FakeNovaClient()

        # NOTE(hughsaunders) Default security group is precreated
        self.assertEqual(len(fake_nova.security_groups.list()), 1)
        mock_cl = mock.MagicMock()
        mock_cl.nova.return_value = fake_nova
        mock_osclients.return_value = mock_cl

        secgroup._prepare_open_secgroup('endpoint')

        self.assertEqual(len(fake_nova.security_groups.list()), 2)
        rally_open = fake_nova.security_groups.find(secgroup.SSH_GROUP_NAME)
        self.assertEqual(len(rally_open.rules), 3)

        # run prep again, check that extra rules are not created
        secgroup._prepare_open_secgroup('endpoint')
        rally_open = fake_nova.security_groups.find(secgroup.SSH_GROUP_NAME)
        self.assertEqual(len(rally_open.rules), 3)

    @mock.patch("rally.benchmark.context.secgroup.osclients.Clients")
    @mock.patch("rally.benchmark.context.secgroup._prepare_open_secgroup")
    @mock.patch("rally.benchmark.wrappers.network.NetworkWrapper")
    @mock.patch("rally.benchmark.wrappers.network.wrap")
    @mock.patch("novaclient.v1_1.security_groups.SecurityGroup")
    def test_sec_group_setup_secgroup_supported(self,
                                                mock_security_group,
                                                mock_network_wrap,
                                                mock_network_wrapper,
                                                mock_prepare_open_secgroup,
                                                mock_osclients):
        mock_network_wrap.return_value = mock_network_wrapper
        mock_network_wrapper.supports_security_group.return_value = (
            True, "")
        mock_prepare_open_secgroup.return_value = mock_security_group
        mock_osclients.return_value = mock.MagicMock()

        secgrp_ctx = secgroup.AllowSSH(self.ctx_without_keys)
        secgrp_ctx.setup()
        self.assertEqual(len(secgrp_ctx.secgroup), 1)
        secgrp_ctx.cleanup()
        self.assertTrue(mock_security_group.delete.called)

    @mock.patch("rally.benchmark.context.secgroup.osclients.Clients")
    @mock.patch("rally.benchmark.wrappers.network.NetworkWrapper")
    @mock.patch("rally.benchmark.wrappers.network.wrap")
    def test_sec_group_setup_secgroup_unsupported(self,
                                                  mock_network_wrap,
                                                  mock_network_wrapper,
                                                  mock_osclients):
        mock_network_wrap.return_value = mock_network_wrapper
        mock_network_wrapper.supports_security_group.return_value = (
            False, "Not supported")
        mock_osclients.return_value = mock.MagicMock()

        secgrp_ctx = secgroup.AllowSSH(self.ctx_without_keys)
        secgrp_ctx.setup()
        self.assertEqual(len(secgrp_ctx.secgroup), 0)
