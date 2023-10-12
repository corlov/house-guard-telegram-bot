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
import psycopg2
from datetime import datetime
import struct
import configparser
import traceback
import requests
import linecache


p = configparser.RawConfigParser()
p.read('/root/house_guard/guard_system.conf')
cam_name = os.path.dirname(os.path.realpath(__file__)).split('/')[-1]

#       -= SYSTEMD =-   
                        #cd /etc/systemd/system/
                        #vim /etc/systemd/system/motion_detector.service
                        #
                        #systemctl start motion_detector
                        #systemctl stop motion_detector
                        #
                        #systemctl disable motion_detector
                        #systemctl enable motion_detector
                        #
                        #systemctl status motion_detector.service



BotToken = p.get('telegram_bot', 'BotToken') #'1209017671:AAH8evw44Tlf-eTtIXGwiOCklqiNOa0r3XA'
ChatId = p.get('telegram_bot', 'ChatId')     # '-444235704'


#R = redis.Redis(host='127.0.0.1', port=6379, db=0)
R = redis.Redis(host=p.get('redis_db', 'host'), port=p.get('redis_db', 'port'), db=p.get('redis_db', 'db'))

DB_USR = p.get('db', 'DB_USR') #'hc625ma'
DB_PWD = p.get('db', 'DB_PWD') #'qwe123#' 
DB_NAME = p.get('db', 'DB_NAME') # 'house_cctv'


    # settings:
DB_CAMERA_ID = p.get(cam_name, 'DB_CAMERA_ID') #2
CAMERA_DESCR = p.get(cam_name, 'CAMERA_DESCR')
CAM_ADDR = p.get(cam_name, 'CAM_ADDR') #'172.16.78.253'
CAM_PORT = p.get(cam_name, 'CAM_PORT') #'172.16.78.253'
SRC_VIDEO_STREAM = p.get(cam_name, 'SRC_VIDEO_STREAM') # 'rtsp://'+CAM_ADDR+':11554/user=admin_password=_channel=1_stream=0.sdp'
HOME_DIR = p.get(cam_name, 'HOME_DIR') #'/root/house_guard/cam_2/'

CAMERA_FPS = int(p.get(cam_name, 'CAMERA_FPS'))

MIN_RATIO_BOUND = float(p.get(cam_name, 'min_ratio'))
MAX_RATIO_BOUND = float(p.get(cam_name, 'max_ratio'))

ROI_X1 = int(p.get(cam_name, 'x1'))
ROI_X2 = int(p.get(cam_name, 'x2'))
ROI_Y1 = int(p.get(cam_name, 'y1'))
ROI_Y2 = int(p.get(cam_name, 'y2'))



DB_MSG_TYPE_ALARM = 1
DB_MSG_TYPE_SERVICE = 2
DB_MSG_TYPE_ERR = 3

RKEY_IMG_4_VERIFY =  'image_for_verify' + str(DB_CAMERA_ID)
RQUEUE_NAME_IMG_4_VERIFY =  'queue_image_for_verify_' + str(DB_CAMERA_ID)

    # Number of frames to pass before changing the frame to compare the current
    # frame against
    # как часто обновляем фрейм-бекграунд
FRAMES_TO_PERSIST = CAMERA_FPS * 60

    # Minimum boxed area for a detected motion to count as actual motion
    # Use to filter out noise or small objects
#MIN_SIZE_FOR_MOVEMENT = 2000
MIN_SIZE_FOR_MOVEMENT = int(p.get(cam_name, 'MIN_CNTR_SIZE'))

    # Minimum length of time where no motion is detected it should take
    #(in program cycles) for the program to declare that there is no movement
MOVEMENT_DETECTED_PERSISTENCE = 100


DEBUG_MODE = False
STORAGE_DIR = HOME_DIR + 'storage/'


def logmsg(msg_text):
    cur_time = datetime.now().strftime("[%m.%d.%Y %H:%M:%S]     ")
    print(cur_time + msg_text)
    f = open(HOME_DIR + "guard.log", "a")  # write mode 
    f.write(cur_time + msg_text + "\n") 
    f.close() 
    
    
    

