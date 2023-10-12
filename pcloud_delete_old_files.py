#!/usr/bin/python3
# -*- coding: utf-8 -*-

import requests
import sys
from datetime import datetime
import time

def pcloud_delete_old_files(camera_dir):
    pcloud_url = 'https://eapi.pcloud.com/'

        # create dir
    pcloud_method = 'listfolder'
    mth_params = {
        'path' : '/CCTV/' + camera_dir,
        #'name' : camera_dir,
        'username' : 'co*****ex.ru',
        'password' : '*******'
    } 
    r = requests.get(url = pcloud_url + pcloud_method, params = mth_params) 
    if r.json()['result'] != 0:
        print("error:", r.json())
        return
    
    for f in r.json()['metadata']['contents']:
            # Fri, 06 Nov 2020 03:24:21 +0000
        date_dt1 = datetime.strptime(f['created'], '%a, %d %b %Y %H:%M:%S %z')
        delta = time.time() - date_dt1.timestamp()
        if delta > 60*60*24*5:
            pcloud_method2 = 'deletefile'
            mth_params2 = {
                'fileid' : f['id'],
                'path' : f['path'],
                'username' : 'corlov@yandex.ru',
                'password' : 'manarstot'
            } 
            r2 = requests.get(url = pcloud_url + pcloud_method2, params = mth_params2)
            print (str(r2.json()['result']) + ' delete: ' + f['name'])

    
        
pcloud_delete_old_files('cam_1')
pcloud_delete_old_files('cam_2')
pcloud_delete_old_files('cam_3')
pcloud_delete_old_files('cam_4')
pcloud_delete_old_files('cam_5')

