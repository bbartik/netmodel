#!/usr/bin/env python3.5

import ipaddress
import pprint

from nornir.core import InitNornir
from nornir.plugins.tasks.networking import netmiko_send_command
from nornir.plugins.functions.text import print_result
from nornir.plugins.tasks.networking import napalm_get
from napalm import get_network_driver


# PART 1: GATHER DATA


nr = InitNornir() 
router_list = []


# get all the interface data and store it in the intfs variable

intfs = nr.run(task=napalm_get, getters=["interfaces_ip"])

print(intfs)
print(dir(intfs))

intfs = intfs.items()

print(intfs)
print(type(intfs))


# FUNCTION 1: This function creates an ipv4 interface list per router, each
# object in the list is a dictionary with "interface", "address", "mask" keys

def create_interface_list(intf_result):

    # loop through the items and add only the ones with ipv4 addresses
    # there is lots of unpacking here so use print to find our what you have
    
    for k, v in intf_result.items():
        
        intf_list = []

        for y, z in v.items():

            intf_obj = {}

            if "ipv4" in z:
                intf_obj["int"] = y
                
                for a, b in z.items():
                    
                    for c, d in b.items():
                        intf_obj["ip"] = c
                        intf_obj["mask"] = d["prefix_length"]

                intf_list.append(intf_obj)        

    return intf_list

for x in intfs:
    
    # clear out the router list, we create a new router dictionary
    # everytime through. First key is the name, second is the interface
    # list which is created using the function above.

    router = {}
    router["name"] = x[0]
    
    intf_result = x[1][0].result
    router["interfaces"] = create_interface_list(intf_result)
    
    router_list.append(router)


# PART 2: Part of script which does the mapping of networks to the routers


network = {"networks":[]}
netmap = []

# FUNCTION 2: This creates the network lists based on interface subnets
# The list is then used to create a "map" of which routers are on each net

def create_netlist(router_list):
    netlist_init = []
    for r in router_list:
        rnets = []
        for int in r["interfaces"]:
            ip = (int["ip"], int["mask"])
            net = str(ipaddress.IPv4Network(ip, strict = False))
            rnets.append(net)
            netlist_init.append(net)
        r["networks"] = rnets
    return netlist_init

netlist = list(set(create_netlist(router_list)))

for x in netlist:
        net_obj = {}
        net_obj["name"] = x
        net_obj["nodes"] = []
        for y in router_list:
                for z in y["networks"]:
                        if x == z:
                                net_obj["nodes"].append(y["name"])
        netmap.append(net_obj)

for x in netmap:
    if len(x["nodes"]) > 1:
        for y in x["nodes"]:
            print(y, end=" ")
        print("are connected on network", x["name"])


