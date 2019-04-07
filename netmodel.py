#!/usr/bin/env python3

import ipaddress
import json
import requests
import random
import re
import fileinput
import paramiko

from nornir.core import InitNornir
from nornir.plugins.tasks.networking import netmiko_send_command
from nornir.plugins.functions.text import print_result
from nornir.plugins.tasks.networking import napalm_get
from napalm import get_network_driver
from ciscoconfparse import CiscoConfParse

from gnsmodel import Node
from gnsmodel import Link
from gnsmodel import Interface
from gnsconfig import create_gns_config


'''
This script creates a GNS topology based on a live network. Here are the steps
it takes:
1. Log into each device in the inventory and create a "node" list which is list
of routers (gns calls them nodes).
2. From the ip addresses in each node create a network list
3. Prune any networks from the network list you don't want to model in gns3
4. From the two lists create a "netmap" that is what i need to create a
gns3 topology:
    link1 has routers r1 and r2
    link2 has routers r1 and r3
5. Go back to the node list and prune any interfaces you dont need configs for
6. Get the configs for the interfaces left on the nodes
7. Create starup configs for the nodes
8. Create the gns tpology
'''


# initialize nornir, and other variables

nr = InitNornir()
node_list = []
gns_node_list = []
network = {"networks": []}

# get all the interface data and store it in the intfs variable

router_get = nr.run(task=napalm_get, getters=["config", "interfaces_ip"])
router_get = router_get.items()

# gns server, project id, appliance id, random project name

gns_ip = "172.28.88.11:3080"
p_id = ""
app_id = "55258fc4-42a7-4b1a-b0ca-6775f471d3cb"
r = str(random.randint(100, 999))
prj_name = "netmodel" + r


# create the gns3 project

def create_project():
    p_data = {"name": prj_name}
    p_data = json.dumps(p_data)
    p_url = "http://" + gns_ip + "/v2/projects"
    p_create = requests.post(p_url, data=p_data)
    p_id = json.loads(p_create.text)['project_id']
    return p_id


# create_node_list and create_interface_list are creating the data model
# similar to the example below

'''
Example of what is being created:
[{"name":"r1","interfaces":[{"int":"e1","ip":"192.168.12.1",
      "mask":"255.255.255.0"},{"int":"e2","ip":"192.168.13.1",
      "mask":"255.255.255.0"}]},
{"name":"r2","interfaces":[{"int":"e1","ip":"192.168.12.2",
      "mask":"255.255.255.0"},{"int":"e2","ip":"192.168.23.2",
      "mask":"255.255.255.0"}]}]
'''


def create_node_list(router_get):
    for x in router_get:

        # clear out the router list, we create a new router dictionary
        # everytime through.

        node = {}
        node["name"] = x[0]

        intf_result = x[1][0].result["interfaces_ip"]
        node["interfaces"] = create_interface_list(intf_result)

        # create network list for the router similar to interface list but
        # just networks, this is for network comparison when we add routers
        # to the link list

        node["networks"] = []
        for intf in node["interfaces"]:
            net_obj = str(ipaddress.IPv4Network(
                str(intf["ip"]) + "/" + str(intf["mask"]), strict=False))
            node["networks"].append(net_obj)

        # this node list is only used for creating the netmap.

        node_list.append(node)

    return node_list


def create_interface_list(intf_result):

    # loop through the ip interfaces and add only the ones with ipv4 addresses
    # there is lots of unpacking here so use print to find out what you have

    # k = interface names, v = ipv4 or ipv6 dict
    # y = 'ipv4' or 'ipv6' (str), z = address dict {add: {{pfx_len:int}}}
    # a = ip, b = mask

    intf_list = []
    for k, v in intf_result.items():
        for y, z in v.items():
            intf_obj = {}
            if "ipv4" in y:
                intf_obj["intf"] = k
                for a, b in z.items():
                    intf_obj["ip"] = a
                    intf_obj["mask"] = b["prefix_length"]
                intf_list.append(intf_obj)

    return intf_list


# creates a list of networks with list of node objects attached to each

