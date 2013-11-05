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
from django.contrib.contenttypes.models import ContentType

from deep_serializer.settings import USE_INTERNAL_SERIALIZERS

if USE_INTERNAL_SERIALIZERS:
    from deep_serializer.serializers.base import DeserializationError
else:
    from django.core.serializers.base import DeserializationError

from deep_serializer import base
from deep_serializer.utils import findnth
from xml.dom import minidom

TOKEN_M2M_START = '<object>'
TOKEN_OBJECT_START = '<object '
TOKEN_OBJECT_END = '</object>'
TOKEN_OBJECTS_END = '</django-objects>'


class Serializer(base.Serializer):
    format = 'xml'


class Deserializer(base.Deserializer):

    format = 'xml'

    @classmethod
    def calcule_item_end(cls, fixtures, start, num_m2m=0):
        end = start + findnth(fixtures[start:], TOKEN_OBJECT_END, num_m2m)
        if end < start:
            raise DeserializationError('Bad formatting on fixtures')
        fixtures_item = fixtures[start: end + len(TOKEN_OBJECT_END)]
        num_m2m_item = fixtures_item.count(TOKEN_M2M_START)
        if num_m2m_item != num_m2m:
            return cls.calcule_item_end(fixtures, start, num_m2m=num_m2m_item)
        return end

    @classmethod
    def deserialize_reorder(cls, fixtures, num_item, num_reorder):
        num_items = fixtures.count(TOKEN_OBJECT_START)
        if num_reorder > sum(range(num_items)):
            raise DeserializationError('Maximum number of reordering')
        fixture_first_item_start = findnth(fixtures, TOKEN_OBJECT_START, 0)
        fixture_item_start = findnth(fixtures, TOKEN_OBJECT_START, num_item)
        fixture_item_end = cls.calcule_item_end(fixtures, fixture_item_start)
        if fixture_item_start == -1 or fixture_item_end == -1:
            raise DeserializationError('Bad formatting on fixtures')
        fixtures_item = fixtures[fixture_item_start:fixture_item_end + len(TOKEN_OBJECT_END)]
        fixtures = fixtures[:fixture_first_item_start] + fixtures[fixture_item_end + len(TOKEN_OBJECT_END):]
        last_item_index = findnth(fixtures, TOKEN_OBJECTS_END, 0)
        if last_item_index == -1:
            raise DeserializationError('Bad formatting on fixtures')
        fixtures = fixtures[:last_item_index] + fixtures_item + fixtures[last_item_index:]
        return fixtures

    @classmethod
    def pretreatment_fixtures(cls, initial_obj, fixtures, walking_classes,
                              request=None, deserialize_options=None,
                              sorted_function=None):
        fixture_first_item_start = findnth(fixtures, TOKEN_OBJECT_START, 0)
        last_item_index = findnth(fixtures, TOKEN_OBJECTS_END, 0)
        fixtures_xml = minidom.parseString(fixtures)
        nodes = fixtures_xml.getElementsByTagName('object')
        if sorted_function:
            nodes.sort(cmp=sorted_function)
        new_fixtures = ''
        for obj_fix in nodes:
            app_model = obj_fix.getAttribute("model")
            if not app_model:  # m2m relations
                continue
            app_label, model = app_model.split(".")
            model = ContentType.objects.get(model=model, app_label=app_label).model_class()
            meta_walking_class = cls.get_meta_walking_class(model, walking_classes)
            new_obj_fix = meta_walking_class.pretreatment_fixture(initial_obj, obj_fix, request, deserialize_options)
            if new_obj_fix:
                new_fixtures += new_obj_fix.toxml()
        new_fixtures = fixtures[:fixture_first_item_start] + new_fixtures + fixtures[last_item_index:]
        return new_fixtures
