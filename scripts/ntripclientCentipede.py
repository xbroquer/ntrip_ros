#!/usr/bin/python

import rospy

#from nmea_msgs.msg import Sentence
from rtcm_msgs.msg import Message

import http.client
import base64 
import urllib
from threading import Thread
import binascii
from datetime import datetime

class ntripconnect(Thread):
    def __init__(self, ntc):
        super(ntripconnect, self).__init__()
        self.ntc = ntc
        self.stop = False

   #  master  ~  src  NTRIP  NTRIP Client  ./NtripClient.py  -u centipede -p centipede  -m 10 -v2 -v  caster.centipede.fr 2101 STLYS

    def run(self):

        myheaders = {
            'Ntrip-Version': 'Ntrip/2.0',
            'User-Agent': 'NTRIP NtripClient/0.1',
            "Authorization":"Basic {}".format(base64.b64encode(bytes(self.ntc.ntrip_user + ':' + self.ntc.ntrip_pass,"utf-8")).decode("ascii")),
            "Connection" : "close"
        }

        conn = http.client.HTTPConnection(self.ntc.ntrip_server)
        conn.request("GET", '/'+self.ntc.ntrip_stream, self.ntc.nmea_gga, myheaders)
        response = conn.getresponse()

        if response.status != 200: raise Exception("blah")

        buf = b''
        rmsg = Message()
        while not self.stop:
            data = response.read(1)
            #print(binascii.hexlify(data))
            if len(data) != 0:
                if data[0] == 211:
                    buf += data
                    data = response.read(2)
                    buf += data
                    cnt = data[0] * 256 + data[1]
                    data = response.read(2)
                    buf += data
                    typ = (data[0] * 256 + data[1]) / 16
                    print (str(datetime.now()), cnt, typ)
                    cnt = cnt + 1
                    for x in range(cnt):
                        data = response.read(1)
                        buf += data
                    rmsg.message = buf
                    rmsg.header.seq += 1
                    rmsg.header.stamp = rospy.get_rostime()
                    self.ntc.pub.publish(rmsg)

                    buf = b''
                else: print (data)
            else:
                ''' If zero length data, close connection and reopen it '''
                restart_count = restart_count + 1
                print("Zero length ", restart_count)
                connection.close()
                connection = http.client.HTTPConnection(self.ntc.ntrip_server)
                connection.request('GET', '/'+self.ntc.ntrip_stream, self.ntc.nmea_gga, myheaders)
                response = connection.getresponse()
                if response.status != 200: raise Exception("blah")
                buf = b''
        
        connection.close()

class ntripclient:
    def __init__(self):
        rospy.init_node('ntripclient', anonymous=True)

        self.rtcm_topic = rospy.get_param('~rtcm_topic', 'rtcm')
        self.nmea_topic = rospy.get_param('~nmea_topic', 'nmea')

        self.ntrip_server = rospy.get_param('~ntrip_server', 'caster.centipede.fr:2101')
        self.ntrip_user = rospy.get_param('~ntrip_user', 'centipede')
        self.ntrip_pass = rospy.get_param('~ntrip_pass', 'centipede')
        self.ntrip_stream = rospy.get_param('~ntrip_stream', 'STLYS')
        self.nmea_gga = rospy.get_param('~nmea_gga')

        self.pub = rospy.Publisher(self.rtcm_topic, Message, queue_size=10)

        self.connection = None
        self.connection = ntripconnect(self)
        self.connection.start()

    def run(self):
        rospy.spin()
        if self.connection is not None:
            self.connection.stop = True

if __name__ == '__main__':
    c = ntripclient()
    c.run()

