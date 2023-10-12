#!/usr/bin/perl

# Basic Telegram Bot implementation using WWW::Telegram::BotAPI
use strict;
use warnings;
use WWW::Telegram::BotAPI;
use utf8;
use DBI;  
use Data::Printer;
use POSIX qw( strftime );
use Proc::Daemon;
use Redis;
use IO::Socket::PortState qw(check_ports);

#Proc::Daemon::Init;

my $continue = 1;
$SIG{TERM} = sub { $continue = 0 };



my $api = WWW::Telegram::BotAPI->new (
    token => ('12090xxxxxxxxxxxxxxxxxxCklqiNOa0r3XA')
);

# Bump up the timeout when Mojo::UserAgent is used (LWP::UserAgent uses 180s by default)
$api->agent->can ("inactivity_timeout") and $api->agent->inactivity_timeout (45);
my $me = $api->getMe or die;
my ($offset, $updates) = 0;

# The commands that this bot supports.
my $pic_id; # file_id of the last sent picture



my $commands = {
        # поставить на охрану
    "on"  => sub { 
        "activate_guard";
    },
        # сниять с охраны
    "off"  => sub { 
        "deactivate_guard";
    },
        # получить текущий снимок с камер
    "view"  => sub { 
        "view";
    },
        # жэурнал событий в текстовом виде
    "log"  => sub { 
        "show_log";
    },
    
    "status"  => sub { 
        "ping_cameras";
    },
    
    "_unknown" => "Unknown command :( Try /start"
};



# Generate the command list dynamically.
$commands->{start} = "Hello! Try /" . join " - /", grep !/^_/, keys %$commands;


# Special message type handling
my $message_types = {
    # Save the picture ID to use it in `lastphoto`.
    "photo" => sub { $pic_id = shift->{photo}[0]{file_id} },
    # Receive contacts!
    "contact" => sub {
        my $contact = shift->{contact};
        +{
            method     => "sendMessage",
            parse_mode => "Markdown",
            text       => sprintf (
                            "Here's some information about this contact.\n" .
                            "- Name: *%s*\n- Surname: *%s*\n" .
                            "- Phone number: *%s*\n- Telegram UID: *%s*",
                            $contact->{first_name}, $contact->{last_name} || "?",
                            $contact->{phone_number}, $contact->{user_id} || "?"
                        )
        }
    }
};


system('curl -X POST "https://api.telegram.org/bot'.'1209017671:AAH8evw44Tlf-eTtIXGwiOCklqiNOa0r3XA'.'/sendMessage" -d "chat_id=-444235704&text=restart Bot"');

printf "Hello! I am %s. Starting...\n", $me->{result}{username};

my $redis = Redis->new(server => '127.0.0.1:6379');

