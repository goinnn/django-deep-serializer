from django.contrib.auth.models import User

from deep_serializer import Serializer, BaseMetaWalkClass

from example.app.models import WebSite, Page
from example.app.serializer import (WebSiteClone, PageClone,
                                    WebSiteRestore, PageRestore)

walking_clone_classes = {WebSite: WebSiteClone,
                         Page: PageClone,
                         User: BaseMetaWalkClass}

walking_restore_classes = {WebSite: WebSiteRestore,
                           Page: PageRestore,
                           User: BaseMetaWalkClass}


def serialize_website(website, clone=True):
    if clone:
        walking_classes = walking_clone_classes
        natural_keys = True
    else:
        walking_classes = walking_restore_classes
        natural_keys = False
    return Serializer.serialize(website, request=None,
                                walking_classes=walking_classes,
                                format='json',
                                indent=4,
                                natural_keys=natural_keys)


def deserialize_website(website, fixtures, clone=True):
    if clone:
        walking_classes = walking_clone_classes
        natural_keys = True
    else:
        walking_classes = walking_restore_classes
        natural_keys = False
    return Serializer.deserialize(website, fixtures,
                                  format='json',
                                  walking_classes=walking_classes,
                                  natural_keys=natural_keys)


def clone_website(website):
    fixtures = serialize_website(website, clone=True)
    return deserialize_website(website, fixtures, clone=True)
