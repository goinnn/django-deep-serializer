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

import logging
import sys

from django.conf import settings
from django.core import serializers
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db import transaction
from django.utils import importlib

from deep_serializer.settings import USE_INTERNAL_SERIALIZERS

if USE_INTERNAL_SERIALIZERS:
    from deep_serializer.serializers.base import DeserializationError
else:
    from django.core.serializers.base import DeserializationError

from deep_serializer.api import BaseMetaWalkClass, WALKING_INTO_CLASS, WALKING_STOP
from deep_serializer.exceptions import DoesNotNaturalKeyException, DeepSerializerDoesNotExist
from deep_serializer.utils import has_natural_key

PY3 = sys.version_info[0] == 3

logger = logging.getLogger(__name__)


BUILTIN_DEEP_SERIALIZERS = {
    "xml": "deep_serializer.xml_serializer",
    "python": "deep_serializer.python_serializer",
    "json": "deep_serializer.json_serializer",
}

try:
    import yaml
    BUILTIN_DEEP_SERIALIZERS["yaml"] = "deep_serializer.yaml_serializer"
except ImportError:
    pass


global _deep_serializers

_deep_serializers = {}


class BaseMetaWalkClassProvider(object):

    @classmethod
    def get_meta_walking_class(cls, model, walking_classes):
        if walking_classes and isinstance(walking_classes, dict):
            return walking_classes.get(model, BaseMetaWalkClass)
        return BaseMetaWalkClass


