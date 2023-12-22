import schedule as schedule
from pysnmp.hlapi import *
import pymysql
import time
from datetime import datetime

class VlanThroughOut:

    def __init__(self):
        self.mysql_host = "10.10.10.244"
        self.mysql_user = "root"
        self.mysql_password = "Password123@mysql"
        self.mysql_db = "ale"
        self.mysql_table = "vlan_through_out"
    # 提供的IP地址
    ips_by_device_type = {
        'OmniSwitch': ['10.10.10.68', '10.10.10.226', '10.10.10.227'],
    }

    # SNMP数据收集函数
    def get_snmp_data(host, community, oid):
        iterator = getCmd(
            SnmpEngine(),
            CommunityData(community),
            UdpTransportTarget((host, 161)),
            ContextData(),
            ObjectType(ObjectIdentity(oid))
        )

        errorIndication, errorStatus, errorIndex, varBinds = next(iterator)

        if errorIndication:
            print(f"Error: {errorIndication}")
            return None
        elif errorStatus:
            print(f"SNMP Error: {errorStatus.prettyPrint()} at {varBinds[int(errorIndex) - 1][0] if errorIndex else '?'}")
            return None
        else:
            for varBind in varBinds:
                return str(varBind[1])

    # MySQL数据库插入函数
    # 数据库插入函数
    def insert_into_mysql(connection, table, ip,vlan, ifOutOctets,ifInOctets, data_create, data_update):
        with connection.cursor() as cursor:
            # 检查该IP是否已经存在于数据库中
            ifOutOctets_b = int(ifOutOctets) / 8
            ifInOctets_b = int(ifInOctets) / 8
            ifOutOctets_kb = int(ifOutOctets_b) / 1024
            ifInOctets_kb = int(ifInOctets_b) / 1024
            ifInOctets_mb = int(ifInOctets_kb) / 1024
            ifOutOctets_mb = int(ifOutOctets_kb) / 1024

            sql = f"INSERT INTO `{table}` (`ip`, `vlan`, `ifOutOctets`,`ifInOctets`, `data_create`, `data_update`) VALUES (%s,%s,%s,%s, %s, %s)"
            cursor.execute(sql, (ip,vlan, ifOutOctets_mb,ifInOctets_mb, data_create, data_update))

        connection.commit()

    # 主逻辑
    def job(self):
        community = "public"  # SNMP community字符串
        ifOutOctets1_oid = '.1.3.6.1.2.1.2.2.1.16.13600002'
        ifInOctets1_oid = '.1.3.6.1.2.1.2.2.1.10.13600002'
        ifOutOctets2_oid = '.1.3.6.1.2.1.2.2.1.16.13600001'
        ifInOctets2_oid = '.1.3.6.1.2.1.2.2.1.10.13600001'
        vlan_oid1 = '.1.3.6.1.2.1.2.2.1.2.13600002'
        vlan_oid2 = '.1.3.6.1.2.1.2.2.1.2.13600001'

        # 数据库信息


        # 建立数据库连接
        connection = pymysql.connect(host=self.mysql_host, user=self.mysql_user, password=self.mysql_password, db=self.mysql_db)

        try:
            for device_type, ips in self.ips_by_device_type.items():
                for ip in ips:
                    if ip == '10.10.10.226':
                        ifOutOctets = VlanThroughOut.get_snmp_data(ip, community, ifOutOctets2_oid)
                        ifInOctets = VlanThroughOut.get_snmp_data(ip, community, ifInOctets2_oid)
                    else:
                        ifOutOctets = VlanThroughOut.get_snmp_data(ip, community, ifOutOctets1_oid)
                        ifInOctets = VlanThroughOut.get_snmp_data(ip, community, ifInOctets1_oid)
                    if ip == '10.10.10.226':
                        vlan = VlanThroughOut.get_snmp_data(ip, community, vlan_oid2)
                    else:
                        vlan = VlanThroughOut.get_snmp_data(ip, community, vlan_oid1)
                    # 获取设备的sysName
                    if ip:
                        data_update = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        # 如果是首次运行，data_create和data_update时间相同
                        VlanThroughOut.insert_into_mysql(connection, self.mysql_table, ip, vlan, ifOutOctets,ifInOctets, data_update, data_update)
                        print(f"Data for device with IP {ip} updated in MySQL database successfully.")
                    else:
                        print(f"Failed to get sysName for device with IP {ip}")

        finally:
            connection.close()


