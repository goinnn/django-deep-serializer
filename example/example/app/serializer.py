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

from django.utils.timezone import utc

from deep_serializer import (BaseMetaWalkClass, WALKING_STOP,
                             ONLY_REFERENCE)


class MyMetaWalkClass(BaseMetaWalkClass):

    @classmethod
    def pre_serialize(cls, initial_obj, obj, request=None, serialize_options=None):
        obj = super(MyMetaWalkClass, cls).pre_serialize(initial_obj, obj,
                                                        request,
                                                        serialize_options=serialize_options)
        obj.creation_date = None
        obj.modification_date = None
        return obj

    @classmethod
    def pre_save(cls, initial_obj, obj, request=None):
        super(MyMetaWalkClass, cls).pre_save(initial_obj, obj, request=request)
        now = datetime.datetime.utcnow().replace(tzinfo=utc)
        if not obj.creation_date:
            obj.creation_date = now
        if not obj.modification_date:
            obj.modification_date = now

## Example 1: Clone an WebSite


def get_hash():
    return ''.join(str(uuid.uuid4()).split('-'))


class WebSiteClone(MyMetaWalkClass):

    @classmethod
    def pre_serialize(cls, initial_obj, obj, request, serialize_options=None):
        obj = super(WebSiteClone, cls).pre_serialize(initial_obj, obj,
                                                     request,
                                                     serialize_options=serialize_options)
        new_title = '%s-%s' % (obj.title, time.time())
        obj.title = new_title[:200]
        obj.slug = get_hash()
        obj.original_website_id = obj.pk
        obj.initial_page = None
        return obj

    @classmethod
    def walking_into_class(cls, initial_obj, obj, field_name, model, request=None):
        if field_name in ('initial_page', 'websites_created_of'):
            return WALKING_STOP
        elif field_name in ('original_website', 'owners'):
            return ONLY_REFERENCE
        return super(WebSiteClone, cls).walking_into_class(
            initial_obj, obj, field_name, model, request=request)


class PageClone(MyMetaWalkClass):

    @classmethod
    def pre_serialize(cls, initial_obj, obj, request, serialize_options=None):
        obj = super(PageClone, cls).pre_serialize(initial_obj,
                                                  obj, request,
                                                  serialize_options=serialize_options)
        obj.website = initial_obj
        obj.created_from_id = obj.pk
        return obj

    @classmethod
    def walking_into_class(cls, initial_obj, obj, field_name, model, request=None):
        if field_name in ('pages_created_of', 'website'):
            return WALKING_STOP
        elif field_name in ('created_from', 'last_editor'):
            return ONLY_REFERENCE
        return super(PageClone, cls).walking_into_class(
            initial_obj, obj, field_name, model, request=request)

    @classmethod
    def post_save(cls, initial_obj, obj, request=None):
        super(PageClone, cls).post_save(initial_obj, obj, request=request)
        initial_page = obj.created_from.website.initial_page
        if initial_page and obj.slug == initial_page.slug:
            obj.website.initial_page = obj
            obj.website.save()

## End example 1


## Example 2: Clone an WebSite and also clone the owners


class WebSiteOwnersClone(WebSiteClone):

    @classmethod
    def walking_into_class(cls, initial_obj, obj, field_name, model, request=None):
        if field_name in ('initial_page', 'websites_created_of'):
            return WALKING_STOP
        elif field_name in ('original_website'):
            return ONLY_REFERENCE
        return super(WebSiteOwnersClone, cls).walking_into_class(
            initial_obj, obj, field_name, model, request=request)

    @classmethod
    def pre_serialize(cls, initial_obj, obj, request, serialize_options=None):
        obj = super(WebSiteOwnersClone, cls).pre_serialize(initial_obj,
                                                           obj, request,
                                                           serialize_options=serialize_options)
        obj.owners = []
        return obj


class PageOwnersClone(PageClone):

    @classmethod
    def walking_into_class(cls, initial_obj, obj, field_name, model, request=None):
        if field_name in ('pages_created_of', 'website'):
            return WALKING_STOP
        elif field_name in ('created_from'):
            return ONLY_REFERENCE
        return super(PageClone, cls).walking_into_class(
            initial_obj, obj, field_name, model, request=request)