def PrintException():
    exc_type, exc_obj, tb = sys.exc_info()
    f = tb.tb_frame
    lineno = tb.tb_lineno
    filename = f.f_code.co_filename
    linecache.checkcache(filename)
    line = linecache.getline(filename, lineno, f.f_globals)
    return 'EXCEPTION IN ({}, LINE {} "{}"): {}'.format(filename, lineno, line.strip(), exc_obj)
    
    

def pcloud_upload(camera_dir, sys_file_name):
    RQUEUE_IMG_PCLOUD_UPLOAD_FILE = 'RQUEUE_IMG_PCLOUD_UPLOAD_FILE'
    RQUEUE_IMG_PCLOUD_UPLOAD_DIR = 'RQUEUE_IMG_PCLOUD_UPLOAD_DIR'
    R.lpush(RQUEUE_IMG_PCLOUD_UPLOAD_FILE, sys_file_name)
    R.lpush(RQUEUE_IMG_PCLOUD_UPLOAD_DIR, camera_dir)
    return
    
    pcloud_url = 'https://eapi.pcloud.com/'

        # create dir
    pcloud_method = 'createfolderifnotexists'
    mth_params = {
        'path' : '/CCTV/' + camera_dir,
        'name' : camera_dir,
        'username' : 'corlov@yandex.ru',
        'password' : 'manarstot'
    } 
    r = requests.get(url = pcloud_url + pcloud_method, params = mth_params) 
    if r.json()['result'] != 0:
        print("error:", r.json())
        return

        # upload
    files = { 'file_name' : open( sys_file_name, 'rb') }
    data = {
        'path' : '/CCTV/'+camera_dir, 
        'username': 'corlov@yandex.ru', 
        'password': 'manarstot'
    }
    pcloud_method = 'uploadfile'
    r = requests.post(pcloud_url + pcloud_method, files=files, data=data)
    if r.json()['result'] != 0:
        print("error:", r.json())
        return


def write_2_db(msg_text, msg_type):
    try:
        conn = psycopg2.connect(user = DB_USR,password = DB_PWD,host = "127.0.0.1",port = "5432",database = DB_NAME)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO message (ts, camera_id, msg_text, msg_type_id) VALUES (%s,%s,%s,%s)", 
            (datetime.now(), DB_CAMERA_ID, msg_text, msg_type, ) 
        )
        conn.commit()
        cur.close()
    except (Exception, psycopg2.Error) as error :
        print ("Error while connecting to PostgreSQL", error)
    finally:
        if(conn):
            cur.close()
            conn.close()
            
            



def ping_host(addr, port):
    response = os.system("nc " + str(addr) + " " + str(port) + " -zv ")
    if response == 0:
        return True
    else:
        return False
    #ping_k = 0
    #while ping_k < 10:
        #response = os.system("ping -c 1 " + addr)
        #if (response == 0):
        #    return True 
        #ping_k += 1
    #return False
    
    
    
def send_text_telegram(text):
    text = "Камера " + str(DB_CAMERA_ID) + " (" + CAMERA_DESCR + "), " + text
    os.system('curl -X POST "https://api.telegram.org/bot'+BotToken+'/sendMessage" -d "chat_id='+ChatId+'&text=' + text + '" &')
  
  
  
def check_camera_accessibility(addr, port, cur_guard_state):
    if not ping_host(addr, port):
        if cur_guard_state:
            send_text_telegram('Камера недоступна')
            write_2_db('Камера недоступна', DB_MSG_TYPE_ERR)
            R.set('guard_active', 0)
            R.set('prev_guard_active', 0)
        
        print("\n\nCamera unavailable")
        sys.exit()
        


def toRedis(r, redis_queue_name, img):
   h, w = img.shape[:2]
   shape = struct.pack('>II',h,w)
   encoded = shape + img.tobytes()
   #print (encoded)
   #r.set(redis_key, encoded)
   r.lpush(redis_queue_name, encoded)
   
   
   
