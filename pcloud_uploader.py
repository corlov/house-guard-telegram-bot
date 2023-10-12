#!/usr/bin/python3
# -*- coding: utf-8 -*-

import imutils
import cv2
import numpy as np
import os
import time
from time import gmtime, strftime
import redis
import sys
from datetime import datetime
import traceback
import requests
import linecache

RQUEUE_IMG_PCLOUD_UPLOAD_FILE = 'RQUEUE_IMG_PCLOUD_UPLOAD_FILE'
RQUEUE_IMG_PCLOUD_UPLOAD_DIR = 'RQUEUE_IMG_PCLOUD_UPLOAD_DIR'
R = redis.Redis(host='127.0.0.1', port=6379, db=0)


   


def pcloud_upload_next():
    sys_file_name = str(R.lpop(RQUEUE_IMG_PCLOUD_UPLOAD_FILE).decode('utf8'))
    camera_dir =    str(R.lpop(RQUEUE_IMG_PCLOUD_UPLOAD_DIR).decode('utf8'))
    
    pcloud_url = 'https://eapi.pcloud.com/'

        # create dir
    pcloud_method = 'createfolderifnotexists'
    mth_params = {
        'path' : '/CCTV/' + camera_dir,
        'name' : camera_dir,
        'username' : 'user',
        'password' : '********'
    } 
    r = requests.get(url = pcloud_url + pcloud_method, params = mth_params) 
    if r.json()['result'] != 0:
        print("error:", r.json())
        return

        # upload
    files = { 'file_name' : open( sys_file_name, 'rb') }
    data = {
        'path' : '/CCTV/'+camera_dir, 
        'username': 'cor******x.ru', 
        'password': '*****'
    }
    pcloud_method = 'uploadfile'
    r = requests.post(pcloud_url + pcloud_method, files=files, data=data)
    if r.json()['result'] != 0:
        print("error:", r.json())
        return


        
if __name__ == '__main__':
    while(1):
        if R.llen(RQUEUE_IMG_PCLOUD_UPLOAD_FILE) == 0: 
            print('wait...')
            time.sleep(1)
            continue
        else:
            pcloud_upload_next()
            print('uploaded')

        
        
