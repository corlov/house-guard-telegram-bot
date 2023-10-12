#!/usr/bin/perl
use strict;
use warnings;
use POSIX qw(strftime);

# /etc/crontab каждую минуту вызывать этот скрипт

my $STORAGE_DIR = '/root/house_guard/cam_template/video_storage/';
my $CAM_NAME = 'cam_1';
my $CAM_ADDR = '"rtsp://172.16.74.29/akg036_(p)d5"';

main();

sub main {
    system("mkdir -p $STORAGE_DIR");
    my $time_label = strftime("%Y.%m.%d_%H_%M_%S", localtime);
    print ("$time_label ok\n");
    system("ffmpeg -y -t 120 -i $CAM_ADDR -acodec copy -vcodec copy ${STORAGE_DIR}${CAM_NAME}_${time_label}.avi");
}




#-vf select='not(mod(n\,"+str(step_len_f)+"))',select='gte(scene,0)',metadata=print:file="+temp_file+" 
# ffmpeg -y -t 10 -i "rtsp://172.16.74.29/akg036_(p)d5" -vf select='gte(scene,0.5)' -acodec copy -vcodec copy test.avi
