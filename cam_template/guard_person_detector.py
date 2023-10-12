#!/usr/bin/python3
# -*- coding: utf-8 -*-


#       taskset --cpu-list 0,1,2,3 python3 person_detector.py

import cv2
import numpy as np
from datetime import datetime
import time
import pprint
import sys
import os
import redis
import struct
import configparser

p = configparser.RawConfigParser()   
p.read('/root/house_guard/guard_system.conf')
cam_name = os.path.dirname(os.path.realpath(__file__)).split('/')[-1]

MIN_CONFIDENCE = float(p.get('nn', 'min_response_confidence'))
MIN_RATIO_BOUND = float(p.get(cam_name, 'min_ratio'))
MAX_RATIO_BOUND = float(p.get(cam_name, 'max_ratio'))
MIN_PERSON_SIZE = int(p.get(cam_name, 'MIN_CNTR_SIZE'))

BotToken = p.get('telegram_bot', 'BotToken') #'1209017671:AAH8evw44Tlf-eTtIXGwiOCklqiNOa0r3XA'
ChatId = p.get('telegram_bot', 'ChatId')     # '-444235704'

    # settings
DB_CAMERA_ID = p.get(cam_name, 'DB_CAMERA_ID')
SRC_VIDEO_STREAM = p.get(cam_name, 'SRC_VIDEO_STREAM')
HOME_DIR = p.get(cam_name, 'HOME_DIR')

RKEY_IMG_4_VERIFY =  'image_for_verify' + str(DB_CAMERA_ID)
RQUEUE_NAME_IMG_4_VERIFY = 'queue_image_for_verify_' + str(DB_CAMERA_ID)




cl_green = (0, 255, 0)
cl_blue = (255, 0, 0)
cl_sky_blue = (232, 162, 0)
cl_red = (0, 0, 255) 
cl_violet = (235, 0, 255)
cl_lime = (127, 255, 0)
cl_cyan = (0, 255, 255)
cl_yellow = (0, 255, 255)
cl_white = (255, 255, 255)
cl_black = (0, 0, 0)
cl_orange = (0, 127, 255)

use_tiny = True



CONFIG_FILE = HOME_DIR + 'yolov3.cfg'
WEIGHTS_FILE = HOME_DIR + 'yolov3.weights'
CLASSES_NAMES_FILE = HOME_DIR + 'coco.names'


def logmsg(msg_text):
    cur_time = datetime.now().strftime("[%m.%d.%Y %H:%M:%S]     ")
    
    f = open(HOME_DIR + "guard_person.log", "a")  # write mode 
    f.write(cur_time + msg_text + "\n") 
    f.close() 
    
    
    
def get_output_layers(net):
    
    layer_names = net.getLayerNames()
    
    output_layers = [layer_names[i[0] - 1] for i in net.getUnconnectedOutLayers()]

    return output_layers




def draw_prediction(img, class_id, confidence, x, y, x_plus_w, y_plus_h):
    color = cl_cyan
    cv2.rectangle(img, (x,y), (x_plus_w,y_plus_h), color, 1)



def toRedis(r, redis_key, img):
   h, w = img.shape[:2]
   shape = struct.pack('>II',h,w)
   encoded = shape + img.tobytes()
   #print (encoded)
   r.set(redis_key, encoded)
   
   
def fromRedis(r, redis_queue_name):
   """Retrieve Numpy array from Redis key 'n'"""
   #encoded = r.get(redis_key)
   encoded = r.lpop(redis_queue_name)
   #print (encoded)
   h, w = struct.unpack('>II',encoded[:8])
   img = np.frombuffer(encoded, dtype=np.uint8, offset=8).reshape(h,w,3)
   return img

   

if __name__ == "__main__":
    
    R = redis.Redis(host='127.0.0.1', port=6379, db=0)
    logmsg('started')
        # загружаем названия классов
    classes = None
    with open(CLASSES_NAMES_FILE, 'r') as f:
        classes = [line.strip() for line in f.readlines()]

    net = cv2.dnn.readNet(WEIGHTS_FILE, CONFIG_FILE)
    print("readNet ok")

    #os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;1"
    
    while(1):
        alarm_value = False

        if R.llen(RQUEUE_NAME_IMG_4_VERIFY) == 0: 
        #if R.get(RKEY_IMG_4_VERIFY) is None:
            print('wait...')
            time.sleep(1)
            continue

        

        inp_image = fromRedis(R, RQUEUE_NAME_IMG_4_VERIFY)
        
        Width = inp_image.shape[1]
        Height = inp_image.shape[0]
            # fixme: непонятные константы
        scale = 0.00392
            # fixme: непонятные константы
        blob = cv2.dnn.blobFromImage(inp_image, scale, (416,416), (0,0,0), True, crop=False)

        net.setInput(blob)

            # fixme: медленная операция
        outs = net.forward(get_output_layers(net))


        class_ids = []
        confidences = []
        boxes = []
            # порог вероятности после которого мы уверенны что это необходимый объект найден сетью
        conf_threshold = 0.2
        nms_threshold = 0.4

        res_count = 0
        for out in outs:
            for detection in out:
                scores = detection[5:]
                class_id = np.argmax(scores)
                confidence = scores[class_id]
                
                if (confidence > MIN_CONFIDENCE) and (class_id == 0):
                    center_x = int(detection[0] * Width)
                    center_y = int(detection[1] * Height)
                    w = int(detection[2] * Width)
                    h = int(detection[3] * Height)
                    x = center_x - w / 2
                    y = center_y - h / 2

                    h_w_ratio = (h / w)
                    area_square = h * w
                    if (h_w_ratio > MIN_RATIO_BOUND) and (h_w_ratio < MAX_RATIO_BOUND) and (area_square >= MIN_PERSON_SIZE):
                        alarm_value = True
                        class_ids.append(class_id)
                        confidences.append(float(confidence))
                        boxes.append([x, y, w, h])

        indices = cv2.dnn.NMSBoxes(boxes, confidences, conf_threshold, nms_threshold)

            # прорисовка прямоугольников на изображении
        for i in indices:
            i = i[0]
            box = boxes[i]
            x = box[0]
            y = box[1]
            w = box[2]
            h = box[3]
            draw_prediction(inp_image, class_ids[i], confidences[i], round(x), round(y), round(x+w), round(y+h))
            center_x = round((x + x + w) / 2)
            center_y = round((y + y + h) / 2)
        
            
        if alarm_value:
            os.system('curl -X POST "https://api.telegram.org/bot'+BotToken+'/sendMessage" -d "chat_id='+ChatId+'&text=Камера ' + str(DB_CAMERA_ID) + ' Подтверждение проникновения (Уровень 2)"')
            cv2.imwrite(HOME_DIR + 'alarm.png', inp_image)
            os.system('curl -s -X POST "https://api.telegram.org/bot'+BotToken+'/sendPhoto"   -F chat_id='+ChatId+' -F photo="@'+ HOME_DIR + 'alarm.png' + '"')
            logmsg('ALARM')
        else:
            #os.system('curl -X POST "https://api.telegram.org/bot'+BotToken+'/sendMessage" -d "chat_id='+ChatId+'&text=Камера ' + str(DB_CAMERA_ID) + ' Ложная тревога"')
            logmsg('false alarm')
            pass
            
        #R.delete(RKEY_IMG_4_VERIFY)


            
                
                
        