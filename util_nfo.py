# -*- coding: utf-8 -*-
# python
import os, traceback, time, json

# third-party
import requests
from flask import Blueprint, request, send_file, redirect

# sjva 공용
from framework import app, path_data, check_api, py_urllib, SystemModelSetting
from framework.logger import get_logger
from framework.util import Util


from .plugin import P
logger = P.logger


class UtilNfo(object):

    @classmethod
    def make_nfo_movie(cls, info):
        try:
            logger.debug('make nfo movie')
        except Exception as exception: 
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())
    
    