def fromRedis(r, redis_key):
   """Retrieve Numpy array from Redis key 'n'"""
   encoded = r.get(redis_key)
   #print (encoded)
   h, w = struct.unpack('>II',encoded[:8])
   img = np.frombuffer(encoded, dtype=np.uint8, offset=8).reshape(h,w,3)
   return img
   
   


if __name__ == '__main__':
    os.system('mkdir -p ' + STORAGE_DIR + '/' + str(DB_CAMERA_ID))
    write_2_db('запуск демона видеонаблюдения', DB_MSG_TYPE_SERVICE)
    
    if (ROI_X1 >= ROI_X2) or (ROI_Y1 >= ROI_Y2):
        print("roi size error")
        sys.exit()
        
    cur_video_fname = ''
        # Init frame variables
    bkg_frame = None
    next_frame = None
    delay_counter = 0
    
    
        # buffer for previous frames
    PrevFramesList = []
    
    
    # guard_state = 1
    # if R.get('guard_active'):
        # guard_state = int(R.get('guard_active'))
    # else:
        # R.set('guard_active', 1)
        
    # prev_guard_state = guard_state
    # if R.get('prev_guard_active'):
        # prev_guard_state = int(R.get('prev_guard_active'))
        
    # check_camera_accessibility(CAM_ADDR, guard_state)

    if not ping_host(CAM_ADDR, CAM_PORT):
        send_text_telegram("Камера (" + CAMERA_DESCR + ") недоступна по сети")
        write_2_db("Камера недоступна по сети", DB_MSG_TYPE_ERR)
        time.sleep(5)
        

    cap = cv2.VideoCapture(SRC_VIDEO_STREAM)
    ret,inp_image = cap.read()
    video_h, video_w, depth = inp_image.shape
    vout = None
    vout_alarm = None
    if DEBUG_MODE:
        vout = cv2.VideoWriter(HOME_DIR + 'result_motion_detection.avi', cv2.VideoWriter_fourcc(*'XVID'), 1, (video_w, video_h), True)
    
    

    acc = 0
    hit_in_a_row_threshold = int(p.get(cam_name, 'hit_in_a_row_threshold'))
    BUSY = False
    
    frame_no = 0
    frame_read_trouble_count = 0
    while True:
        try:
            frame_no += 1
            ret, frame = cap.read()
                # If there's an error in capturing
            if not ret:
                #print("CAPTURE ERROR")
                #write_2_db("CAPTURE ERROR", 2)
                frame_read_trouble_count += 1
                if frame_read_trouble_count > 10:
                    logmsg("frame_read_trouble_count")
                    if not ping_host(CAM_ADDR, CAM_PORT):
                        logmsg("Камера (" + CAMERA_DESCR + ") недоступна по сети")
                        send_text_telegram("Камера недоступна по сети")
                    sys.exit()
                continue
            frame_read_trouble_count = 0

            frame_virgin = frame
            if (frame_no % 10 == 0):
                cv2.imwrite(HOME_DIR + 'snapshot.png', frame)
            frame = frame[ROI_Y1:ROI_Y2, ROI_X1:ROI_X2]
            
            # guard_state = int(R.get('guard_active'))
            
            # if not guard_state:
                # if prev_guard_state:
                    # send_text_telegram('Подтверждение выключения охраны')
                    # write_2_db('Подтверждение выключения охраны', 2)
                    
                # print("guard was deactivated")
                # prev_guard_state = guard_state
                # R.set('prev_guard_active', prev_guard_state)
                # time.sleep(1)
                # continue
            # else:
                # if guard_state and not prev_guard_state:
                    # send_text_telegram('Подтверждение включения охраны')
                    # write_2_db('Подтверждение включения охраны', 2)
                        # перезапускаем
                    # check_camera_accessibility(CAM_ADDR, guard_state)
                    # frame_no = 0
                    # cap = cv2.VideoCapture(SRC_VIDEO_STREAM)
                    # ret,inp_image = cap.read()
                    # video_h, video_w, depth = inp_image.shape
                    
            # prev_guard_state = guard_state
            # R.set('prev_guard_active', prev_guard_state)
                
            
            
            PrevFramesList.append(frame)
            if len(PrevFramesList) > hit_in_a_row_threshold*2:
                PrevFramesList.pop(0)
            
            
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Blur it to remove camera noise (reducing false positives)
            gray = cv2.GaussianBlur(gray, (21, 21), 0)

            # If the first frame is nothing, initialise it
            if bkg_frame is None: bkg_frame = gray    

            delay_counter += 1

                # Otherwise, set the first frame to compare as the previous frame
                # But only if the counter reaches the appriopriate value
                # The delay is to allow relatively slow motions to be counted as large
                # motions if they're spread out far enough
            if delay_counter > FRAMES_TO_PERSIST:
                delay_counter = 0
                bkg_frame = next_frame

                # Set the next frame to compare (the current frame)
            next_frame = gray

                # Compare the two frames, find the difference
            frame_delta = cv2.absdiff(bkg_frame, next_frame)
            #thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]
            #thresh = cv2.threshold(frame_delta, 80, 255, cv2.THRESH_BINARY)[1]
            #thresh = cv2.threshold(frame_delta, 50, 255, cv2.THRESH_BINARY)[1]
            thresh = cv2.threshold(frame_delta, 40, 255, cv2.THRESH_BINARY)[1]

                # Fill in holes via dilate(), and find contours of the thesholds
            thresh = cv2.dilate(thresh, None, iterations = 2)
            #cnts, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cnts, _ = cv2.findContours(thresh.copy(), cv2.RETR_LIST, method=cv2.CHAIN_APPROX_TC89_KCOS)
            

            smth_detected_in_frame = False
            for c in cnts:
                    # Save the coordinates of all found contours
                (x, y, w, h) = cv2.boundingRect(c)
                
                h_w_ratio = (h / w)
                
                    # If the contour is too small, ignore it, otherwise, there's transient movement
                if (int(cv2.contourArea(c)) > MIN_SIZE_FOR_MOVEMENT):
                    logmsg("size: " + str(cv2.contourArea(c)) + ', ' + str(w) + ' x ' + str(h) + ", ratio: " + str(h_w_ratio))
                    if (h_w_ratio > MIN_RATIO_BOUND) and (h_w_ratio < MAX_RATIO_BOUND):
                        logmsg("draw rectangle")
                            # Draw a rectangle around big enough movements
                        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 64), 1)
                        smth_detected_in_frame = True
                        break

            #print("%s   %s  %s" % (frame_no, BUSY, strftime("%H:%M:%S", gmtime())))

            if DEBUG_MODE:
                vout.write(frame)
            
            if smth_detected_in_frame:
                if BUSY:
                    acc = 0
                else:
                    acc += 1
            else:
                if BUSY:
                    acc += 1
                else:
                    acc = 0
            
            if BUSY:
                vout_alarm.write(frame_virgin) 
            
            
            if acc == hit_in_a_row_threshold:
                if BUSY:
                    logmsg("BUSY = False")
                    BUSY = False
                    vout_alarm.release()
                    vout_alarm = None
                    #os.system('curl -s -X POST "https://api.telegram.org/bot'+BotToken+'/sendVideo"   -F chat_id='+ChatId+' -F video="@'+ cur_video_fname + '"')
                    pcloud_upload(cam_name, cur_video_fname)
                    #print('FREE - sent video')

                    write_2_db("Фиксация проникновения завершена", DB_MSG_TYPE_ALARM)
                else:
                    logmsg("BUSY = True")
                    BUSY = True
                        # сообщаем об алареме через телеграм-бота, туда скриншот с камеры
                        # пишем в лог до тех пор пока не спадет флаг аларма
                    #os.system('curl    -X POST "https://api.telegram.org/bot'+BotToken+'/sendMessage" -d "chat_id='+ChatId+'&text=person_detected_alarm"')
                    cur_time_str = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
                    img_fname = STORAGE_DIR + str(DB_CAMERA_ID) + '/' + cur_time_str + '_end.png' 
                    cv2.imwrite(img_fname, frame)                    
                        # чтобы не беспокоить ложными тревогами не отправляем пустых сообщений с некоторых камер
                    #os.system('curl -s -X POST "https://api.telegram.org/bot'+BotToken+'/sendPhoto"   -F chat_id='+ChatId+' -F photo="@'+ img_fname + '" -F caption="Камера ' + str(DB_CAMERA_ID) + ' (' + CAMERA_DESCR + '), Проникновение на участок" &')
                    pcloud_upload(cam_name, img_fname)
                    
                    img_fname = STORAGE_DIR + str(DB_CAMERA_ID) + '/' + cur_time_str + '_begin.png' 
                    cv2.imwrite(img_fname, PrevFramesList[0])                    
                    #os.system('curl -s -X POST "https://api.telegram.org/bot'+BotToken+'/sendPhoto"   -F chat_id='+ChatId+' -F photo="@'+ img_fname + '" -F caption="Камера ' + str(DB_CAMERA_ID) + ' (' + CAMERA_DESCR + '), Проникновение на участок (начало фиксации)" &')
                    pcloud_upload(cam_name, img_fname)
                    
                    
                    #print('BUSY - sent photo')
                    write_2_db("Фиксация проникновения", DB_MSG_TYPE_ALARM)
                        # отдаем на проверку-подтверждение
                    toRedis(R, RQUEUE_NAME_IMG_4_VERIFY, frame)
                    for frm in PrevFramesList:
                        toRedis(R, RQUEUE_NAME_IMG_4_VERIFY, frm)

                    cur_video_fname = STORAGE_DIR + str(DB_CAMERA_ID) + '/' + cur_time_str + '.avi' 
                    vout_alarm = cv2.VideoWriter(cur_video_fname, cv2.VideoWriter_fourcc(*'XVID'), 1, (video_w, video_h), True)
                    for f in range(len(PrevFramesList)):
                        vout_alarm.write(PrevFramesList.pop(0))
                        
             # для проверки           
            # if frame_no == 70:
                # BUSY = False
                # vout_alarm.release()
                # vout_alarm = None
                # os.system('curl -s -X POST "https://api.telegram.org/bot'+BotToken+'/sendVideo"   -F chat_id='+ChatId+' -F video="@'+ cur_video_fname + '"')
                # print('FREE - sent video')
                # write_2_db("Фиксация проникновения завершена", 1)
                
            # if frame_no == 20:
                # BUSY = True
                    # # сообщаем об алареме через телеграм-бота, туда скриншот с камеры
                    # # пишем в лог до тех пор пока не спадет флаг аларма
                # #os.system('curl    -X POST "https://api.telegram.org/bot'+BotToken+'/sendMessage" -d "chat_id='+ChatId+'&text=person_detected_alarm"')
                # cur_time_str = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
                # img_fname = STORAGE_DIR + str(DB_CAMERA_ID) + '/' + cur_time_str + '.png' 
                # cv2.imwrite(img_fname, frame)
                # os.system('curl -s -X POST "https://api.telegram.org/bot'+BotToken+'/sendPhoto"   -F chat_id='+ChatId+' -F photo="@'+ img_fname + '" -F caption="Проникновение на участок"')
                # print('BUSY - sent photo')
                # write_2_db("Фиксация проникновения", 1)
                # toRedis(R, RKEY_IMG_4_VERIFY, frame)

                # cur_video_fname = STORAGE_DIR + str(DB_CAMERA_ID) + '/' + cur_time_str + '.avi' 
                # vout_alarm = cv2.VideoWriter(cur_video_fname, cv2.VideoWriter_fourcc(*'XVID'), 1, (video_w, video_h), True)
                # for f in range(len(PrevFramesList)):
                    # vout_alarm.write(PrevFramesList.pop(0))
                        
        except Exception as e:
            print(PrintException())
            #write_2_db("Exception: " + str(e) + ' ' + traceback.format_exc(), 2)
            write_2_db("Exception: " + PrintException(), DB_MSG_TYPE_ERR)
            logmsg("Exception: " + PrintException())
            sys.exit()


