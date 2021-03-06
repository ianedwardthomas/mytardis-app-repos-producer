# -*- coding: utf-8 -*-
#
# Copyright (c) 2012, RMIT eResearch Office
#   (RMIT University, Australia)
# Copyright (c) 2010-2012, Monash e-Research Centre
#   (Monash University, Australia)
# Copyright (c) 2010-2011, VeRSI Consortium
#   (Victorian eResearch Strategic Initiative, Australia)
# All rights reserved.
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#    *  Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#    *  Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#    *  Neither the name of the VeRSI, the VeRSI Consortium members, nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE REGENTS AND CONTRIBUTORS ``AS IS'' AND ANY
# EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE REGENTS AND CONTRIBUTORS BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#

import logging
logger = logging.getLogger(__name__)

from django.contrib.auth.models import User
from django.test import TestCase
from django.test.client import Client

from lxml import etree

from tardis.tardis_portal.models import \
    Experiment, ExperimentACL, License, UserProfile


def _create_test_data():
    """
    Create Single experiment with two owners
    """
    user1 = User(username='tom',
                first_name='Thomas',
                last_name='Atkins',
                email='tommy@atkins.net')
    user1.save()
    UserProfile(user=user1).save()

    user2 = User(username='joe',
                first_name='Joe',
                last_name='Bloggs',
                email='joe@mail.com')
    user2.save()
    UserProfile(user=user2).save()

    license_ = License(name='Creative Commons Attribution-NoDerivs 2.5 Australia',
                       url='http://creativecommons.org/licenses/by-nd/2.5/au/',
                       internal_description='CC BY 2.5 AU',
                       allows_distribution=True)
    license_.save()
    experiment = Experiment(title='Norwegian Blue',
                            description='Parrot + 40kV',
                            created_by=user1)
    experiment.public_access = Experiment.PUBLIC_ACCESS_FULL
    experiment.license = license_
    experiment.save()
    experiment.author_experiment_set.create(order=0,
                                            author="John Cleese",
                                            url="http://nla.gov.au/nla.party-1")
    experiment.author_experiment_set.create(order=1,
                                            author="Michael Palin",
                                            url="http://nla.gov.au/nla.party-2")

    acl1 = ExperimentACL(experiment=experiment,
                    pluginId='django_user',
                    entityId=str(user1.id),
                    isOwner=True,
                    canRead=True,
                    canWrite=True,
                    canDelete=True,
                    aclOwnershipType=ExperimentACL.OWNER_OWNED)
    acl1.save()

    acl2 = ExperimentACL(experiment=experiment,
                    pluginId='django_user',
                    entityId=str(user2.id),
                    isOwner=True,
                    canRead=True,
                    canWrite=True,
                    canDelete=True,
                    aclOwnershipType=ExperimentACL.OWNER_OWNED)
    acl2.save()
    return experiment


class DCEndPointTest(TestCase):

    def setUp(self):
        self._client = Client()
        self.ns = {'r': 'http://ands.org.au/standards/rif-cs/registryObjects',
                   'o': 'http://www.openarchives.org/OAI/2.0/',
                   'd': 'http://purl.org/dc/elements/1.1/'}

    def testListRecords(self):
        """
        Can we retieve a single experiment as dc with additional
        ident and creator fields
        """
        ns = self.ns
        experiment = _create_test_data()
        args = {
            'verb': 'ListRecords',
            'metadataPrefix': 'oai_dc'
        }
        response = self._client_get('/apps/oaipmh/?%s' %
                                        '&'.join('%s=%s' % (k, v)
                                                 for k, v in args.items()))
        self.assertEqual(response.status_code, 200)
        xml = etree.fromstring(response.content)
        print response.content
        assert xml.xpath('/o:OAI-PMH', namespaces=ns)
        assert not xml.xpath('o:error', namespaces=ns)
        idents = xml.xpath('/o:OAI-PMH/o:ListRecords' +
                           '/o:record/o:header/o:identifier',
                           namespaces=ns)
        self.assertEqual(len(idents), 1)
        self.assertTrue('experiment/%d' % experiment.id in
            [i.text for i in idents])
        metadata_xpath = '/o:OAI-PMH/o:ListRecords/o:record/o:metadata'
        metadata = xml.xpath(metadata_xpath, namespaces=ns)
        assert len(metadata) == 1

        # only checks additional fields beyond normal dc
        ident = xml.xpath(metadata_xpath +
                                     '//d:identifier[1]',
                                     namespaces=ns)
        ident_to_check = [x.text for x in ident]
        self.assertEqual(ident_to_check[0], "1")

        creator = xml.xpath(metadata_xpath +
                                     '//d:creator',
                                     namespaces=ns)
        print "creator=%s" % creator
        creator_to_check = sorted([x.text for x in creator])
        self.assertEqual(creator_to_check, ['1'])

        #import nose.tools
        #nose.tools.set_trace()

    def _client_get(self, url, **kwargs):
        return self._client.get(url, kwargs)
