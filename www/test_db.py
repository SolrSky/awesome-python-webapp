#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date    : 2017-08-26 14:10:07
# @Author  : djj (295846891@qq.com)
# @Link    : ${link}
# @Version : $Id$

__author__ = "SolrSky"

from models import User, Blog, Comment
from transwarp import  db


db.create_engine(user='www-data', password='www-data', database='awesome', host='localhost', port='3306')

u = User(name='Test', email='test@example.com', password='123456', image='http://img.qfc.cn/upload/01/certificate/02/0d/705808.jpg')

u.insert()

print "new user id:", u.id

u1 = User.find_first('where email=?', 'test@example.com')

print 'find user\'s name:', u1.name

u1.delete()

u2 = User.find_first('where email=?', 'test@example.com')

print 'find user:', u2

