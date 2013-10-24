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
import os
from pprint import pprint
from tempfile import gettempdir

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core import serializers
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db import transaction
from django.utils import simplejson

from deep_serialize.settings import USE_INTERNAL_SERIALIZERS
if USE_INTERNAL_SERIALIZERS:
    from deep_serialize.serializers.base import DeserializationError
else:
    from django.core.serializers.base import DeserializationError


from deep_serialize.exceptions import DoesNotNaturalKeyException
from deep_serialize.utils import (has_natural_key,
                                  dumps,
                                  BaseMetaWalkClass,
                                  WALKING_INTO_CLASS,
                                  WALKING_STOP)

logger = logging.getLogger('vpsites.editor')


def log_json(filename, json):
    tmpdir = gettempdir()
    log = open(os.path.join(tmpdir, filename), 'w')
    pprint(json, log)
    log.close()


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
        use_natural_primary_keys = False
        use_natural_foreign_keys = False
        contents = cls.objects_to_serialize(obj, object_list,
                                            request=request,
                                            natural_keys=natural_keys,
                                            walking_classes=walking_classes,
                                            walking_always=walking_always)
        if natural_keys:
            use_natural_primary_keys = True
            use_natural_foreign_keys = True
        contents_to_serialize = []
        with transaction.commit_manually():
            try:
                for content in contents:
                    meta_walking_class = cls.get_meta_walking_class(content.__class__, walking_classes)
                    for field in content._meta.fields:
                        if hasattr(field.rel, 'to'):
                            walking_status = cls.walking_into_class(content, field.name, field.rel.to, walking_classes, walking_always)
                            if walking_status == WALKING_STOP:
                                field.null = True
                                field.blank = True
                                setattr(content, field.name, None)
                    for field in content._meta.many_to_many:
                        walking_status = cls.walking_into_class(content, field.name, field.rel.to, walking_classes, walking_always)
                        if walking_status == WALKING_STOP:
                            setattr(content, field.name, [])
                    content_to_serialize = meta_walking_class.pre_serialize(obj, content, request, options)
                    if content_to_serialize:
                        contents_to_serialize.append(content_to_serialize)
                fixtures = serializers.serialize(format, contents_to_serialize, indent=indent,
                                                 use_natural_primary_keys=use_natural_primary_keys,
                                                 use_natural_foreign_keys=use_natural_foreign_keys,
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
                fixtures_python = simplejson.loads(fixtures)
                fixtures_python_changed = [obj for obj in fixtures_python if obj['fields'].pop('changed', True) and not obj['fields'].get('deleted', False)]
                fixtures_python_deleted = [obj for obj in fixtures_python if obj['fields'].get('deleted', False)]
                if getattr(settings, 'JSON_DEBUG', False):
                    log_json('put_request_changed.json', fixtures_python_changed)
                    log_json('put_request_deleted.json', fixtures_python_deleted)
                if not natural_keys:
                    fixtures_python_with_pk = [obj for obj in fixtures_python_changed if 'pk' in obj]
                    fixtures_python_without_pk = [obj for obj in fixtures_python_changed if not 'pk' in obj]
                    fixtures_with_pk = cls.pretreatment_fixtures(initial_obj, fixtures_python_with_pk, walking_classes, sorted_function)
                    fixtures_without_pk = cls.pretreatment_fixtures(initial_obj, fixtures_python_without_pk, walking_classes, sorted_function)
                    contents = cls._deserialize(initial_obj, fixtures_with_pk,
                                                len_fixtures=len(fixtures_python_with_pk), format=format,
                                                walking_classes=walking_classes, using=using,
                                                natural_keys=natural_keys,
                                                exclude_contents=exclude_contents)
                    contents += cls._deserialize(initial_obj, fixtures_without_pk,
                                                 len_fixtures=len(fixtures_python_without_pk), format=format,
                                                 walking_classes=walking_classes, using=using,
                                                 natural_keys=True,
                                                 exclude_contents=exclude_contents)
                else:
                    fixtures = cls.pretreatment_fixtures(initial_obj, fixtures_python_changed, walking_classes, sorted_function)
                    contents = cls._deserialize(initial_obj, fixtures,
                                                len_fixtures=len(fixtures_python_changed), format=format,
                                                walking_classes=walking_classes, using=using,
                                                natural_keys=natural_keys,
                                                exclude_contents=exclude_contents)
                cls.delete_contents(fixtures_python_deleted)
                transaction.commit()
                return contents
            except Exception, e:
                if settings.DEBUG:
                    import traceback
                    logger.error(traceback.format_exc())
                transaction.rollback()
                raise e

    @classmethod
    def pretreatment_fixtures(cls, initial_obj, fixtures_python, walking_classes, sorted_function=None):
        if sorted_function:
            fixtures_python.sort(cmp=sorted_function)
        for obj in fixtures_python:
            app_label, model = obj['model'].split(".")
            model = ContentType.objects.get(model=model, app_label=app_label).model_class()
            meta_walking_class = cls.get_meta_walking_class(model, walking_classes)
            meta_walking_class.pretreatment_fixture(initial_obj, obj)
        return dumps(fixtures_python)

    @classmethod
    def _deserialize(cls, initial_obj, fixtures, len_fixtures, format='json',
                     walking_classes=None, using='default',
                     natural_keys=True,
                     exclude_contents=None, contents=None):
        return cls.deserialize_step(initial_obj, fixtures, len_fixtures=len_fixtures,
                                    format=format, walking_classes=walking_classes, using=using,
                                    natural_keys=natural_keys,
                                    exclude_contents=exclude_contents, contents=contents)

    @classmethod
    def deserialize_step(cls, initial_obj, fixtures, len_fixtures, format='json',
                         walking_classes=None, using='default',
                         natural_keys=True, exclude_contents=None, contents=None):
        objects = serializers.deserialize(format, fixtures, using=using,
                                          use_natural_primary_keys=natural_keys,
                                          use_natural_foreign_keys=natural_keys)
        exclude_contents = exclude_contents or []
        contents = contents or []
        init = True
        obj_does_not_exist = False
        obj = None
        i = 0
        while obj or init:
            init = False
            try:
                obj = objects.next()
                i = i + 1
            except DeserializationError:
                obj_does_not_exist = True
                break
            except StopIteration:
                break
            natural_key = '%s__%s__%s' % (obj.object._meta.app_label,
                                          obj.object._meta.module_name,
                                          obj.object.natural_key())

            if not natural_key in exclude_contents:
                meta_walking_class = cls.get_meta_walking_class(obj.object.__class__, walking_classes)
                meta_walking_class.pre_save(initial_obj, obj.object)
                obj.save(using=using)
                meta_walking_class.post_save(initial_obj, obj.object)
                contents.append(obj.object)
                exclude_contents.append(natural_key)
        if obj_does_not_exist:
            fixtures_python = simplejson.loads(fixtures)
            fix_obj = fixtures_python[i]
            fixtures_python = fixtures_python[i + 1:]
            fixtures_python.append(fix_obj)
            fixtures = dumps(fixtures_python)
            cls._deserialize(initial_obj, fixtures, len_fixtures=len_fixtures, format=format,
                             walking_classes=walking_classes,
                             natural_keys=natural_keys,
                             exclude_contents=exclude_contents,
                             contents=contents)
        return contents

    @classmethod
    def delete_contents(cls, fixtures):
        cts = {}
        for obj_fix in fixtures:
            app_model = obj_fix['model']
            if not app_model in cts:
                cts[app_model] = []
            cts[app_model].append(obj_fix['pk'])
        for app_model, pks in cts.items():
            app_label, model = obj_fix['model'].split('.')
            ct = ContentType.objects.get(app_label=app_label, model=model)
            model_class = ct.model_class()
            model_class.objects.filter(pk__in=pks).delete()
