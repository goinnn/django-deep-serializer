# -*- coding: utf-8 -*-
# Copyright (c) 2013 by Pablo Martín <goinnn@gmail.com>
#
# This software is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this software.  If not, see <http://www.gnu.org/licenses/>.

import sys

from django.conf import settings
from django.test import TestCase
from django.test.client import Client

from example.app.models import WebSite, Page
from example.app.utils import clone_website, serialize_website, deserialize_website

if sys.version_info[0] >= 2:
    string = str
else:
    string = basestring


class DeepSerializerTestCase(TestCase):

    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)

    def test_clone(self):
        websites = list(WebSite.objects.all())
        pages = list(Page.objects.all())
        website = WebSite.objects.get(pk=1)
        objs = clone_website(website)
        self.assertEqual(WebSite.objects.all().count(), len(websites) * 2)
        self.assertEqual(Page.objects.all().count(), len(pages) * 2)
        for new_obj in objs:
            if isinstance(new_obj, WebSite):
                self.assertEqual(new_obj.original_website, website)
            elif isinstance(new_obj, Page):
                self.assertEqual(new_obj.created_from in pages, True)
                pages.pop(pages.index(new_obj.created_from))
            else:
                self.assertRaises(ValueError)

    def test_restore(self, action='restore'):
        websites = list(WebSite.objects.all())
        pages = list(Page.objects.all())
        website = WebSite.objects.get(pk=1)
        fixtures = serialize_website(website, action=action)
        db_website = WebSite.objects.get(pk=1)
        db_website.title = 'New title'
        if action == 'restore':
            db_website.slug = 'new-title'
        db_website.save()
        objs = deserialize_website(website, fixtures, action=action)
        self.assertEqual(WebSite.objects.all().count(), len(websites))
        self.assertEqual(Page.objects.all().count(), len(pages))
        db_website = WebSite.objects.get(pk=1)
        self.assertEqual(objs[0].title, "My website")
        self.assertEqual(objs[0].slug, "my-website")
        self.assertEqual(db_website.title, "My website")
        self.assertEqual(db_website.slug, "my-website")

    def test_restore_without_internal_modules(self):
        serialization_modules = settings.SERIALIZATION_MODULES
        settings.SERIALIZATION_MODULES = {}
        self.test_restore()
        settings.SERIALIZATION_MODULES = serialization_modules

    def test_restore_natural_keys(self):
        self.test_restore(action='restore-natural-keys')

    def test_serialize_xml(self):
        website = WebSite.objects.get(pk=1)
        serialize_website(website, action='restore', format='xml')
