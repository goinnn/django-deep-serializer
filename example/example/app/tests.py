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

import json
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

    # Test type 1:

    def test_clone(self, format='json'):
        websites = list(WebSite.objects.all())
        pages = list(Page.objects.all())
        website = WebSite.objects.get(pk=1)
        objs = clone_website(website, format=format)
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

    def test_clone_xml(self):
        self.test_clone(format='xml')

    def test_clone_python(self):
        self.test_clone(format='python')

    def test_clone_yaml(self):
        self.test_clone(format='yaml')

    # Test type 2:

    def test_restore(self, action='restore', format='json'):
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

    def test_restore_xml(self):
        self.test_restore(action='restore', format='xml')

    def test_restore_python(self):
        self.test_restore(action='restore', format='python')

    def test_restore_yaml(self):
        self.test_restore(action='restore', format='yaml')

    # Test type 3:

    def test_restore_without_internal_modules(self, format='json'):
        serialization_modules = settings.SERIALIZATION_MODULES
        settings.SERIALIZATION_MODULES = {}
        self.test_restore(format=format)
        settings.SERIALIZATION_MODULES = serialization_modules

    def test_restore_without_internal_modules_xml(self):
        self.test_restore_without_internal_modules(format='xml')

    def test_restore_without_internal_modules_python(self):
        self.test_restore_without_internal_modules(format='python')

    def test_restore_without_internal_modules_yaml(self):
        self.test_restore_without_internal_modules(format='yaml')

    # Test type 4:

    def test_restore_natural_keys(self, format='json'):
        self.test_restore(action='restore-natural-keys')

    def test_restore_natural_keys_xml(self):
        self.test_restore(action='restore-natural-keys', format='xml')

    def test_restore_natural_keys_python(self):
        self.test_restore(action='restore-natural-keys', format='python')

    def test_restore_natural_keys_yaml(self):
        self.test_restore(action='restore-natural-keys', format='yaml')

    # Test type 5:

    def test_reorder_json_fixtures(self):
        fixtures = [{'fields': {'created_from': ['my-website', 'index'],
                                'html_code': '<p>Index of my website</p>',
                                'slug': 'index',
                                'title': 'Index',
                                'website': ['my-website-with-reorder']},
                     'model': 'app.page'},
                    {'fields': {'created_from': ['my-website', 'contact'],
                                'html_code': '<p>Contact form</p>',
                                'slug': 'contact',
                                'title': 'Contact',
                                'website': ['my-website-with-reorder']},
                     'model': 'app.page'},
                    {'fields': {'is_active': True,
                                'original_website': ['my-website'],
                                'owners': [['admin']],
                                'slug': 'my-website-with-reorder',
                                'title': 'My website with reorder'},
                     'model': 'app.website'}]
        deserialize_website(None, json.dumps(fixtures), action='clone')

    def test_reorder_xml_fixtures(self):
        fixtures = """<?xml version="1.0" encoding="utf-8"?>
        <django-objects version="1.0">
            <object model="app.page">
                <field type="CharField" name="title">Index</field>
                <field type="SlugField" name="slug">index</field>
                <field type="TextField" name="html_code">&lt;p&gt;Index of my website&lt;/p&gt;</field>
                <field to="app.website" name="website" rel="ManyToOneRel"><natural>my-website-with-reorder-xml</natural></field>
                <field to="app.page" name="created_from" rel="ManyToOneRel"><natural>my-website</natural><natural>index</natural></field>
                <field type="DateTimeField" name="creation_date"><None></None></field>
                <field type="DateTimeField" name="modification_date"><None></None></field>
            </object>
            <object model="app.page">
                <field type="CharField" name="title">Contact</field>
                <field type="SlugField" name="slug">contact</field>
                <field type="TextField" name="html_code">&lt;p&gt;Contact form&lt;/p&gt;</field>
                <field to="app.website" name="website" rel="ManyToOneRel"><natural>my-website-with-reorder-xml</natural></field>
                <field to="app.page" name="created_from" rel="ManyToOneRel"><natural>my-website</natural><natural>contact</natural></field>
                <field type="DateTimeField" name="creation_date"><None></None></field>
                <field type="DateTimeField" name="modification_date"><None></None></field>
            </object>
            <object model="app.website">
                <field type="CharField" name="title">My website with reorder XML</field>
                <field type="SlugField" name="slug">my-website-with-reorder-xml</field>
                <field type="BooleanField" name="is_active">True</field>
                <field to="app.website" name="original_website" rel="ManyToOneRel"><natural>my-website</natural></field>
                <field to="app.page" name="initial_page" rel="OneToOneRel"><None></None></field>
                <field type="DateTimeField" name="creation_date"><None></None></field>
                <field type="DateTimeField" name="modification_date"><None></None></field>
                <field to="auth.user" name="owners" rel="ManyToManyRel"><object><natural>admin</natural></object></field>
            </object>
        </django-objects>
        """
        deserialize_website(None, fixtures, action='clone', format='xml')

    def test_reorder_python_fixtures(self):
        fixtures = [{'fields': {'created_from': ['my-website', 'index'],
                                'html_code': '<p>Index of my website</p>',
                                'slug': 'index',
                                'title': 'Index',
                                'website': ['my-website-with-reorder-python']},
                     'model': 'app.page'},
                    {'fields': {'created_from': ['my-website', 'contact'],
                                'html_code': '<p>Contact form</p>',
                                'slug': 'contact',
                                'title': 'Contact',
                                'website': ['my-website-with-reorder-python']},
                     'model': 'app.page'},
                    {'fields': {'is_active': True,
                                'original_website': ['my-website'],
                                'owners': [['admin']],
                                'slug': 'my-website-with-reorder-python',
                                'title': 'My website with reorder python'},
                     'model': 'app.website'}]
        deserialize_website(None, fixtures, action='clone', format='python')

    def test_reorder_yaml_fixtures(self):
        if not "yaml" in settings.SERIALIZATION_MODULES:
            return
        fixtures = """
        -   fields:
                created_from: [my-website, index]
                creation_date: null
                html_code: <p>Index of my website</p>
                modification_date: null
                slug: index
                title: Index
                website: [my-website-with-reorder-yaml]
            model: app.page
        -   fields:
                created_from: [my-website, contact]
                creation_date: null
                html_code: <p>Contact form</p>
                modification_date: null
                slug: contact
                title: Contact
                website: [my-website-with-reorder-yaml]
            model: app.page
        -   fields:
                creation_date: null
                initial_page: null
                is_active: true
                modification_date: null
                original_website: [my-website]
                owners:
                - [admin]
                slug: my-website-with-reorder-yaml
                title: My website with reorder yaml
            model: app.website
        """
        deserialize_website(None, fixtures, action='clone', format='yaml')
