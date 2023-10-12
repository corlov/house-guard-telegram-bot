#!/usr/bin/perl

my $t =  time();
system("pg_dump -h localhost -U hc625ma -W -F t house_cctv > db_dump_$t.tar");