class Serializer(BaseMetaWalkClassProvider):

    @classmethod
    def walking_into_class(cls, initial_obj, obj, field_name, model,
                           walking_classes, walking_always=False, request=None):
        if walking_always:
            return WALKING_INTO_CLASS
        elif model in walking_classes:
            meta_class = cls.get_meta_walking_class(obj.__class__, walking_classes)
            return meta_class.walking_into_class(initial_obj, obj, field_name, model, request=request)
        else:
            return WALKING_STOP

    @classmethod
    def serialize_fk(cls, initial_obj, obj, object_list, request=None,
                     natural_keys=True, walking_classes=None, walking_always=True):
        model = obj.__class__
        for field in model._meta.fields:
            if hasattr(field.rel, 'to'):
                walking_status = cls.walking_into_class(initial_obj,
                                                        obj, field.name,
                                                        field.rel.to,
                                                        walking_classes,
                                                        walking_always,
                                                        request=request)
                if walking_status != WALKING_INTO_CLASS:
                    continue
                content = getattr(obj, field.name)
                if content and not content in object_list:
                    cls.objects_to_serialize(initial_obj, content, object_list, request,
                                             natural_keys, walking_classes, walking_always)

    @classmethod
    def serialize_m2m(cls, initial_obj, obj, object_list, request=None,
                      natural_keys=True, walking_classes=None, walking_always=True):
        model = obj.__class__
        for field in model._meta.many_to_many:
            walking_status = cls.walking_into_class(initial_obj,
                                                    obj,
                                                    field.name,
                                                    field.rel.to,
                                                    walking_classes,
                                                    walking_always,
                                                    request=request)
            if walking_status != WALKING_INTO_CLASS:
                continue
            meta_class = cls.get_meta_walking_class(obj.__class__, walking_classes)
            contents = getattr(obj, field.name).all()
            contents = meta_class.get_queryset_to_relation(initial_obj, obj, field.name, contents, request=request)
            for content in contents:
                if content and not content in object_list:
                    cls.objects_to_serialize(initial_obj, content, object_list, request,
                                             natural_keys, walking_classes, walking_always)

    @classmethod
    def serialize_reverse(cls, initial_obj, obj, object_list, request=None,
                          natural_keys=True, walking_classes=None, walking_always=True):
        model = obj.__class__
        for field in model._meta.get_all_related_objects():
            related_query_name = field.field.related_query_name()
            walking_status = cls.walking_into_class(initial_obj,
                                                    obj,
                                                    related_query_name,
                                                    field.model,
                                                    walking_classes,
                                                    walking_always,
                                                    request=request)
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
                    contents = meta_class.get_queryset_to_relation(initial_obj, obj,
                                                                   related_query_name,
                                                                   contents,
                                                                   request=request)
            except ObjectDoesNotExist:
                contents = []
            for content in contents:
                if content and not content in object_list:
                    cls.objects_to_serialize(initial_obj, content, object_list, request,
                                             natural_keys, walking_classes, walking_always)

    @classmethod
    def add_content(cls, object_list, content, request=None, natural_keys=True):
        if natural_keys and not has_natural_key(content):
            raise DoesNotNaturalKeyException("The model %s don't have a natural key" % content.__class__)
        object_list.append(content)

    @classmethod
    def objects_to_serialize(cls, initial_obj, obj, object_list=None,
                             request=None, natural_keys=True,
                             walking_classes=None, walking_always=True):
        object_list = object_list or []
        walking_classes = walking_classes or []
        if obj in object_list:
            return object_list
        cls.add_content(object_list, obj, request=None, natural_keys=natural_keys)
        cls.serialize_fk(initial_obj,
                         obj, object_list, request=request,
                         natural_keys=natural_keys,
                         walking_classes=walking_classes,
                         walking_always=walking_always)
        cls.serialize_m2m(initial_obj,
                          obj,
                          object_list,
                          request=request,
                          natural_keys=natural_keys,
                          walking_classes=walking_classes,
                          walking_always=walking_always)
        cls.serialize_reverse(initial_obj, obj, object_list,
                              request=request,
                              natural_keys=natural_keys,
                              walking_classes=walking_classes,
                              walking_always=walking_always)
        return object_list

    @classmethod
    def serialize(cls, obj, request=None, walking_classes=None, natural_keys=True,
                  indent=None, walking_always=False,
                  serialize_options=None):
        serialize_options = serialize_options or {}
        walking_classes = walking_classes or []
        object_list = None
        contents = cls.objects_to_serialize(obj, obj, object_list,
                                            request=request,
                                            natural_keys=natural_keys,
                                            walking_classes=walking_classes,
                                            walking_always=walking_always)
        if natural_keys:
            serialize_options['use_natural_primary_keys'] = True
            serialize_options['use_natural_foreign_keys'] = True
        contents_to_serialize = []
        with transaction.commit_manually():
            try:
                for content in contents:
                    meta_walking_class = cls.get_meta_walking_class(content.__class__, walking_classes)
                    for field in content._meta.fields:
                        if hasattr(field.rel, 'to'):
                            walking_status = cls.walking_into_class(obj,
                                                                    content,
                                                                    field.name,
                                                                    field.rel.to,
                                                                    walking_classes,
                                                                    walking_always,
                                                                    request=request)
                            if walking_status == WALKING_STOP:
                                field_null = field.null
                                field_blank = field.blank
                                field.null = True
                                field.blank = True
                                setattr(content, field.name, None)
                                field.null = field_null
                                field.blank = field_blank
                    for field in content._meta.many_to_many:
                        walking_status = cls.walking_into_class(obj,
                                                                content,
                                                                field.name,
                                                                field.rel.to,
                                                                walking_classes,
                                                                walking_always,
                                                                request=request)
                        if walking_status == WALKING_STOP:
                            getattr(content, field.name).clear()
                    content_to_serialize = meta_walking_class.pre_serialize(obj, content, request, serialize_options)
                    if content_to_serialize:
                        contents_to_serialize.append(content_to_serialize)
                fixtures = serializers.serialize(cls.format, contents_to_serialize, indent=indent,
                                                 **serialize_options)
            finally:
                transaction.rollback()
        return fixtures


