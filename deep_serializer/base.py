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
    def get_meta_walking_class(cls, obj_or_model, walking_classes):
        if walking_classes and isinstance(walking_classes, dict):
            if isinstance(obj_or_model, models.Model):
                model = obj_or_model.__class__
            else:
                model = obj_or_model
            return walking_classes.get(model, BaseMetaWalkClass)
        return BaseMetaWalkClass


class Serializer(BaseMetaWalkClassProvider):

    @classmethod
    def walking_into_class(cls, initial_obj, obj, field_name, model,
                           walking_classes, walking_always=False, request=None):
        if walking_always:
            return WALKING_INTO_CLASS
        elif model in walking_classes:
            meta_class = cls.get_meta_walking_class(obj, walking_classes)
            return meta_class.walking_into_class(initial_obj, obj, field_name, model, request=request)
        else:
            return WALKING_STOP

    @classmethod
    def serialize_fk(cls, initial_obj, obj, object_list,
                     walking_classes=None,
                     walking_always=True,
                     natural_keys=True,
                     several_path=False,
                     request=None):
        model = obj.__class__
        for field in model._meta.fields:
            if hasattr(field.rel, 'to'):
                walking_status = cls.walking_into_class(initial_obj,
                                                        obj, field.name,
                                                        field.rel.to,
                                                        walking_classes,
                                                        walking_always,
                                                        request=request)

                if walking_status == WALKING_STOP:
                    field_null = field.null
                    field_blank = field.blank
                    field.null = True
                    field.blank = True
                    setattr(obj, field.name, None)
                    field.null = field_null
                    field.blank = field_blank

                if walking_status != WALKING_INTO_CLASS:
                    continue
                content = getattr(obj, field.name)
                if content and not content in object_list:
                    cls.objects_to_serialize(initial_obj, content, object_list,
                                             walking_classes=walking_classes,
                                             walking_always=walking_always,
                                             natural_keys=natural_keys,
                                             several_path=several_path,
                                             request=request)
                elif content and several_path:
                    cls.add_content(object_list, content,
                                    natural_keys=natural_keys,
                                    request=request)

    @classmethod
    def serialize_m2m(cls, initial_obj, obj, object_list,
                      walking_classes=None,
                      walking_always=True,
                      natural_keys=True,
                      several_path=False,
                      request=None):
        model = obj.__class__
        for field in model._meta.many_to_many:
            walking_status = cls.walking_into_class(initial_obj,
                                                    obj,
                                                    field.name,
                                                    field.rel.to,
                                                    walking_classes,
                                                    walking_always,
                                                    request=request)
            if walking_status == WALKING_STOP:
                getattr(obj, field.name).clear()

            if walking_status != WALKING_INTO_CLASS:
                continue
            meta_class = cls.get_meta_walking_class(obj, walking_classes)
            contents = getattr(obj, field.name).all()
            contents = meta_class.get_queryset_to_relation(initial_obj, obj, field.name, contents, request=request)
            for content in contents:
                if content and not content in object_list:
                    cls.objects_to_serialize(initial_obj, content, object_list,
                                             walking_classes=walking_classes,
                                             walking_always=walking_always,
                                             natural_keys=natural_keys,
                                             several_path=several_path,
                                             request=request)
                elif content and several_path:
                    cls.add_content(object_list, content,
                                    natural_keys=natural_keys,
                                    request=request)

    @classmethod
    def serialize_reverse(cls, initial_obj, obj, object_list,
                          walking_classes=None,
                          walking_always=True,
                          natural_keys=True,
                          several_path=False,
                          request=None):
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
                    meta_class = cls.get_meta_walking_class(obj, walking_classes)
                    contents = relation.all()
                    contents = meta_class.get_queryset_to_relation(initial_obj, obj,
                                                                   related_query_name,
                                                                   contents,
                                                                   request=request)
            except ObjectDoesNotExist:
                contents = []
            for content in contents:
                if content and not content in object_list:
                    cls.objects_to_serialize(initial_obj, content, object_list,
                                             walking_classes=walking_classes,
                                             walking_always=walking_always,
                                             natural_keys=natural_keys,
                                             several_path=several_path,
                                             request=request)
                elif content and several_path:
                    cls.add_content(object_list, content,
                                    natural_keys=natural_keys,
                                    request=request)

    @classmethod
    def add_content(cls, object_list, content, natural_keys=True, request=None):
        if natural_keys and not has_natural_key(content):
            raise DoesNotNaturalKeyException("The model %s don't have a natural key" % content.__class__)
        object_list.append(content)

    @classmethod
    def objects_to_serialize(cls, initial_obj, obj, object_list,
                             walking_classes=None,
                             walking_always=True,
                             natural_keys=True,
                             several_path=False,
                             request=None):
        walking_classes = walking_classes or []
        cls.add_content(object_list, obj,
                        natural_keys=natural_keys,
                        request=request)
        cls.serialize_fk(initial_obj,
                         obj, object_list,
                         walking_classes=walking_classes,
                         walking_always=walking_always,
                         natural_keys=natural_keys,
                         several_path=several_path,
                         request=request)
        cls.serialize_m2m(initial_obj,
                          obj,
                          object_list,
                          walking_classes=walking_classes,
                          walking_always=walking_always,
                          natural_keys=natural_keys,
                          several_path=several_path,
                          request=request)
        cls.serialize_reverse(initial_obj, obj, object_list,
                              walking_classes=walking_classes,
                              walking_always=walking_always,
                              natural_keys=natural_keys,
                              several_path=several_path,
                              request=request)

    @classmethod
    def serialize(cls, initial_obj,
                  walking_classes=None,
                  walking_always=False,
                  natural_keys=True,
                  indent=None,
                  serialize_options=None,
                  can_get_objs_from_several_path=False,
                  request=None):
        serialize_options = serialize_options or {}
        walking_classes = walking_classes or []
        object_list = []
        if natural_keys:
            serialize_options['use_natural_primary_keys'] = True
            serialize_options['use_natural_foreign_keys'] = True
        contents_to_serialize = []
        with transaction.commit_manually():
            try:
                cls.objects_to_serialize(initial_obj, initial_obj, object_list,
                                         walking_classes=walking_classes,
                                         walking_always=walking_always,
                                         natural_keys=natural_keys,
                                         several_path=can_get_objs_from_several_path,
                                         request=request)
                for content in object_list:
                    meta_walking_class = cls.get_meta_walking_class(content, walking_classes)
                    content_to_serialize = meta_walking_class.pre_serialize(initial_obj, content, request, serialize_options)
                    if content_to_serialize and not content_to_serialize in contents_to_serialize:
                        contents_to_serialize.append(content_to_serialize)
                fixtures = serializers.serialize(cls.format, contents_to_serialize, indent=indent,
                                                 **serialize_options)
            finally:
                transaction.rollback()
        return fixtures


