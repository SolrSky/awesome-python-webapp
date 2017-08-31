#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date    : 2017-08-26 14:10:07
# @Author  : djj (295846891@qq.com)
# @Link    : ${link}
# @Version : $Id$

__author__ = "SolrSky"

import sys

reload(sys)
sys.setdefaultencoding('utf-8')

'''
Database operation module. This module is independent with web moudle.
'''

import time, logging

import db

class Field(object):

	_count = 0
	"""docstring for Field"""
	def __init__(self, **kw):
		self.name = kw.get('name', None)
		self._default = kw.get('default', None)
		self.primary_key = kw.get('primary_key', None)
		self.nullable = kw.get('nullable', None)
		self.updatable = ke.get('updatable', None)
		self.insertable = kw.get('insertable', None)
		self.ddl = kw.get('ddl', '')
		self._order = Field._count
		Field._count = Field._count + 1

	@property
	def default(self):
		d = self._default
		return d() if callable(d) else d
		
	def __str__(self):
		s = ['<%s:%s,%s,default(%s),' % (self.__class__.__name__, self.name, self.ddl, self._default)]
		self.nullable and s.append('N')
		self.updatable and s.append('U')
		self.insertable and s.append('I')
		s.append('>')
		return ''.join(s)

class StringField(Field):
	"""docstring for StringField"""
	def __init__(self, **kw):
		if not 'default' in kw:
			kw['default'] = ''
		if not 'ddl' in kw:
			kw['ddl'] = 'varchar(225)'
		super(StringField, self).__init__(**kw)

class IntegerField(Field):
	"""docstring for IntegerField"""
	def __init__(self, **kw):
		if not 'default' in kw:
			kw['default'] = 0
		if not 'ddl' in kw:
			kw['ddl'] = 'bigint'
		super(IntegerField, self).__init__(**kw)
		
class FloatField(Field):
	"""docstring for FloatField"""
	def __init__(self, **kw):
		if not 'default' in kw:
			kw['default'] = 0.0
		if not 'ddl' in kw:
			kw['ddl'] = 'real'
		super(FloatField, self).__init__(**kw)
		
class BooleanField(Field):
	"""docstring for BooleanField"""
	def __init__(self, **kw):
		if not 'default' in kw:
			kw['default'] = False
		if not 'ddl' in kw:
			kw['ddl'] = 'bool'
		super(BooleanField, self).__init__(**kw)

class TextField(Field):
	"""docstring for TextField"""
	def __init__(self, **kw):
		if not 'default' in kw:
			kw['default'] = ''
		if not 'ddl' in kw:
			kw['ddl'] = 'text'
		super(TextField, self).__init__(**kw)

class BlobField(Field):
	"""docstring for BlobField"""
	def __init__(self, **kw):
		if not 'default' in kw:
			kw['default'] = ''
		if not 'ddl' in kw:
			kw['ddl'] = 'blob'
		super(BlobField, self).__init__(**kw)

class VersionField(Field):
	"""docstring for VersionField"""
	def __init__(self, name=None):
		super(VersionField, self).__init__(name=name, default=0, ddl='bigint')
		
_triggers = frozenset(['pre_insert', 'pre_update', 'pre_delete'])

def _gen_sql(table_name, mappings):
	pk = None
	sql = ['-- generating SQL for %s:' % table_name, 'create table `%s` (' %table_name]
	for f in sorted(mappings.values(), lambda x, y: cmp(x._order, y._order)):
		if not hasattr(f, 'ddl'):
			raise StandardError('no ddl in field "%s".' % n)
		ddl = f.ddl
		nullable = f.nullable
		if f.primary_key:
			pk = f.name
		sql.append(nullable and '  `%s` %s,' % (f.name, ddl) or '  `%s` %s not null,' % (f.name, ddl))
	sql.append('  primary key(`%s`)' % pk)
	sql.append(');')
	return '\n'.join(sql)

class ModelMetaclass(type):
	'''
	Metaclass for model objects.
	'''
	def __new__(cls, name, bases, attrs):
		# skip base Model class:
		if name == 'Model':
			return type.__new__(cls,name,bases,attrs)

		# store all subclasses info:
		if not hasattr(cls, 'subclasses'):
			cls.subclasses = {}
		if not name in cls.subclasses:
			cls.subclasses[name] = name
		else:
			logging.warning('Redefine class: %s' % name)

		logging.info('Scan ORMapping %s...' % name)
		mappings = dict()
		primary_key = None
		for k, v in attrs.iteritems():
			if isinstance(v, Field):
				if not v.name:
					v.name = k
				logging.info('Found mapping: %s => %s' % (k, v))
				# check duplicate primary key:
				if v.primary_key:
					if primary_key:
						raise TypeError('Cannot define more than 1 primary key in class: %s' % name)
					if v.updatable:
						logging.warning('NOTE: change primary key to non-updatable.')
						v.updatable = False
					if v.nullable:
						logging.warning('NOTE: change primary key to non-nullable')
						v.nullable = False
					primary_key = v
				mappings[k] = v
		# check exist of primary key:
		if not primary_key:
			raise TypeError('Primary key not defined in class: %s' % name)
		for k in mappings.iterkeys():
			attrs.pop(k)
		if not '__table__' in attrs:
			attrs['__table__'] = name.lower()
		attrs['__mappings__'] = mappings
		attrs['__primary_key__'] = primary_key
		attrs['__sql__'] = lambda self: _gen_sql(attrs['__table__'], mappings)
		for trigger in _triggers:
			if not trigger in attrs:
				attrs[trigger] = None
		return type.__new__(cls, name, bases, attrs)

class Model(dict):
	'''
	Base class for ORM.
	'''
	__metaclass__ = ModelMetaclass

	def __init__(self, **kw):
		super(Model, self).__init__(**kw)

	def __getattr__(self, key):
		try:
			return self[key]
		except KeyError:
			raise AttributeError(r"'Dict' object has no attribute '%s'" % key)

	def __setattr__(self, key, value):
		self[key] = value

	