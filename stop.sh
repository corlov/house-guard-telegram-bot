#!/bin/bash

systemctl stop motion_detector_cam1.service
systemctl stop motion_detector_cam2.service
systemctl stop motion_detector_cam3.service
systemctl stop motion_detector_cam4.service
systemctl stop motion_detector_cam5.service
systemctl stop motion_detector_cam6.service


systemctl stop motion_detector_person_cam1.service
systemctl stop motion_detector_person_cam2.service
systemctl stop motion_detector_person_cam3.service
systemctl stop motion_detector_person_cam4.service
systemctl stop motion_detector_person_cam5.service
systemctl stop motion_detector_person_cam6.service

#systemctl restart motion_detector_telegram_bot.service
