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

import datetime
import uuid
import time

from deep_serializer import BaseMetaWalkClass, WALKING_STOP, WALKING_INTO_CLASS, ONLY_REFERENCE


def hash_slug():
    return ''.join(str(uuid.uuid4()).split('-'))


class MyMetaWalkClass(BaseMetaWalkClass):

    @classmethod
    def pre_serialize(cls, initial_obj, obj, request, options=None):
        obj = super(MyMetaWalkClass, cls).pre_serialize(initial_obj, obj, request, options=options)
        obj.creation_date = None
        obj.modification_date = None
        return obj

    @classmethod
    def pretreatment_fixture(cls, initial_obj, obj):
        obj = super(MyMetaWalkClass, cls).pretreatment_fixture(initial_obj, obj)
        obj['fields']['creation_date'] = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
        obj['fields']['modification_date'] = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
        return obj


class BaseWebSiteWalkClass(MyMetaWalkClass):

    @classmethod
    def pre_serialize(cls, initial_obj, obj, request, options=None):
        obj = super(BaseWebSiteWalkClass, cls).pre_serialize(initial_obj, obj, request, options=options)
        return obj


class WebSiteClone(MyMetaWalkClass):

    @classmethod
    def pre_serialize(cls, initial_obj, obj, request, options=None):
        obj = super(WebSiteClone, cls).pre_serialize(initial_obj, obj, request, options=options)
        new_title = '%s-%s' % (obj.title, time.time())
        obj.title = new_title[:200]
        obj.slug = hash_slug()
        obj.original_website_id = obj.pk
        obj.initial_page = None
        return obj

    @classmethod
    def walking_into_class(cls, obj, field_name, model):
        if field_name in ('initial_page', 'websites_created_of'):
            return WALKING_STOP
        elif field_name in ('original_website', 'owners'):
            return ONLY_REFERENCE
        return WALKING_INTO_CLASS


class PageClone(MyMetaWalkClass):

    @classmethod
    def pre_serialize(cls, initial_obj, obj, request, options=None):
        obj = super(PageClone, cls).pre_serialize(initial_obj, obj, request, options=options)
        obj.website = initial_obj
        obj.created_from_id = obj.pk
        return obj

    @classmethod
    def walking_into_class(cls, obj, field_name, model):
        if field_name in ('pages_created_of', 'website'):
            return WALKING_STOP
        elif field_name in ('created_from'):
            return ONLY_REFERENCE
        return WALKING_INTO_CLASS

    @classmethod
    def post_save(cls, initial_obj, obj):
        super(PageClone, cls).post_save(initial_obj, obj)
        initial_page = obj.created_from.website.initial_page
        if initial_page and obj.slug == initial_page.slug:
            obj.website.initial_page = obj
            obj.website.save()


class WebSiteRestore(MyMetaWalkClass):

    @classmethod
    def walking_into_class(cls, obj, field_name, model):
        if field_name in ('websites_created_of'):
            return WALKING_STOP
        elif field_name in ('initial_page', 'original_website', 'owners'):
            return ONLY_REFERENCE
        return WALKING_INTO_CLASS


class PageRestore(MyMetaWalkClass):

    @classmethod
    def walking_into_class(cls, obj, field_name, model):
        if field_name in ('pages_created_of'):
            return WALKING_STOP
        elif field_name in ('created_from', 'website'):
            return ONLY_REFERENCE
        return WALKING_INTO_CLASS
