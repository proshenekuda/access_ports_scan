from netmiko import ConnectHandler
from datetime import datetime
from pprint import pprint
import textfsm
import csv
import socket
import struct
import re

start_time = datetime.now()

site = 'SEAKRP'

site = site.lower()

print(site)

wrt_routers = [site + "wrt004", site + "wrt005"]

pprint(wrt_routers)

username = "m-dash username"
password = "password"


def nxos_get_cdp_neigbours(device_name, username, password):
    router = {
        'device_type': 'cisco_nxos',
        'ip': device_name,
        'username': username,
        'password': password,
        'verbose': False
    }

    net_connect = ConnectHandler(**router)
    show_cdp_neighbors = net_connect.send_command("show cdp neighbors")
    print("")
    print("show_cdp_neighbors")
    pprint(show_cdp_neighbors)
    print("")

    cdp_table = textfsm.TextFSM(open("cisco_nxos_show_cdp_neighbors"))
    cdp_results = cdp_table.ParseText(show_cdp_neighbors)
    print("")
    print("cdp_results")
    pprint(cdp_results, width=200)
    return cdp_results

def ios_get_cdp_neigbours(device_name, username, password):
    router = {
        'device_type': 'cisco_ios',
        'ip': device_name,
        'username': username,
        'password': password,
        'verbose': False
    }

    net_connect = ConnectHandler(**router)
    show_cdp_neighbors = net_connect.send_command("show cdp neighbors")
    print()
    print("show_cdp_neighbors")
    pprint(show_cdp_neighbors)

    cdp_table = textfsm.TextFSM(open("cisco_ios_show_cdp_neighbors"))
    cdp_results = cdp_table.ParseText(show_cdp_neighbors)

    print()
    print("cdp_results")
    pprint(cdp_results, width=200)
    return cdp_results

def get_switch_list(routers):

    wrt_cdp_table = []
    for wrt in routers:
        wrt_cdp_table += nxos_get_cdp_neigbours(wrt, username, password)

    pprint(wrt_cdp_table, width=200)

    switch_list = set()
    for item in wrt_cdp_table:
        if ("spare" not in item[0]) and ("wsw" in item[0]):
            switch_list.add(item[0][:12])
    pprint(switch_list)

    wsw_cdp_table = []
    for wsw in switch_list:
        wsw_cdp_table += ios_get_cdp_neigbours(wsw, username, password)

    pprint(wsw_cdp_table, width=200)

    full_table = wrt_cdp_table + wsw_cdp_table

    full_switch_list = set()
    for item in full_table:
        if "wsw" in item[0]:
            full_switch_list.add(item[0][:12])


    sorted_switch_list = sorted(full_switch_list)
    print()
    print("This is full switch list, two layers deep")
    pprint(sorted_switch_list)

    return sorted_switch_list


switch_list = get_switch_list(wrt_routers)

def get_interface_status(switch_name):
    switch = {
        'device_type': 'cisco_ios',
        'ip': switch_name,
        'username': username,
        'password': password,
        'verbose': False
    }

    net_connect = ConnectHandler(**switch)

    int_status = net_connect.send_command("show interface status")
    int_status_table = textfsm.TextFSM(open("cisco_ios_show_interfaces_status"))
    int_status_results = int_status_table.ParseText(int_status)
    pprint(int_status_results, width=200)
    record_switch = []
    for item in int_status_results:
        if "Gi" in item[0] or "Fa" in item[0]:
            record_line = []
            record_line.extend((switch_name, item[0], item[2], item[3]))
            record_switch.append(record_line)
    print("This is 1st Record switch")
    pprint(record_switch)

    int_desc = net_connect.send_command("show int desc")
    print()
    print(int_desc)
    print()
    int_desc_table = textfsm.TextFSM(open("xe_show_int_desc"))
    int_desc_results = int_desc_table.ParseText(int_desc)
    print("This is Parsed Interface Description")
    pprint(int_desc_results, width=200)
    print()

    for item1 in record_switch:
        for item2 in int_desc_results:
            if item1[1] == item2[0]:
                item1.append(item2[2])

    print()
    print("This is 2nd Record switch")
    pprint(record_switch, width=200)
    print()

    mac_add = net_connect.send_command("show mac address-table")
    mac_table = textfsm.TextFSM(open("cisco_ios_show_mac-address-table"))
    mac_results = mac_table.ParseText(mac_add)
    print()
    print(len(mac_results))
    pprint(mac_results, width=200)

    for item1 in record_switch:
        for item2 in mac_results:
            if len(item1) > 4:
                if ("wrt" not in item1[4]) and ("wsw" not in item1[4]) and (item1[1] != "Gi0/1") and ("Po" not in item1[1]) and (item1[1] == item2[3]):
                    if len(item1) <= 5:
                        item1.append([item2[0]])
                    else:
                        items = item1[5]
                        items.append(item2[0])
                        item1[5] = items

    print()
    print("This is 3rd Record switch")
    pprint(record_switch, width=200)
    print()

    return record_switch


