#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time
import threading
import cx_Oracle
import netsnmp
import csv
import re
import os
import Queue
#import pdb
import sys
from threading import Thread

#global stderr
#基础数据
workQueue = Queue.Queue(0)
max_thread = 5

oid = {
       'HU':'1.0.8802.1.1.2.1.4.2.1.4',
       'FH':'1.0.8802.1.1.2.1.4.2.1.2',
       'ZT':'1.0.8802.1.1.2.1.4.2.1.4'
}

exitFlag = 0
class SnmpClass(object):
    """
    SNMP
    """
    def __init__(self, oid="ifDescr", version=2, destHost="localhost", community="public",file="/slview/test/lixn/snmp.csv"):
        self.oid = oid
        self.version = version
        self.destHost = destHost
        self.community = community
        self.file = file

    @property
    def query(self):
        """
        snmpwalk
        """
        result = None
        try:
            result = netsnmp.snmpwalk(netsnmp.VarList(netsnmp.Varbind(self.oid,'',10,'INTEGER')),Version=int(self.version),DestHost=self.destHost,Community=self.community)
            print result
            if len(result) == 0:
                error = 'snmp get lldp info fail'
                if not os.path.exists(self.file):
                    os.mknod(self.file)
                with open(self.file, 'w') as f:
                    csvwriter = csv.writer(f)
                    csvwriter.writerow([self.destHost, self.community, self.oid, error])
        except Exception:
            error = 'snmp get lldp info fail'
            if not os.path.exists(self.file):
                os.mknod(self.file)
            with open(self.file,'w') as f:
                csvwriter = csv.writer(f)
                csvwriter.writerow([self.destHost,self.community,self.oid,error])
            result = None
        return result

class DeviceList(object):
    """获取设备信息"""
    def __init__(self,db_connect):
        self.db_connect = db_connect
        self.devinfo = {}

    def get_devinfo(self,*args,**kwargs):
        sql = None
        if len(args) == 0:
            sql = "select loopaddress,decrypt_data(rocommunity,'beijingtiananmen'),snmpversion,devicemodelcode from device where changetype='0'"
        else:
            deivce = '(\'' + '\',\''.join(args[0].split(',')) + '\')'
            sql = "select loopaddress,decrypt_data(rocommunity,'beijingtiananmen'),snmpversion,devicemodelcode from device where deviceid in {devlist} and changetype='0'".format(devlist=deivce)
        query = self.db_connect.execute(sql)
        rows = query.fetchall()
        for row in rows:
            if row != None:
                self.devinfo[row[0]] = [row[0],row[1],row[2],row[3]]
            else:
                continue
        return self.devinfo

class myThread(threading.Thread):
    def __init__(self,loopaddress,q):
        super(myThread, self).__init__()
        self.loopaddress = loopaddress
        self.q = q

    def run(self):
        print("Starting,queue has %s data"%self.q.qsize())
        process_data(self.q)
        print("Exiting")


def process_data(q):
    global exitFlag
    while not exitFlag:
        queueLock.acquire()
        if not workQueue.empty():
            loopaddress = q.get()
            try:
                devicemodelcode = deviceinfo.get(loopaddress)[3]
                rocommunity = deviceinfo.get(loopaddress)[1]
                searchObj = re.search(r'DEV\_IP\_\S+\_(\S+)\_(IPRAN|COM)', devicemodelcode, re.M | re.I)
                devoid = None
                if searchObj:
                    devoid = oid[searchObj.group(1)]
                else:
                    devoid = oid['HU']
            except TypeError:
                devicemodelcode = 'HU'
                rocommunity = 'public'
                devoid = oid['HU']
            print("I'm threading" + threading.current_thread().name)
            print("loopaddress:%s community:%s oid:%s" % (loopaddress, rocommunity,devoid))
            obj = SnmpClass(destHost=str(loopaddress), community=str(rocommunity), oid=str(devoid))
            obj.query
            queueLock.release()
            time.sleep(2)
        else:
            queueLock.release()
            exitFlag = 1


if __name__ == '__main__':
    #pdb.set_trace()
    conn = cx_Oracle.connect('slview/slview@132.225.164.31:1521/dbnms')
    c = conn.cursor()
    dev_obj = DeviceList(c)
    #获取设备信息
    deviceid = None
    if len(sys.argv) > 1:
        deviceid = sys.argv[sys.argv.index('-deviceid') + 1]
        #deivce = '(\'' + '\',\''.join(deviceid.split(',')) + '\')'
    deviceinfo = dev_obj.get_devinfo(deviceid)
    conn.close()
    queueLock = threading.Lock()
    devicelist = deviceinfo.keys()
    for i in devicelist:
        workQueue.put(i)
    #process_data(workQueue)

    for i in range(3):
        t = myThread(i,workQueue)
        t.start()
    for i in range(3):
        t.join()