while (1) 
{
    $updates = $api->getUpdates ({
        timeout => 30, # Use long polling
        $offset ? (offset => $offset) : ()
    });
    unless ($updates and ref $updates eq "HASH" and $updates->{ok}) {
        warn "WARNING: getUpdates returned a false value - trying again...";
        next;
    }
    for my $u (@{$updates->{result}}) {
        $offset = $u->{update_id} + 1 if $u->{update_id} >= $offset;
        if (my $text = $u->{message}{text}) { # Text message
            printf "Incoming text message from \@%s\n", $u->{message}{from}{username};
            printf "Text: %s\n", $text;
            next if $text !~ m!^/[^_].!; # Not a command
            my ($cmd, @params) = split / /, $text;
            my $res = $commands->{substr ($cmd, 1)} || $commands->{_unknown};
            #p($res);
            # Pass to the subroutine the message object, and the parameters passed to the cmd.
            $res = $res->($u->{message}, @params) if ref $res eq "CODE";
            
            
            #p($res);
            next unless $res;
            #p($u);
            my $method = ref $res && $res->{method} ? delete $res->{method} : "sendMessage";
            #p($u);
            #p($method);
            if ($res eq 'activate_guard') {
                #$redis->set('guard_active' => '1');
                system("/bin/bash /root/house_guard/start.sh");
                $api->sendMessage ({
                    chat_id => $u->{message}{chat}{id},
                    text    => 'Режим охраны активирован'
                }, sub {
                    my ($ua, $tx) = @_;
                    die 'Something bad happened!' if $tx->error;
                    say $tx->res->json->{ok} ? 'YAY!' : ':('; # Not production ready!
                });
            }
            elsif ($res eq 'deactivate_guard') {
                #$redis->set('guard_active' => '0');
                system("/bin/bash /root/house_guard/stop.sh");
                $api->sendMessage ({
                    chat_id => $u->{message}{chat}{id},
                    text    => 'Снято с охраны'
                }, sub {
                    my ($ua, $tx) = @_;
                    die 'Something bad happened!' if $tx->error;
                    say $tx->res->json->{ok} ? 'YAY!' : ':('; # Not production ready!
                });
            }
            elsif ($res eq 'ping_cameras') {
                my $timeout = 10;

                my %ports = (
                    tcp => {
                        1080 => {}, 
                        1180 => {},
                        1280 => {},
                        1380 => {},
                        1480 => {},
                        }
                    );
                my @ips = ('172.16.78.253');

                my $status_msg = '';
                for my $ip (@ips) {
                    chomp $ip;
                    my $host_hr = check_ports($ip, $timeout, \%ports);
                    for my $port (sort {$a <=> $b} keys %{$host_hr->{tcp}}) {
                        my $stat = $host_hr->{tcp}{$port}{open} ? 'online' : 'failure';
                        print "$ip - $port - $stat\n";
                        $status_msg .= "$ip - $port - $stat\n";
                    }
                }
                
                my $run_daemons = `ps aux | grep guard`;

                my %cam_status = ('cam_1' => 'disabled','cam_2' => 'disabled','cam_3' => 'disabled','cam_4' => 'disabled', 'cam_5' => 'disabled', 'cam_6' => 'disabled',);
                my @arr = split("\n", $run_daemons);
                for my $str (@arr) {
                    if ($str =~ /.*(cam_\d).*/) 
                    {
                        $cam_status{$1} = "is working"; 
                    }
                }
                my $run_daemons = '';
                for my $k (sort keys%cam_status) {
                    $run_daemons .= "Daemon for $k $cam_status{$k}\n";
                }
                
                $api->sendMessage ({
                            chat_id => $u->{message}{chat}{id},
                            text    => $status_msg . "\n" . $run_daemons
                        }, sub {
                            my ($ua, $tx) = @_;
                            die 'Something bad happened!' if $tx->error;
                            say $tx->res->json->{ok} ? 'YAY!' : ':('; # Not production ready!
                        });
            }
            elsif ($res eq 'view') {
                    # FIXME: цикл по всем камерам в системе
                $api->sendPhoto ({
                    chat_id => $u->{message}{chat}{id},
                    photo   => {
                        file => '/root/house_guard/cam_1/snapshot.png'
                    },
                    caption => 'Камера 1: Флигель, Вход от соседей'
                });
                $api->sendPhoto ({
                    chat_id => $u->{message}{chat}{id},
                    photo   => {
                        file => '/root/house_guard/cam_2/snapshot.png'
                    },
                    caption => 'Камера 2: Лужайка, 1ая Линия'
                });
                $api->sendPhoto ({
                    chat_id => $u->{message}{chat}{id},
                    photo   => {
                        file => '/root/house_guard/cam_3/snapshot.png'
                    },
                    caption => 'Камера 3: Крыльцо, вход перед калиткой'
                });
                $api->sendPhoto ({
                    chat_id => $u->{message}{chat}{id},
                    photo   => {
                        file => '/root/house_guard/cam_4/snapshot.png'
                    },
                    caption => 'Камера 4: Гараж, генератор, крыльцо'
                });
                $api->sendPhoto ({
                    chat_id => $u->{message}{chat}{id},
                    photo   => {
                        file => '/root/house_guard/cam_5/snapshot.png'
                    },
                    caption => 'Камера 5: Мангал, детская площадка'
                });
                $api->sendPhoto ({
                    chat_id => $u->{message}{chat}{id},
                    photo   => {
                        file => '/root/house_guard/cam_6/snapshot.png'
                    },
                    caption => 'Камера 6: Калитка - вход'
                });
                
                #$api->sendMessage ({
                #            chat_id => $u->{message}{chat}{id},
                #            text    => "$msg"
                #        }, sub {
                #            my ($ua, $tx) = @_;
                #            die 'Something bad happened!' if $tx->error;
                #            say $tx->res->json->{ok} ? 'YAY!' : ':('; # Not production ready!
                #        });
            }
            elsif ($res eq 'log') {
                
            }
            else {
                $api->$method ({
                    chat_id => $u->{message}{chat}{id},
                    ref $res ? %$res : ( text => $res )
                });
            }
            print "Reply sent.\n";
        }
        # Handle other message types.
        for my $type (keys %{$u->{message} || {}}) {
            next unless exists $message_types->{$type} and
                        ref (my $res = $message_types->{$type}->($u->{message}));
            my $method = delete ($res->{method}) || "sendMessage";
            $api->$method ({
                chat_id => $u->{message}{chat}{id},
                %$res
            })
        }
    }
}
