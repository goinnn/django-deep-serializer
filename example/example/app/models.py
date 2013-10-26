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
from django.db import models
from django.utils.translation import ugettext_lazy as _


from example.app.managers import WebSiteManager, PageManager


class WebSite(models.Model):

    title = models.CharField(verbose_name=_('Title'), max_length=200)
    # http://en.wikipedia.org/wiki/Domain_Name_System#Domain_name_syntax
    slug = models.SlugField(verbose_name=_('Slug'), unique=True, db_index=True, max_length=63)
    owners = models.ManyToManyField(User, verbose_name=_('Owner'))
    is_active = models.BooleanField(verbose_name=_('Is active?'), db_index=True, default=True)
    original_website = models.ForeignKey('self', related_name='websites_created_of',
                                         verbose_name=_('Original WebSite'),
                                         null=True, blank=True,
                                         on_delete=models.SET_NULL)
    initial_page = models.OneToOneField('Page', related_name='website_initial_page',
                                        verbose_name=_('Initial Page'),
                                        null=True, blank=True,
                                        on_delete=models.SET_NULL)
    creation_date = models.DateTimeField(verbose_name=_('Creation date'), auto_now_add=True)
    modification_date = models.DateTimeField(verbose_name=_('Last Modification date'), auto_now=True)
    objects = WebSiteManager()

    class Meta:
        verbose_name = _('WebSite')
        verbose_name_plural = _('WebSites')
        ordering = ['title']

    def natural_key(self):
        return (self.slug,)

    def __str__(self):
        return self.slug

    def __unicode__(self):
        return self.__str__()


class Page(models.Model):

    title = models.CharField(verbose_name=_('Title'), max_length=200)
    slug = models.SlugField(verbose_name=_('Slug'), db_index=True, max_length=200)
    html_code = models.TextField(verbose_name=_('HTML code'), blank=True)
    website = models.ForeignKey(WebSite, verbose_name=_('WebSite'))
    created_from = models.ForeignKey('self', related_name='pages_created_of',
                                     verbose_name=_('Created from'), null=True, blank=True,
                                     on_delete=models.SET_NULL)
    creation_date = models.DateTimeField(verbose_name=_('Creation date'), auto_now_add=True)
    modification_date = models.DateTimeField(verbose_name=_('Last Modification date'), auto_now=True)

    objects = PageManager()

    class Meta:
        verbose_name = _('Page')
        verbose_name_plural = _('Pages')
        unique_together = ('slug', 'website')

    def natural_key(self):
        return self.website.natural_key() + (self.slug, )

    def __str__(self):
        return "%s -- %s" % (str(self.website), self.slug)

    def __unicode__(self):
        return self.__str__()
