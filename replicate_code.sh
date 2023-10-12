#!/bin/bash

cp cam_template/guard.py cam_1/
cp cam_template/guard.py cam_2/
cp cam_template/guard.py cam_3/
cp cam_template/guard.py cam_4/
cp cam_template/guard.py cam_5/
cp cam_template/guard.py cam_6/


cp cam_template/guard_person_detector.py cam_1/
cp cam_template/guard_person_detector.py cam_2/
cp cam_template/guard_person_detector.py cam_3/
cp cam_template/guard_person_detector.py cam_4/
cp cam_template/guard_person_detector.py cam_5/
cp cam_template/guard_person_detector.py cam_6/


#systemctl restart motion_detector_cam1.service
#systemctl restart motion_detector_cam2.service
#systemctl restart motion_detector_cam3.service
#systemctl restart motion_detector_cam4.service

#systemctl restart motion_detector_person_cam1.service
#systemctl restart motion_detector_person_cam2.service
#systemctl restart motion_detector_person_cam3.service
#systemctl restart motion_detector_person_cam4.service