def create_netmap(netlist, node_list, gns_node_list):

    # initiliaze some variables we need to append to or increment

    id = 0
    netmap = []

    # loop through each network and each node, when the a network on the node
    # list matches the network we are looping thourgh, add the node to the
    # network node list

    for network in netlist:

        # id is used for our identification if we want to delete links

        id += 1
        net_obj = {}
        net_obj["name"] = network
        net_obj["nodes"] = []
        net_obj["id"] = id

        for gns_node in gns_node_list:
            for net in gns_node.node["networks"]:
                if network == net:
                    net_obj["nodes"].append(gns_node)
        netmap.append(net_obj)

    # remove networks that have only 1 router, we don't model These

    for x in netmap[:]:
        if len(x["nodes"]) < 2:
            netmap.remove(x)

    print("These are the links we discovered: ")
    for index, value in enumerate(netmap, 1):
        print("{}. Network {} connects nodes: ".format(
            value["id"], value["name"]), end="")
        [print(node.node["name"], end=" ") for node in value["nodes"]]
        print(" ")

    # prompt user to delete any links they don't want modeled and delete the
    # ones they list. toggle it by manually setting q1 to not "y"

    # q1 = input("Would you like to delete any links? [y/n]")
    q1 = "n"
    if q1 == "y":
        print("Enter link IDs to delete, separated by space: ")
        links = list(map(int, input().split()))
        for x in links:
            netmap[:] = [d for d in netmap if d.get('id') != x]

    print("These are the links we will model: ")
    for index, value in enumerate(netmap, 1):
        print("{}. Network {} connects nodes: ".format(
            value["id"], value["name"]), end="")
        [print(node.node["name"], end=" ") for node in value["nodes"]]
        print(" ")

    return netmap


# This is called from create_netmap to retrieve list of all p2p networks. I am
# pruning /24 and /32 for now but that may change

def create_netlist(node_list):
    print("Creating the netlist...")

    netlist_init = []
    for n in node_list:
        rnets = []
        for int in n["interfaces"]:
            if int["mask"] == 24 or int["mask"] == 32:
                continue
            else:
                ip = (int["ip"], int["mask"])
                net = str(ipaddress.IPv4Network(ip, strict=False))
                rnets.append(net)
                netlist_init.append(net)
        n["networks"] = rnets
    return netlist_init


# use list comprehension to remove unneeded interfaces from
# gns nodes, these address

def prune_gns_node_intfs(gns_node_list, subnets):
    for gns_node in gns_node_list:
        gns_node.node["interfaces"] = [
            x for x
            in gns_node.node["interfaces"]
            if net_string(x["ip"], x["mask"])
            in subnets
            ]


# takes ip and mask and creates a cidr-notated network string
# (e.g. "10.1.1.0/24")

def net_string(ip, mask):
    intf_net = ipaddress.IPv4Network(str(ip) + "/" + str(mask), strict=False)
    return str(intf_net)


def create_gns_node(node, app_url, prj_url):

    # generate random graph spot for router

    x = (random.randint(0, 300))
    y = (random.randint(0, 300))
    node_data = {"x": x, "y": y}
    node_data = json.dumps(node_data)
    node_create = requests.post(app_url, data=node_data)

    # gather info about node to assign to instance attributes

    node_id = json.loads(node_create.text)['node_id']
    node_name = json.loads(node_create.text)['name']
    node_dir = json.loads(node_create.text)['node_directory']
    node_url = prj_url + "/nodes/" + node_id

    # update node name

    node_data = {"name": node.node["name"]}
    node_data = json.dumps(node_data)
    node_update = requests.put(node_url, data=node_data)

    # add id to node object, will be used when creating links

    node.add_id(node_id)
    node.add_dir(node_dir)


# this is where we give gns adapter, port and interface names to the
# remaining interfaces of the node. we do this after pruning.

def add_gns_interfaces(gns_interface, gns_port_info):
    gns_interface["gns_adapter"] = gns_port_info[0]
    gns_interface["gns_port"] = gns_port_info[1]
    gns_interface["gns_ifname"] = gns_port_info[2]


# similar to code of create_netmap but i needed gns router_id to create this

def create_linkmap(netlist, node_list, gns_node_list):

    id = 0
    linkmap = []
    for network in netlist:
        id += 1
        net_obj = {}
        net_obj["name"] = network
        net_obj["interfaces"] = []
        net_obj["id"] = id
        for gns_node in gns_node_list:
            for i in gns_node.node["interfaces"]:
                if network == net_string(i["ip"], i["mask"]):
                    intf_obj = {}
                    intf_obj["id"] = gns_node.id
                    intf_obj["adapter"] = i["gns_adapter"]
                    intf_obj["port"] = i["gns_port"]
                    net_obj["interfaces"].append(intf_obj)
        linkmap.append(net_obj)
    return linkmap


# create configs for gns router nodes based on live config and gns
# interface names

def add_node_cfg(router_get, gns_node_list):

    for x in router_get:
        for gns_node in gns_node_list:

            # this is how we match gns node object to nornir results

            if x[0] == gns_node.node["name"]:
                config = x[1][0].result["config"]
                config = config["running"]
                config_file = str(x[0]) + ".cfg"
                config_gns = str(x[0]) + "-gns.cfg"

                # this is where we write config to file

                with open(config_file, 'w') as f:
                    f.write(config)

                create_gns_config(config_file, config_gns)

                # convert interfaces to gns names

                add_int_config(gns_node, config_file, config_gns)

                # add the config filename as an attribute to the node object

                gns_node.add_config(config_gns)