class UserClone(BaseMetaWalkClass):

    @classmethod
    def pre_serialize(cls, initial_obj, obj, request, serialize_options=None):
        obj = super(UserClone, cls).pre_serialize(initial_obj, obj,
                                                  request,
                                                  serialize_options=serialize_options)
        obj.date_joined = None
        obj.last_login = None
        obj.username = get_hash()
        obj.email = 'xxx@example.com'
        return obj

    @classmethod
    def pre_save(cls, initial_obj, obj, request=None):
        super(UserClone, cls).pre_save(initial_obj, obj, request=request)
        now = datetime.datetime.utcnow().replace(tzinfo=utc)
        if obj.date_joined is None:
            obj.date_joined = now
        if obj.last_login is None:
            obj.last_login = now

    @classmethod
    def post_save(cls, initial_obj, obj, request=None):
        super(UserClone, cls).post_save(initial_obj, obj, request=request)
        db_website = initial_obj.__class__.objects.get(slug=initial_obj.slug)
        db_website.owners.add(obj)


## End example 2


## Example 3: Restore a website using primary keys


class WebSiteRestore(MyMetaWalkClass):

    @classmethod
    def walking_into_class(cls, initial_obj, obj, field_name, model, request=None):
        if field_name in ('websites_created_of'):
            return WALKING_STOP
        elif field_name in ('initial_page', 'original_website', 'owners'):
            return ONLY_REFERENCE
        return super(WebSiteRestore, cls).walking_into_class(
            initial_obj, obj, field_name, model, request=request)


class PageRestore(MyMetaWalkClass):

    @classmethod
    def walking_into_class(cls, initial_obj, obj, field_name, model, request=None):
        if field_name in ('pages_created_of'):
            return WALKING_STOP
        elif field_name in ('created_from', 'website'):
            return ONLY_REFERENCE
        return super(PageRestore, cls).walking_into_class(
            initial_obj, obj, field_name, model, request=request)


## End example 3

## Example 4: Restore a website using natural keys


class WebSiteRestoreNaturalKey(MyMetaWalkClass):

    @classmethod
    def pre_serialize(cls, initial_obj, obj, request, serialize_options=None):
        obj = super(WebSiteRestoreNaturalKey, cls).pre_serialize(
            initial_obj, obj, request, serialize_options=serialize_options)
        obj.initial_page_bc = obj.initial_page
        obj.initial_page = None
        return obj

    @classmethod
    def walking_into_class(cls, initial_obj, obj, field_name, model, request=None):
        if field_name in ('websites_created_of'):
            return WALKING_STOP
        if field_name in ('initial_page', 'original_website', 'owners'):
            return ONLY_REFERENCE
        return super(WebSiteRestoreNaturalKey, cls).walking_into_class(
            initial_obj, obj, field_name, model, request)


class PageRestoreNaturalKey(MyMetaWalkClass):

    @classmethod
    def walking_into_class(cls, initial_obj, obj, field_name, model, request=None):
        if field_name in ('pages_created_of', 'created_from', 'website'):
            return ONLY_REFERENCE
        return super(PageRestoreNaturalKey, cls).walking_into_class(
            initial_obj, obj, field_name, model, request)

    @classmethod
    def post_save(cls, initial_obj, obj, request=None):
        super(PageRestoreNaturalKey, cls).post_save(initial_obj, obj, request=request)
        initial_page = initial_obj.initial_page_bc
        if initial_page and obj.slug == initial_page.slug:
            obj.website.initial_page = obj
            obj.website.save()

## End example 4

## Example 4: Clone filtering objects


class PageCloneFiltering(PageClone):

    @classmethod
    def pretreatment_fixture(cls, initial_obj, obj_fix, request=None, deserialize_options=None):
        if isinstance(obj_fix, dict):
            if obj_fix['fields']['slug'] == 'contact':
                return None
        else:  # xml format
            for field in obj_fix.getElementsByTagName("field"):
                if field.getAttribute("name") == "slug":
                    if field.childNodes[0].data == 'contact':
                        return None
                    else:
                        break
        return obj_fix
