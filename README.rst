.. contents::

======================
django-deep-serializer
======================

.. image:: https://travis-ci.org/goinnn/django-deep-serializer.png?branch=master
    :target: https://travis-ci.org/goinnn/django-deep-serializer

.. image:: https://coveralls.io/repos/goinnn/django-deep-serializer/badge.png?branch=master
    :target: https://coveralls.io/r/goinnn/django-tables2-reports

.. image:: https://badge.fury.io/py/django-deep-serializer.png
    :target: https://badge.fury.io/py/django-deep-serializer

.. image:: https://pypip.in/d/django-deep-serializer/badge.png
    :target: https://pypi.python.org/pypi/django-deep-serializer

With django-deep-serializer you can serialize/deserialize an object and its relations through class definitions

Requeriments
============

* `django <http://pypi.python.org/pypi/django/>`_ (>=1.4, it's possible that works with previous versions)


Installation
============

* If you want use natural keys, you have use the `internal serializers <https://github.com/goinnn/django-deep-serializer/commit/35190702bbd00324a1bb526a2aa842405e241bd3>`_ These are get from django git repository. These are not in the never stable branch or release. You have to write in your settings:

::

    SERIALIZATION_MODULES = {
        "xml"    : "deep_serializer.serializers.xml_serializer",
        "python" : "deep_serializer.serializers.python",
        "json"   : "deep_serializer.serializers.json",
        #"yaml"   : "deep_serializer.serializers.pyyaml",
    }

Use cases
=========

* Serialize (using primary keys or natural keys) an object and its relations
* Deserialize (using primary keys or natural keys) some objects
* Clone (using natural keys) an object. To do you can serialize, update the natural key to the main object and after deserialize these objects
* Restore an object with its relations, (using primary keys or natural keys)

How to use
==========

The idea is get to have a serializer and a deserializer that this allow define some rules with a very few lines.
There are three examples in the `example project <https://github.com/goinnn/django-deep-serializer/blob/master/example/example/app/serializer.py>`_. E.g.:

::
    class WebSiteClone(MyMetaWalkClass):

        @classmethod
        def pre_serialize(cls, initial_obj, obj, request, options=None):
            obj = super(WebSiteClone, cls).pre_serialize(initial_obj, obj, request, options=options)
            new_title = '%s-%s' % (obj.title, time.time())
            obj.title = new_title[:200]
            obj.slug = hash_slug()
            obj.original_website_id = obj.pk
            obj.initial_page = None
            return obj

        @classmethod
        def walking_into_class(cls, obj, field_name, model):
            if field_name in ('initial_page', 'websites_created_of'):
                return WALKING_STOP
            elif field_name in ('original_website', 'owners'):
                return ONLY_REFERENCE
            return WALKING_INTO_CLASS


    class PageClone(MyMetaWalkClass):

        @classmethod
        def pre_serialize(cls, initial_obj, obj, request, options=None):
            obj = super(PageClone, cls).pre_serialize(initial_obj, obj, request, options=options)
            obj.website = initial_obj
            obj.created_from_id = obj.pk
            return obj

        @classmethod
        def walking_into_class(cls, obj, field_name, model):
            if field_name in ('pages_created_of', 'website'):
                return WALKING_STOP
            elif field_name in ('created_from'):
                return ONLY_REFERENCE
            return WALKING_INTO_CLASS

        @classmethod
        def post_save(cls, initial_obj, obj):
            super(PageClone, cls).post_save(initial_obj, obj)
            initial_page = obj.created_from.website.initial_page
            if initial_page and obj.slug == initial_page.slug:
                obj.website.initial_page = obj
                obj.website.save()


Test project
============

In the source tree, you will find a directory called 'example'. It contains
a readily setup project that uses django-deep-serializer. You can run it as usual:

::

    python manage.py syncdb
    python manage.py runserver