def add_int_config(gns_node, config_file, config_gns):

    # loop through the interfaces to get the ip we will feed
    # to ciscoconfparse

    # config_intf = str(gns_node.node["name"]) + "-gns.cfg"
    # with open(config_intf, 'w') as f:
    #    f.write("! GENERATED BY B-TOWN\n\n")

    with open(config_gns, 'a') as f:
        for intf in gns_node.node["interfaces"]:
            ip = intf["ip"]
            parse = CiscoConfParse(config_file)
            ip_ints = parse.find_objects_w_child("^interface", ip)
            for i in ip_ints:
                # i is a <class 'ciscoconfparse.models_cisco.IOSCfgLine'>
                for j in i.ioscfg:
                    if "bfd" not in j:
                        f.write(j+"\n")
                f.write("!\n")
    # return config_gns


# update the config interface names with the gns names

def modify_cfg(gns_node):

    filename = str(gns_node.node["name"]) + "-gns.cfg"

    # create the tuple for interface name replacement then call the mod func

    for i in gns_node.node["interfaces"]:
        intfs = (i["intf"], i["gns_ifname"])
        modify_intf(filename, intfs)


def modify_intf(filename, intfs):

    with fileinput.FileInput(filename, inplace=True, backup='.bak') as file:
        for line in file:
            line = re.sub(intfs[0], intfs[1], line.rstrip())
            print(line)


def create_gns_link(link, prj_url):

    # converting the linkmap into gns nomenclature

    link_data = {}
    link_data["nodes"] = []
    for i in link["interfaces"]:
        port_obj = {}
        port_obj["adapter_number"] = i["adapter"]
        port_obj["node_id"] = i["id"]
        port_obj["port_number"] = i["port"]
        link_data["nodes"].append(port_obj)
    link_url = prj_url + "/links"
    link_data = json.dumps(link_data)
    link_create = requests.post(link_url, data=link_data)
    print(link_create.text)


# create the GNS3 project and set URLs

if p_id == "":
    p_id = create_project()
prj_url = "http://" + gns_ip + "/v2/projects/" + p_id
app_url = prj_url + "/appliances/" + app_id

# create a node list based on nornir and napalm results. We also create
# a Node instance since we have methods that will add stuff to the node

node_list = create_node_list(router_get)
for node in node_list:
    gns_node = Node(node)
    gns_node_list.append(gns_node)

# create list of networks for netmap and linkmap functions, removes duplicates

netlist = list(set(create_netlist(node_list)))

# g_id is an internal gns number used for naming the startup config

g_id = 1
for gns_node in gns_node_list:
    startup_config = "i" + str(g_id) + "_startup-config.cfg"
    create_gns_node(gns_node, app_url, prj_url)
    gns_node.add_startup(startup_config)
    g_id += 1

netmap = create_netmap(netlist, node_list, gns_node_list)

# create a list of networks that we can use in list comprehension to delete
# unneded interfaces from the gns_node objects

subnets = []
for nets in netmap:
    subnets.append(str(nets["name"]))

prune_gns_node_intfs(gns_node_list, subnets)

# loop through each gns node interface reamining and add gns port info

for gns_node in gns_node_list:
    port_num = 0
    for i in gns_node.node["interfaces"]:
        gns_adapter = 1
        gns_port = port_num
        gns_ifname = "Ethernet" + str(gns_adapter) + "/" + str(gns_port)
        gns_port_info = (gns_adapter, gns_port, gns_ifname)
        add_gns_interfaces(i, gns_port_info)
        port_num += 1
        if gns_port == 8:
            print("quitting until you add counter to adapter")
            exit()

# recreate the netmap to add gns port info

linkmap = create_linkmap(netlist, node_list, gns_node_list)

# call the function to add configs to the nodes

add_node_cfg(router_get, gns_node_list)

# update the interfaces with the gns names

for gns_node in gns_node_list:
    modify_cfg(gns_node)

print("Creating the GNS3 Link objects...")

for link in linkmap:
    create_gns_link(link, prj_url)

ssh_client = paramiko.SSHClient()
ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh_client.connect(hostname="172.28.88.11", username="gns3", password="gns3")

for gns_node in gns_node_list:
    print(gns_node.__dict__)
    ftp_client = ssh_client.open_sftp()
    remote_file = gns_node.dir + "/configs/" + gns_node.startup
    ftp_client.put(gns_node.config, remote_file)
    ftp_client.close()

# display project info to user

print("Project URL is: ", prj_url)
print("Project name is: ", prj_name)
