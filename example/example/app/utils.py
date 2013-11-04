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

from django.contrib.auth.models import User

from deep_serializer import serializer, deserializer, BaseMetaWalkClass

from example.app.models import WebSite, Page
from example.app.serializer import (WebSiteClone, WebSiteOwnersClone, WebSiteRestore, WebSiteRestoreNaturalKey,
                                    PageClone, PageOwnersClone, PageCloneFiltering, PageRestore, PageRestoreNaturalKey,
                                    UserClone)

walking_clone_classes = {WebSite: WebSiteClone,
                         Page: PageClone,
                         User: BaseMetaWalkClass}

walking_clone_owners_classes = {WebSite: WebSiteOwnersClone,
                                Page: PageOwnersClone,
                                User: UserClone}

walking_filtering_classes = {WebSite: WebSiteClone,
                             Page: PageCloneFiltering,
                             User: BaseMetaWalkClass}

walking_restore_classes = {WebSite: WebSiteRestore,
                           Page: PageRestore,
                           User: BaseMetaWalkClass}

walking_restore_classes_natural = {WebSite: WebSiteRestoreNaturalKey,
                                   Page: PageRestoreNaturalKey,
                                   User: BaseMetaWalkClass}


def get_params_to_serialize_deserialize(action):
    if action == 'clone':
        walking_classes = walking_clone_classes
        natural_keys = True
    elif action == 'clone-with-owners':
        walking_classes = walking_clone_owners_classes
        natural_keys = True
    elif action == 'clone-filtering-objects':
        walking_classes = walking_filtering_classes
        natural_keys = True
    elif action == 'restore':
        walking_classes = walking_restore_classes
        natural_keys = False
    elif action == 'restore-natural-keys':
        walking_classes = walking_restore_classes_natural
        natural_keys = True
    return (walking_classes, natural_keys)


def serialize_website(website, action='clone', format='json', serialize_options=None):
    walking_classes, natural_keys = get_params_to_serialize_deserialize(action)
    return serializer(format,
                      website,
                      walking_classes=walking_classes,
                      natural_keys=natural_keys,
                      can_get_objs_from_several_path=action == 'clone-with-owners',
                      serialize_options=serialize_options,
                      request=None)


def deserialize_website(website, fixtures, action='clone', format='json'):
    walking_classes, natural_keys = get_params_to_serialize_deserialize(action)
    return deserializer(format, website, fixtures,
                        request=None,
                        walking_classes=walking_classes,
                        natural_keys=natural_keys,
                        pretreatment_fixtures=action == 'clone-filtering-objects')


def clone_website(website, action='clone', format='json'):
    fixtures = serialize_website(website, action=action, format=format)
    return deserialize_website(website, fixtures, action=action, format=format)
