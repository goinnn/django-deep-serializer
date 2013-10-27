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

from deep_serializer import Serializer, BaseMetaWalkClass

from example.app.models import WebSite, Page
from example.app.serializer import (WebSiteClone, PageClone, UserClone, WebSiteOwnersClone,
                                    WebSiteRestore, PageRestore,
                                    WebSiteRestoreNaturalKey, PageRestoreNaturalKey)

walking_clone_classes = {WebSite: WebSiteClone,
                         Page: PageClone,
                         User: BaseMetaWalkClass}

walking_clone_owners_classes = {WebSite: WebSiteOwnersClone,
                                Page: PageClone,
                                User: UserClone}

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
    elif action == 'restore':
        walking_classes = walking_restore_classes
        natural_keys = False
    elif action == 'restore-natural-keys':
        walking_classes = walking_restore_classes_natural
        natural_keys = True
    return (walking_classes, natural_keys)


def serialize_website(website, action='clone', format='json'):
    walking_classes, natural_keys = get_params_to_serialize_deserialize(action)
    return Serializer.serialize(website, request=None,
                                walking_classes=walking_classes,
                                format=format,
                                indent=4,
                                natural_keys=natural_keys)


def deserialize_website(website, fixtures, action='clone', format='json'):
    walking_classes, natural_keys = get_params_to_serialize_deserialize(action)
    return Serializer.deserialize(website, fixtures,
                                  format=format,
                                  walking_classes=walking_classes,
                                  natural_keys=natural_keys)


def clone_website(website, action='clone', format='python'):
    fixtures = serialize_website(website, action=action, format=format)
    return deserialize_website(website, fixtures, action=action, format=format)
