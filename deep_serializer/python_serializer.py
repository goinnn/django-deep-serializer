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


class Serializer(base.Serializer):
    format = 'python'


class Deserializer(base.Deserializer):

    format = 'python'

    @classmethod
    def deserialize_reorder(cls, fixtures, num_item, num_reorder):
        num_items = len(fixtures)
        if num_reorder > sum(range(num_items)):
            raise DeserializationError('Maximum number of reordering')
        fix_obj = fixtures[num_item]
        fixtures = fixtures[num_item + 1:]
        fixtures.append(fix_obj)
        return fixtures

    @classmethod
    def pretreatment_fixtures(cls, initial_obj, fixtures, walking_classes,
                              request=None, deserialize_options=None,
                              sorted_function=None):
        if sorted_function:
            fixtures.sort(cmp=sorted_function)
        new_fixtures = []
        for obj_fix in fixtures:
            app_label, model = obj_fix['model'].split(".")
            model = ContentType.objects.get(model=model, app_label=app_label).model_class()
            meta_walking_class = cls.get_meta_walking_class(model, walking_classes)
            new_obj_fix = meta_walking_class.pretreatment_fixture(initial_obj, obj_fix, request, deserialize_options)
            if new_obj_fix:
                new_fixtures.append(new_obj_fix)
        return new_fixtures