class Deserializer(BaseMetaWalkClassProvider):

    @classmethod
    def deserialize(cls, initial_obj, fixtures, request=None,
                    walking_classes=None,
                    using='default',
                    natural_keys=True,
                    exclude_contents=None,
                    deserialize_options=None,
                    pretreatment_fixtures=False,
                    pretreatment_fixtures_sorted_function=None):
        deserialize_options = deserialize_options or {}
        with transaction.commit_manually():
            try:
                if pretreatment_fixtures:
                    fixtures = cls.pretreatment_fixtures(initial_obj,
                                                         fixtures,
                                                         walking_classes,
                                                         deserialize_options,
                                                         pretreatment_fixtures_sorted_function)
                contents = cls._deserialize(initial_obj, fixtures,
                                            request=request,
                                            walking_classes=walking_classes,
                                            using=using,
                                            natural_keys=natural_keys,
                                            exclude_contents=exclude_contents,
                                            deserialize_options=deserialize_options)
                transaction.commit()
                return contents
            except Exception as e:
                if settings.DEBUG:
                    import traceback
                    logger.error(traceback.format_exc())
                transaction.rollback()
                raise e

    @classmethod
    def _deserialize(cls, initial_obj, fixtures,
                     request=None,
                     walking_classes=None,
                     using='default',
                     natural_keys=True,
                     exclude_contents=None,
                     deserialize_options=None,
                     contents=None, num_reorder=0):
        deserialize_options = deserialize_options or {}
        if natural_keys:
            deserialize_options['use_natural_primary_keys'] = True
            deserialize_options['use_natural_foreign_keys'] = True
        objects = serializers.deserialize(cls.format, fixtures, using=using,
                                          **deserialize_options)
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
                meta_walking_class.pre_save(initial_obj, obj.object, request=request)
                obj.save(using=using)
                meta_walking_class.post_save(initial_obj, obj.object, request=request)
                contents.append(obj.object)
                exclude_contents.append(obj_key)
        if obj_does_not_exist:
            num_reorder = num_reorder + 1
            fixtures = cls.deserialize_reorder(fixtures, num_item, num_reorder)
            cls._deserialize(initial_obj, fixtures,
                             request=request,
                             walking_classes=walking_classes,
                             using=using,
                             natural_keys=natural_keys,
                             exclude_contents=exclude_contents,
                             deserialize_options=deserialize_options,
                             contents=contents,
                             num_reorder=num_reorder)
        return contents

    @classmethod
    def deserialize_reorder(cls, fixtures, num_item, num_reorder):
        raise NotImplementedError

    @classmethod
    def pretreatment_fixtures(cls, initial_obj, fixtures, walking_classes,
                              request=None, deserialize_options=None,
                              sorted_function=None):
        raise NotImplementedError


def serializer(format, initial_obj, request=None, walking_classes=None, natural_keys=True,
               indent=None, walking_always=False,
               serialize_options=None):
    s = get_serializer(format)
    return s.serialize(initial_obj, request=request,
                       walking_classes=walking_classes,
                       indent=indent,
                       natural_keys=natural_keys,
                       walking_always=walking_always,
                       serialize_options=serialize_options)


def deserializer(format, initial_obj, fixtures, request=None, walking_classes=None,
                 using='default', natural_keys=True, exclude_contents=None,
                 pretreatment_fixtures=False,
                 pretreatment_fixtures_sorted_function=None,
                 deserialize_options=None):
    d = get_deserializer(format)
    return d.deserialize(initial_obj, fixtures, request=request,
                         walking_classes=walking_classes,
                         using=using,
                         natural_keys=natural_keys,
                         exclude_contents=exclude_contents,
                         deserialize_options=deserialize_options,
                         pretreatment_fixtures=pretreatment_fixtures,
                         pretreatment_fixtures_sorted_function=pretreatment_fixtures_sorted_function,)


def get_serializer(format):
    if not _deep_serializers:
        _load_serializers()
    if format not in _deep_serializers:
        raise DeepSerializerDoesNotExist(format)
    return _deep_serializers[format].Serializer


def get_deserializer(format):
    if not _deep_serializers:
        _load_serializers()
    if format not in _deep_serializers:
        raise DeepSerializerDoesNotExist(format)
    return _deep_serializers[format].Deserializer


def _load_serializers():
    global _deep_serializers
    deep_serializers = {}
    for format in BUILTIN_DEEP_SERIALIZERS:
        deep_serializers[format] = importlib.import_module(BUILTIN_DEEP_SERIALIZERS[format])
    if hasattr(settings, "SERIALIZATION_DEEP_MODULES"):
        for format in settings.SERIALIZATION_DEEP_MODULES:
            deep_serializers[format] = importlib.import_module(settings.SERIALIZATION_DEEP_MODULES[format])
    _deep_serializers = deep_serializers
