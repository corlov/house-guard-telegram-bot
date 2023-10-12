#!/usr/bin/perl

system('find /root/house_guard/cam_1/storage/1/* -mtime +5 -delete -type f');
system('find /root/house_guard/cam_2/storage/2/* -mtime +5 -delete -type f');
system('find /root/house_guard/cam_3/storage/3/* -mtime +5 -delete -type f');
system('find /root/house_guard/cam_4/storage/4/* -mtime +5 -delete -type f');
system('find /root/house_guard/cam_5/storage/5/* -mtime +5 -delete -type f');
system('find /root/house_guard/cam_6/storage/6/* -mtime +5 -delete -type f');




