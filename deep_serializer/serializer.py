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
import logging
import sys

from django.conf import settings
from django.core import serializers
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db import transaction

from deep_serializer.settings import USE_INTERNAL_SERIALIZERS

if USE_INTERNAL_SERIALIZERS:
    from deep_serializer.serializers.base import DeserializationError
else:
    from django.core.serializers.base import DeserializationError

from deep_serializer.api import BaseMetaWalkClass, WALKING_INTO_CLASS, WALKING_STOP
from deep_serializer.exceptions import DoesNotNaturalKeyException
from deep_serializer.utils import has_natural_key, dumps, findnth

PY3 = sys.version_info[0] == 3

logger = logging.getLogger(__name__)


class Serializer(object):

    @classmethod
    def walking_into_class(cls, obj, field_name, model, walking_classes, walking_always=False):
        if walking_always:
            return WALKING_INTO_CLASS
        elif model in walking_classes:
            meta_class = cls.get_meta_walking_class(obj.__class__, walking_classes)
            return meta_class.walking_into_class(obj, field_name, model)
        else:
            return WALKING_STOP

    @classmethod
    def serialize_fk(cls, obj, object_list, request=None, natural_keys=True, walking_classes=None, walking_always=True):
        model = obj.__class__
        for field in model._meta.fields:
            if hasattr(field.rel, 'to'):
                walking_status = cls.walking_into_class(obj, field.name, field.rel.to, walking_classes, walking_always)
                if walking_status != WALKING_INTO_CLASS:
                    continue
                content = getattr(obj, field.name)
                if content and not content in object_list:
                    cls.objects_to_serialize(content, object_list, request,
                                             natural_keys, walking_classes, walking_always)

    @classmethod
    def serialize_m2m(cls, obj, object_list, request=None, natural_keys=True, walking_classes=None, walking_always=True):
        model = obj.__class__
        for field in model._meta.many_to_many:
            walking_status = cls.walking_into_class(obj, field.name, field.rel.to, walking_classes, walking_always)
            if walking_status != WALKING_INTO_CLASS:
                continue
            meta_class = cls.get_meta_walking_class(obj.__class__, walking_classes)
            contents = getattr(obj, field.name).all()
            contents = meta_class.get_queryset_to_relation(obj, field.name, contents, request=request)
            for content in contents:
                if content and not content in object_list:
                    cls.objects_to_serialize(content, object_list, request,
                                             natural_keys, walking_classes, walking_always)

    @classmethod
    def serialize_reverse(cls, obj, object_list, request=None, natural_keys=True, walking_classes=None, walking_always=True):
        model = obj.__class__
        for field in model._meta.get_all_related_objects():
            related_query_name = field.field.related_query_name()
            walking_status = cls.walking_into_class(obj, related_query_name, field.model, walking_classes, walking_always)
            if walking_status != WALKING_INTO_CLASS:
                continue
            try:
                # This has to be getattr. If you use hasattr and this raise a Exception this return False
                relation = getattr(obj, related_query_name, None)
                if not relation:
                    related_query_name = '%s_set' % related_query_name
                    relation = getattr(obj, related_query_name)
                if isinstance(relation, models.Model):
                    contents = [relation]
                else:
                    meta_class = cls.get_meta_walking_class(obj.__class__, walking_classes)
                    contents = relation.all()
                    contents = meta_class.get_queryset_to_relation(obj, related_query_name, contents, request=request)
            except ObjectDoesNotExist:
                contents = []
            for content in contents:
                if content and not content in object_list:
                    cls.objects_to_serialize(content, object_list, request,
                                             natural_keys, walking_classes, walking_always)

    @classmethod
    def add_content(cls, object_list, content, request=None, natural_keys=True):
        if natural_keys and not has_natural_key(content):
            raise DoesNotNaturalKeyException("The model %s don't have a natural key" % content.__class__)
        object_list.append(content)

    @classmethod
    def objects_to_serialize(cls, obj, object_list=None, request=None, natural_keys=True, walking_classes=None, walking_always=True):
        object_list = object_list or []
        walking_classes = walking_classes or []
        if obj in object_list:
            return object_list
        cls.add_content(object_list, obj, request=None, natural_keys=natural_keys)
        cls.serialize_fk(obj, object_list, request=request, natural_keys=natural_keys, walking_classes=walking_classes, walking_always=walking_always)
        cls.serialize_m2m(obj, object_list, request=request, natural_keys=natural_keys, walking_classes=walking_classes, walking_always=walking_always)
        cls.serialize_reverse(obj, object_list, request=request, natural_keys=natural_keys, walking_classes=walking_classes, walking_always=walking_always)
        return object_list

    @classmethod
    def get_meta_walking_class(cls, model, walking_classes):
        if walking_classes and isinstance(walking_classes, dict):
            return walking_classes.get(model, BaseMetaWalkClass)
        return BaseMetaWalkClass

    @classmethod
    def serialize(cls, obj, request=None, walking_classes=None, natural_keys=True,
                  format='json', indent=None, walking_always=False,
                  options=None):
        options = options or {}
        walking_classes = walking_classes or []
        object_list = None
        contents = cls.objects_to_serialize(obj, object_list,
                                            request=request,
                                            natural_keys=natural_keys,
                                            walking_classes=walking_classes,
                                            walking_always=walking_always)
        if natural_keys:
            options['use_natural_primary_keys'] = True
            options['use_natural_foreign_keys'] = True
        contents_to_serialize = []
        with transaction.commit_manually():
            try:
                for content in contents:
                    meta_walking_class = cls.get_meta_walking_class(content.__class__, walking_classes)
                    for field in content._meta.fields:
                        if hasattr(field.rel, 'to'):
                            walking_status = cls.walking_into_class(content, field.name, field.rel.to, walking_classes, walking_always)
                            if walking_status == WALKING_STOP:
                                field_null = field.null
                                field_blank = field.blank
                                field.null = True
                                field.blank = True
                                setattr(content, field.name, None)
                                field.null = field_null
                                field.blank = field_blank
                    for field in content._meta.many_to_many:
                        walking_status = cls.walking_into_class(content, field.name, field.rel.to, walking_classes, walking_always)
                        if walking_status == WALKING_STOP:
                            getattr(content, field.name).clear()
                    content_to_serialize = meta_walking_class.pre_serialize(obj, content, request, options)
                    if content_to_serialize:
                        contents_to_serialize.append(content_to_serialize)
                fixtures = serializers.serialize(format, contents_to_serialize, indent=indent,
                                                 **options)
            finally:
                transaction.rollback()
        return fixtures

    @classmethod
    def deserialize(cls, initial_obj, fixtures, format='json', walking_classes=None, using='default',
                    natural_keys=True,
                    exclude_contents=None,
                    sorted_function=None):
        with transaction.commit_manually():
            try:
                contents = cls._deserialize(initial_obj, fixtures,
                                            format=format,
                                            walking_classes=walking_classes, using=using,
                                            natural_keys=natural_keys,
                                            exclude_contents=exclude_contents)
                transaction.commit()
                return contents
            except Exception as e:
                if settings.DEBUG:
                    import traceback
                    logger.error(traceback.format_exc())
                transaction.rollback()
                raise e

    @classmethod
    def _deserialize(cls, initial_obj, fixtures, format='json',
                     walking_classes=None, using='default',
                     natural_keys=True, exclude_contents=None,
                     contents=None, num_reorder=0):
        objects = serializers.deserialize(format, fixtures, using=using,
                                          use_natural_primary_keys=natural_keys,
                                          use_natural_foreign_keys=natural_keys)
        exclude_contents = exclude_contents or []
        contents = contents or []
        init = True
        obj_does_not_exist = False
        obj = None
        num_item = 0
        while obj or init:
            init = False
            try:
                if PY3:
                    obj = objects.__next__()
                else:
                    obj = objects.next()
                num_item = num_item + 1
            except (DeserializationError, ObjectDoesNotExist):
                obj_does_not_exist = True
                break
            except StopIteration:
                break
            if natural_keys:
                if not has_natural_key(obj.object):
                    raise DoesNotNaturalKeyException("The model %s don't have a natural key" % obj.object.__class__)
                obj_key = '%s__%s__%s' % (obj.object._meta.app_label,
                                          obj.object._meta.module_name,
                                          obj.object.natural_key())
            else:
                obj_key = '%s__%s__%s' % (obj.object._meta.app_label,
                                          obj.object._meta.module_name,
                                          obj.object.pk)
            if not obj_key in exclude_contents:
                meta_walking_class = cls.get_meta_walking_class(obj.object.__class__, walking_classes)
                meta_walking_class.pre_save(initial_obj, obj.object)
                obj.save(using=using)
                meta_walking_class.post_save(initial_obj, obj.object)
                contents.append(obj.object)
                exclude_contents.append(obj_key)
        if obj_does_not_exist:
            num_reorder = num_reorder + 1
            fixtures = getattr(cls, 'deserialize_reorder_%s' % format)(fixtures, num_item, num_reorder)
            cls._deserialize(initial_obj, fixtures, format=format,
                             walking_classes=walking_classes,
                             natural_keys=natural_keys,
                             exclude_contents=exclude_contents,
                             contents=contents,
                             num_reorder=num_reorder)
        return contents

    @classmethod
    def deserialize_reorder_python(cls, fixtures, num_item, num_reorder):
        num_items = len(fixtures)
        if num_reorder > sum(range(num_items)):
            raise DeserializationError
        fix_obj = fixtures[num_item]
        fixtures = fixtures[num_item + 1:]
        fixtures.append(fix_obj)
        return fixtures

    @classmethod
    def deserialize_reorder_json(cls, fixtures, num_item, num_reorder):
        fixtures_python = json.loads(fixtures)
        fixtures_python = cls.deserialize_reorder_python(fixtures_python, num_item, num_reorder)
        fixtures = dumps(fixtures_python)
        return fixtures

    @classmethod
    def deserialize_reorder_yaml(cls, fixtures, num_item, num_reorder):
        try:
            import yaml
        except ImportError:
            raise DeserializationError
        fixtures_python = yaml.load(fixtures, Loader=yaml.SafeLoader)
        fixtures_python = cls.deserialize_reorder_python(fixtures_python, num_item, num_reorder)
        fixtures = yaml.dump(fixtures_python)
        return fixtures

    @classmethod
    def deserialize_reorder_xml(cls, fixtures, num_item, num_reorder):
        token_object_start = '<object '
        token_object_end = '</object>'
        token_objects_end = '</django-objects>'
        num_items = fixtures.count(token_object_start)
        if num_reorder > sum(range(num_items)):
            raise DeserializationError
        fixture_first_item_start = findnth(fixtures, token_object_start, 0)
        fixture_item_start = findnth(fixtures, token_object_start, num_item)
        fixture_item_end = findnth(fixtures, token_object_end, num_item)
        if fixture_item_start == -1 or fixture_item_end == -1:
            raise DeserializationError
        fixtures_item = fixtures[fixture_item_start:fixture_item_end + 9]
        fixtures = fixtures[:fixture_first_item_start] + fixtures[fixture_item_end + 9:]
        last_item_index = findnth(fixtures, token_objects_end, 0)
        if last_item_index == -1:
            raise DeserializationError
        fixtures = fixtures[:last_item_index] + fixtures_item + fixtures[last_item_index:]
        return fixtures
