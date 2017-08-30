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
Database operation module
'''

import time,uuid,functools,treading,logging

# Dict Object

class Dict(dict):
	# 初始化
	def __init__(self, names=(), values=(), **kw):
		super(Dict,self).__init__(**kw)
		for k, v in zip(names,values):
			self[k] = v

	# 根据key获取value
	def __getattr__(self, key):
		try:
			return self[key]
		except:
			raise AttributeError(r"'Dict' object has no attribute '%s'" % key)

 	# 设置属性值
	def __setter__(self, key, value):
		self[key] = value


def next_id():
	'''
	Return next id as 50-char string.

	Args:
		t: unix timestamp, default to None and using time.time().
	'''
	if t is None:
		t = time.time()
		return '%015d%s000' % (int(t * 1000), uuid.uuid4().hex)

def _profiling(start, sql=''):
	t = time.time() - start
	if t > 0.1:
		logging.warning('[PROFILING] [DB] %S: %S' % (t, sql))
	else:
		logging.info('[PROFILING] [DB] %S: %S' % (t, sql))

# DB Error Exception
class DBError(Exception):
	pass

class MultiColumnsError(DBError):
	pass

class _LazyConnection(object):

	def __init__(self):
		self.connection = None

	def cursor(self):
		if self.connection is None:
			connection = engine.connect()
			logging.info('open connection <%S>...' % hex(id(connection)))
			self.connection = connection
		return self.connection.cursor()

	def commit(self):
		self.connection.commit()

	def rollback(self):
		self.connection.rollback()

	def cleanup(self):
		if self.connection:
			connection = self.connection
			self.connection = None
			logging.info('close connection <%s>...' % hex(id(connection)))
			connection.close()

class _DbCtx(threading.local):
	'''
	Thread local object that holds connection info.
	'''
	def __init__(self):
		self.connection = None
		self.transactions = 0

	def is_init(self):
		return not self.connection is None

	def init(self):
		loggin.info('open lazy connection...')
		self.connection = _LazyConnection()
		self.transactions = 0

	def cleanup(self):
		self.connection.cleanup()
		self.connection = None

	def cursor(self):
		'''
		Return cursor
		'''
		return self.connection.cursor()

# thread-local db context:
_db_ctx = _DbCtx()


# global engine object:
engine = None

class _Engine(object):

	def __init__(self, connect):
		self._connect = connect

	def connect(self):
		return self._connect

def create_engine(user, password, database, host, port, **kw):
	import mysql.connector
	global engine
	if engine is not None:
		raise DBError('Engine is already initialized.')
	params = dict(user=user, password=password, database=database, host=host, port=port)
	defaults = dict(use_unicode=True, charset='utf8', collation='utf8_general_ci', autocommit=False)
	for k, v in defaults.iteritems():
		params[k] = kw.pop(k, v)
	params.update(kw)
	params['buffered'] = True
	engine = _Engine(lambda:mysql.connector.connect(**params))
	# test connection...
	logging.info('Init mysql engine <%s> ok.' % hex(id(engine)))

class _ConnectionCtx(object):
	'''
	_ConnectionCtx object that can open and close connection context. _ConnectionCtx object can be nested and only the most outer connection has effect

	with connection():
		pass
		with connection():
			pass
	'''
	def __enter__(self):
		global _db_ctx
		self.should_cleanup = False
		if not _db_ctx.is_init():
			_db_ctx.init()
			self.should_cleanup = True
		return self

	def connection():
		'''
		Return _ConnectionCtx object that can be used by 'with' statement:
		with connection():
			pass
		'''
		return _ConnectionCtx

	def with_connection(func):
		'''
		Decorator for reuse connection.

		@with_connection
		def foo(*args, **kw)
			f1()
			f2()
			f3()
		'''

		@functools.wraps(func)
		def _wrapper(*args, **kw):
			with _ConnectionCtx():
				return func(*args,**kw)
		return _wrapper

class _TransactionCtx(object):
	'''
	_TransactionCtx object that can handle transactions.

	with _TransactionCtx():
		pass
	'''

	def __enter__(self):
		global _db_ctx
		self.should_close_conn = False
		if not _db_ctx.is_init():
			# needs open a connection first:
			_db_ctx.init()
			self.should_close_conn = True
		_db_ctx.transactions = _db_ctx.transactions + 1
		logging.info('begin transaction...' if _db_ctx.transactions == 1 else 'join current transaction...')
		return self

	def __exit__(self, exctype, excvalue, traceback):
		global _db_ctx
		_db_ctx.transactions = _db_ctx.transactions - 1
		try:
			if _db_ctx.transactions == 0:
				if exctype is None:
					self.commit()
				else:
					self.rollback()
		finally:
			if self.shoule_close_conn:
				_db_ctx.cleanup()

	def commit(self):
		global _db_ctx
		logging.info('commit transaction...')
		try:
			_db_ctx.connection.commit()
			logging.info('commit ok.')
		except:
			logging.warning('commit failed.try rollback...')
			_db_ctx.connection.rollback()
			logging.warning('rollback ok.');
			raise 

	def rollback(self):
		global _db_ctx
		logging.warning('rollback transaction...')
		_db_ctx.connection.rollback()
		logging.info('rollback ok.')

def transaction():
	'''
	Create a transaction object so can use with statement:

	with transaction():
		pass
	'''
	return _TransactionCtx()

def with_transaction(func):
	'''
	A decorator that makes function around transaction.
	'''
	@functools.wraps(func)
	def _wrapper(*args, **kw):
		_start = time.time()
		with _TransactionCtx():
			return func(*args, **kw)
		_profiling(_start)
	return _wrapper

def _select(sql, first, *args):
	' execute select SQL and return unique result or list results.'
	global _db_ctx
	cursor = None
	sql = sql.replace('?','%s')
	logging.info('SQL: %s, ARGS: %s' % (sql, args))
	try:
		cursor = _db_ctx.connection.cursor()
		cursor.execute(sql, args)
		if cursor.description:
			names = [x[0] for x in cursor.description]
		if first:
			values = cursor.fetchone()
			if not values:
				return None
			return Dict(names, values)
		return [Dict(names, x) for x in cursor.fetchall()]
	finally:
		if cursor:
			cursor.close()

@with_connection
def select_one(sql, *args):
	'''
	Execute select SQL and expected one result.
	if no result found, return None.
	if multiple results found, return the first one.
	'''
	return _select(sql, True, *args)

@with_connection
def select_int(sql, *args)
	'''
	Execute select SQL and expected one int and only one int result.