mac_add_table = []
for switch in switch_list:
    mac_add_table += get_interface_status(switch)

print()
print("Mac Table for all switches")
pprint(mac_add_table, width=300)
print()

def show_ip_arp(device_name,username, password):
    router = {
        'device_type': 'cisco_nxos',
        'ip': device_name,
        'username': username,
        'password': password,
        'verbose': False
    }

    net_connect = ConnectHandler(**router)
    ip_arp = net_connect.send_command("show ip arp vrf all")
    arp_table = textfsm.TextFSM(open("cisco_nxos_show_ip_arp"))
    arp_results = arp_table.ParseText(ip_arp)
    pprint(arp_results, width=200)
    return arp_results


def sum_wrt(table_list):
    devices = []
    for device_name in table_list:
        wrt_table = show_ip_arp(device_name, username, password)
        devices.extend(wrt_table)
    return devices


wrts = sum_wrt(wrt_routers)

print()
print()
print()
print("This is Merged WRT table")
pprint(wrts)

def find_duplicates(value, grid):
    duplicates = []
    for line in grid:
        if value in line:
            duplicates.append(line)
    pprint (duplicates)
    print (len(duplicates))
    if len(duplicates) == 0:
        return duplicates
    elif len(duplicates) == 1:
        return duplicates[0]
    elif len(duplicates[0]) > len(duplicates[1]):
        return duplicates[0]
    elif len(duplicates[1]) > len(duplicates[0]):
        return duplicates[1]
    elif len(duplicates[0]) <= 4:
        return duplicates[1]
    elif len(duplicates[1]) <= 4:
        return duplicates[0]
    elif len(duplicates) > 2:
        print("Rule 2, Number of duplicates is" + str(len(duplicates)))
        return duplicates
    elif duplicates[0][4] == duplicates[1][4]:
        return(duplicates[0])
    elif duplicates[0][4] == '' and duplicates[1][4] != '':
        return(duplicates[1])
    elif duplicates[1][4] == '' and duplicates[0][4] != '':
        return(duplicates[0])
    else:
        print()
        print("Rule 6 There are 2 items")
        return (duplicates)

def unique_ipadd(grid):
    unique_ips = []
    for item in grid:
        value = find_duplicates(item[0], grid)
        pprint(value, width=100)
        if value not in unique_ips:
            unique_ips.append(value)
    print()
    print()
    print("This are unique IP addresses ")
    pprint(unique_ips, width=100)
    return unique_ips

ip_arp_table = unique_ipadd(wrts)

print ()
print("This IP ARP table")
pprint(ip_arp_table, width=200)
print()

def mac_against_iparp(mac_add_table, ip_arp_table):
     for item1 in mac_add_table:
          for item2 in ip_arp_table:
               if len(item1) > 5:
                    if item2[2] in item1[5]:
                         if len(item1) <= 6:
                              item1.append([item2[0]])
                         else:
                              items = item1[6]
                              items.append(item2[0])
                              item1[6] = items


     print()
     print("This is complete table")
     pprint(mac_add_table, width=200)
     print()
     return mac_add_table


kruto = mac_against_iparp(mac_add_table, ip_arp_table)

def ip_lookup(ip):
    try:
        host = socket.gethostbyaddr(ip.strip())
        return host[0]
    except socket.herror:
        return str(f"Missing hostname for {ip.strip()}")


for item1 in kruto:
     if len(item1) > 6:
          for item2 in item1[6]:
               dns_name = ip_lookup(item2)
               if len(item1) <= 7:
                    item1.append([dns_name])
               else:
                    items = item1[7]
                    items.append(dns_name)
                    item1[7] = items

pprint(kruto, width=250)

