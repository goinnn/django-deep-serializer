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
from hashlib import sha1

from deep_serializer import (BaseMetaWalkClass, WALKING_STOP,
                             ONLY_REFERENCE, WALKING_INTO_CLASS)
from deep_serializer.exceptions import DeepSerializerDoesNotExist


def update_the_serializer(obj, field_name):
    msg = 'Please update the serializer this class: %s has not define the behavior to this relation: %s' % (obj.__class__.__name__, field_name)
    raise DeepSerializerDoesNotExist(msg)


class MyMetaWalkClass(BaseMetaWalkClass):

    @classmethod
    def pre_serialize(cls, initial_obj, obj, request=None, serialize_options=None):
        serialize_options = serialize_options or {}
        if not hasattr(initial_obj, 'only_serializer'):
            initial_obj.only_serializer = serialize_options.pop('only_serializer', None)
        obj = super(MyMetaWalkClass, cls).pre_serialize(initial_obj, obj,
                                                        request,
                                                        serialize_options=serialize_options)
        if not initial_obj.only_serializer:
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
        elif field_name == 'page':
            return WALKING_INTO_CLASS
        update_the_serializer(obj, field_name)


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
        if field_name in ('pages_created_of', 'website', 'website_initial_page'):
            return WALKING_STOP
        elif field_name in ('created_from', 'last_editor'):
            return ONLY_REFERENCE
        update_the_serializer(obj, field_name)

    @classmethod
    def post_save(cls, initial_obj, obj, request=None):
        super(PageClone, cls).post_save(initial_obj, obj, request=request)
        initial_page = obj.created_from.website.initial_page
        if initial_page and obj.slug == initial_page.slug:
            obj.website.initial_page = obj
            obj.website.save()

## End example 1


## Example 2: Clone an WebSite and also clone the owners

def get_new_username(website_slug, username):
    new_username = '%s--%s' % (website_slug, username)
    return sha1(new_username.encode('utf-8')).hexdigest()


class WebSiteOwnersClone(WebSiteClone):

    @classmethod
    def walking_into_class(cls, initial_obj, obj, field_name, model, request=None):
        if field_name in ('initial_page', 'websites_created_of'):
            return WALKING_STOP
        elif field_name == 'original_website':
            return ONLY_REFERENCE
        elif field_name in ('page', 'owners'):
            return WALKING_INTO_CLASS
        update_the_serializer(obj, field_name)

    @classmethod
    def post_save(cls, initial_obj, obj, request=None):
        super(WebSiteOwnersClone, cls).pre_save(initial_obj, obj, request=request)
        new_owners_username = []
        for owner in initial_obj.owners.all():
            new_username = get_new_username(initial_obj.slug, owner.username)
            new_owners_username.append(new_username)
        initial_obj.new_owners_username = new_owners_username
        db_website = initial_obj.__class__.objects.get(slug=initial_obj.slug)
        db_website.owners = []


class PageOwnersClone(PageClone):

    @classmethod
    def walking_into_class(cls, initial_obj, obj, field_name, model, request=None):
        if field_name in ('pages_created_of', 'website', 'website_initial_page'):
            return WALKING_STOP
        elif field_name == 'created_from':
            return ONLY_REFERENCE
        elif field_name == 'last_editor':
            return WALKING_INTO_CLASS
        update_the_serializer(obj, field_name)


class UserClone(BaseMetaWalkClass):

    @classmethod
    def pre_serialize(cls, initial_obj, obj, request, serialize_options=None):
        obj = super(UserClone, cls).pre_serialize(initial_obj, obj,
                                                  request,
                                                  serialize_options=serialize_options)
        obj.date_joined = None
        obj.username = get_new_username(initial_obj.slug, obj.username)
        obj.email = 'xxx@example.com'
        return obj

    @classmethod
    def walking_into_class(cls, initial_obj, obj, field_name, model, request=None):
        return WALKING_STOP

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
        if obj.username in initial_obj.new_owners_username:
            db_website = initial_obj.__class__.objects.get(slug=initial_obj.slug)
            db_website.owners.add(obj)


## End example 2


## Example 3: Restore a website using primary keys


class WebSiteRestore(MyMetaWalkClass):

    @classmethod
    def walking_into_class(cls, initial_obj, obj, field_name, model, request=None):
        if field_name in ('websites_created_of', 'initial_page', 'original_website', 'owners'):
            return ONLY_REFERENCE
        elif field_name == 'page':
            return WALKING_INTO_CLASS
        update_the_serializer(obj, field_name)


class PageRestore(MyMetaWalkClass):

    @classmethod
    def walking_into_class(cls, initial_obj, obj, field_name, model, request=None):
        if field_name == 'website_initial_page':
            return WALKING_STOP
        elif field_name in ('pages_created_of', 'created_from', 'website', 'last_editor'):
            return ONLY_REFERENCE
        update_the_serializer(obj, field_name)


## End example 3

## Example 4: Restore a website using natural keys


class WebSiteRestoreNaturalKey(MyMetaWalkClass):

    @classmethod
    def pre_serialize(cls, initial_obj, obj, request, serialize_options=None):
        obj = super(WebSiteRestoreNaturalKey, cls).pre_serialize(
            initial_obj, obj, request, serialize_options=serialize_options)
        if not initial_obj.only_serializer:
            obj.initial_page_bc = obj.initial_page
            obj.initial_page = None
        return obj

    @classmethod
    def walking_into_class(cls, initial_obj, obj, field_name, model, request=None):
        if field_name in ('websites_created_of', 'initial_page', 'original_website', 'owners', 'last_editor'):
            return ONLY_REFERENCE
        elif field_name == 'page':
            return WALKING_INTO_CLASS
        update_the_serializer(obj, field_name)


class PageRestoreNaturalKey(MyMetaWalkClass):

    @classmethod
    def walking_into_class(cls, initial_obj, obj, field_name, model, request=None):
        if field_name == 'website_initial_page':
            return WALKING_STOP
        elif field_name in ('pages_created_of', 'created_from', 'website', 'last_editor'):
            return ONLY_REFERENCE
        update_the_serializer(obj, field_name)

    @classmethod
    def post_save(cls, initial_obj, obj, request=None):
        super(PageRestoreNaturalKey, cls).post_save(initial_obj, obj, request=request)
        initial_page = initial_obj.initial_page_bc
        if initial_page and obj.slug == initial_page.slug:
            obj.website.initial_page = obj
            obj.website.save()

## End example 4

## Example 5: Clone filtering objects


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

## End example 5