class Deserializer(BaseMetaWalkClassProvider):

    @classmethod
    def deserialize(cls, fixtures,
                    initial_obj=None,
                    walking_classes=None,
                    using='default',
                    natural_keys=True,
                    exclude_contents=None,
                    deserialize_options=None,
                    request=None,
                    pretreatment_fixtures=False,
                    pretreatment_fixtures_sorted_function=None):
        with transaction.commit_manually():
            try:
                if pretreatment_fixtures:
                    fixtures = cls.pretreatment_fixtures(initial_obj,
                                                         fixtures,
                                                         walking_classes,
                                                         deserialize_options,
                                                         pretreatment_fixtures_sorted_function)
                contents = cls._deserialize(fixtures,
                                            initial_obj=initial_obj,
                                            walking_classes=walking_classes,
                                            using=using,
                                            natural_keys=natural_keys,
                                            exclude_contents=exclude_contents,
                                            deserialize_options=deserialize_options,
                                            request=request)
                transaction.commit()
                return contents
            except Exception as e:
                if settings.DEBUG:
                    import traceback
                    logger.error(traceback.format_exc())
                transaction.rollback()
                raise e

    @classmethod
    def _deserialize(cls, fixtures,
                     initial_obj=None,
                     walking_classes=None,
                     using='default',
                     natural_keys=True,
                     exclude_contents=None,
                     deserialize_options=None,
                     request=None,
                     contents=None,
                     num_reorder=0):
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
                meta_walking_class = cls.get_meta_walking_class(obj.object, walking_classes)
                meta_walking_class.pre_save(initial_obj, obj.object, request=request)
                obj.save(using=using)
                meta_walking_class.post_save(initial_obj, obj.object, request=request)
                contents.append(obj.object)
                exclude_contents.append(obj_key)
        if obj_does_not_exist:
            num_reorder = num_reorder + 1
            fixtures = cls.deserialize_reorder(fixtures, num_item, num_reorder)
            cls._deserialize(fixtures,
                             initial_obj=initial_obj,
                             walking_classes=walking_classes,
                             using=using,
                             natural_keys=natural_keys,
                             exclude_contents=exclude_contents,
                             deserialize_options=deserialize_options,
                             request=request,
                             contents=contents,
                             num_reorder=num_reorder)
        return contents

    @classmethod
    def deserialize_reorder(cls, fixtures, num_item, num_reorder):
        raise NotImplementedError

    @classmethod
    def pretreatment_fixtures(cls, initial_obj, fixtures, walking_classes,
                              request=None,
                              deserialize_options=None,
                              sorted_function=None):
        raise NotImplementedError


def serializer(format, *args, **kwargs):
    s = get_serializer(format)
    return s.serialize(*args, **kwargs)


def deserializer(format, *args, **kwargs):
    d = get_deserializer(format)
    return d.deserialize(*args, **kwargs)


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