def get_vlan_gateway():

    router = {
        'device_type': 'cisco_nxos',
        'ip': wrt_routers[0],
        'username': username,
        'password': password,
        'verbose': False
    }

    net_connect = ConnectHandler(**router)
    show_hsrp = net_connect.send_command("show hsrp brief")
    if ("Invalid command" in show_hsrp) or ("Vlan" not in show_hsrp):
        show_vrrp = net_connect.send_command("show vrrp")
        print(show_vrrp)

        vrrp_table = textfsm.TextFSM(open("show_vrrp"))
        vrrp_results = vrrp_table.ParseText(show_vrrp)
        pprint(vrrp_results, width=200)

        for item in vrrp_results:
            show_mask = net_connect.send_command("show int vlan" + item[0] + " | i Internet")
            print(show_mask)
            item.append(show_mask[-2:])

            host_bits = 32 - int(item[2])
            mask = socket.inet_ntoa(struct.pack('!I', (1 << 32) - (1 << host_bits)))
            item.insert(2, mask)

        pprint(vrrp_results, width=200)

        return vrrp_results

    else:
        print(show_hsrp)

        hsrp_table = textfsm.TextFSM(open("show_hsrp"))
        hsrp_results = hsrp_table.ParseText(show_hsrp)
        pprint(hsrp_results, width=300)
        for item in hsrp_results:
            item.pop(1)

        for item in hsrp_results:
            show_mask = net_connect.send_command("show int vlan" + item[0] + " | i Internet")
            print(show_mask)
            item.append(show_mask[-2:])

            host_bits = 32 - int(item[2])
            mask = socket.inet_ntoa(struct.pack('!I', (1 << 32) - (1 << host_bits)))
            item.insert(2, mask)

        pprint(hsrp_results, width=200)

        return hsrp_results


vlan_gateway = get_vlan_gateway()

print()
print("Gateway")
pprint(vlan_gateway)

for item in kruto:
     if len(item) < 5:
          item.append("")
          item.append("")
          item.append("")
          item.append("")
     elif len(item) < 6:
          item.append("")
          item.append("")
          item.append("")
     elif len(item) < 7:
          item.append("")
          item.append("")
     elif len(item) < 8:
          item.append("")

print()
print("Before gateway")
pprint(kruto, width=300)

for item1 in kruto:
    for item2 in vlan_gateway:
        if item1[3] == item2[0]:
            item1.append(item2[2])
            item1.append(item2[1])

print()
print("After gateway")
pprint(kruto, width=300)

for item in kruto:
     hostname = item.pop(7)
     item.insert(5, hostname)
     item.insert(7, '')
     vlan = item.pop(3)
     item.insert(8, vlan)
     item.insert(0, '')
     item.insert(0, 'NO')
     item.insert(0, '')
     item.insert(0, '')
     item.insert(0, '')
     if "001" in item[5]:
          item.insert(0, 'MDF')
     elif "101" in item[5]:
          item.insert(0, 'MDF')
     else:
         item.insert(0, '')
     item.insert(7, '')

pprint(kruto, width=250)

for item in kruto:
    if item[11] == '':
        item[11] = 'SPARE'

def get_show_time(device_name, username, password):
    router = {
        'device_type': 'cisco_nxos',
        'ip': device_name,
        'username': username,
        'password': password,
        'verbose': False
    }

    net_connect = ConnectHandler(**router)
    show_t = net_connect.send_command("sho int | inc line prot|Last inp")
    print("")
    pprint(show_t)
    print("")

    time_table = textfsm.TextFSM(open("show_time"))
    time_results = time_table.ParseText(show_t)
    for item in time_results:
        if 'GigabitEthernet' in item[0]:
            string = item[0]
            replacement = string.replace('GigabitEthernet', 'Gi')
            item.pop(0)
            item.insert(0, replacement)
        elif 'FastEthernet' in item[0]:
            string = item[0]
            replacement = string.replace('FastEthernet', 'Fa')
            item.pop(0)
            item.insert(0, replacement)

    for item in time_results:
        item.insert(0, device_name)
    print("")
    print("Show time table")
    pprint(time_results, width=200)
    return time_results


show_time_table = []
for device_name in switch_list:
    show_time_table += get_show_time(device_name, username, password)

print("")
print("Show full time table")
pprint(show_time_table, width=200)

for item in kruto:
    item.insert(10, '')
    item.insert(11, '')

for item1 in kruto:
    for item2 in show_time_table:
        if (item1[6] == item2[0]) and (item1[8] == item2[1]):
            item1[10] = item2[2]
            item1[11] = item2[3]


heading = [
    'IDF/MDF',
    'PP#',
    'To',
    'Jack#',
    'Patch',
    'Assignment: comment',
    'Switch Name',
    'Switch S/N',
    'Port#',
    'Port Status',
    'Last input',
    'Last output',
    'Port Description',
    'hostname',
    'AP MAC',
    'AP S/N',
    'IP',
    'vLAN',
    'Mask',
    'Gateway',
    'Watts',
    'PoE',
    'device',
    'AP Location',
    'Version update'
]

kruto.insert(0, heading)

now = datetime.now()
us_date = str(now.month) +"-"+ str(now.day) + "-" + str(now.hour) + "-" + str(now.minute)

csvfile = str(wrt_routers[0][:6]) + "_report_" + us_date + ".csv"

with open(csvfile, "w") as output:
    writer = csv.writer(output, lineterminator='\n')
    writer.writerows(kruto)

end_time = datetime.now()
total_time = end_time - start_time

print()
print("Total time to run the script for " + str(wrt_routers[0][:6]) + " = " + str(total_time))
