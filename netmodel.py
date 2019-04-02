
import ipaddress
import pprint
import json
import requests
import random

from nornir.core import InitNornir
from nornir.plugins.tasks.networking import netmiko_send_command
from nornir.plugins.functions.text import print_result
from nornir.plugins.tasks.networking import napalm_get
from napalm import get_network_driver

from gnsmodel import Node
from gnsmodel import Link




### PART 1: GATHER DATA AND CREATE NODE LISTS



# initialize nornir and router list

nr = InitNornir() 
node_list = []
gns_node_list = []

# get all the interface data and store it in the intfs variable

router_get = nr.run(task=napalm_get, getters=["interfaces_ip"])
router_get = router_get.items()


# This function creates an ipv4 interface list per router, each
# object in the list is a dictionary with "int", "ip", and "mask" keys
# The list is created per router using the for loop

'''
Example of what is being created:
r1 = {"name":"r1","interfaces":[{"int":"e1","ip":"192.168.12.1",
      "mask":"255.255.255.0"},{"int":"e2","ip":"192.168.13.1",
      "mask":"255.255.255.0"}]}
r2 = {"name":"r2","interfaces":[{"int":"e1","ip":"192.168.12.2",
      "mask":"255.255.255.0"},{"int":"e2","ip":"192.168.23.2",
      "mask":"255.255.255.0"}]}
'''

def create_interface_list(intf_result):

    # loop through the ip interfaces and add only the ones with ipv4 addresses
    # there is lots of unpacking here so use print to find out what you have
    
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

for x in router_get:
    
    # clear out the router list, we create a new router dictionary
    # everytime through. First k/v is the name, second k/v is the interface
    # list which is created using the function above.

    node = {}
    node["name"] = x[0]
    
    intf_result = x[1][0].result
    node["interfaces"] = create_interface_list(intf_result) 

    # create network list for the router similar to interface list but just networks,
    # this is for network comparison when we add routers to the link list

    node["networks"] = []
    for intf in node["interfaces"]:
        net_obj = str(ipaddress.IPv4Network(str(intf["ip"]) + "/" + str(intf["mask"]), strict=False))
        node["networks"].append(net_obj)
   
    node_list.append(node)
        
    # create the gns node, might move this to a different location
    
    gns_node = Node(node, 8)
    gns_node_list.append(gns_node)
    


### PART 2: CREATE THE NETWORK/LINK LIST AND ADD ROUTERS TO EACH



network = {"networks":[]}
netmap = []


# FUNCTION: This creates the network lists based on interface subnets
# The list is then used to create a "map" of which routers are on each net

def create_netlist(node_list):
    netlist_init = []
    for n in node_list:
        rnets = []
        for int in n["interfaces"]:
            if int["mask"] == 24:
                continue
            else:
                ip = (int["ip"], int["mask"])
                net = str(ipaddress.IPv4Network(ip, strict = False))
                rnets.append(net)
                netlist_init.append(net)
        n["networks"] = rnets
    return netlist_init

# removes duplicates in netlist by converting to setm then back to list:

netlist = list(set(create_netlist(node_list)))

# creates the netmap which is a list of dicts containing name of the network
# and a list of routers (nodes)

id = 0
for network in netlist:

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



### PART 3: PROMPT USER TO PRUNE LIST

# to do: auto-prune that shit for /24s

for x in netmap[:]:
    if len(x["nodes"]) < 2:
        netmap.remove(x)    

print("These are the links we discovered: ")
for index, value in enumerate(netmap, 1):
    print("{}. Network {} connects nodes: ".format(value["id"], value["name"]), end="")
    [print(node.node["name"], end=" ") for node in value["nodes"]]
    print(" ")

q1 = input("Would you like to delete any links? [y/n]")

if q1 == "y":
    print("Enter link IDs to delete, separated by space: ")
    links = list(map(int, input().split()))

    for x in links:
        netmap[:] = [d for d in netmap if d.get('id') != x]

print("These are the links we will model: ")
for index, value in enumerate(netmap, 1):
    print("{}. Network {} connects nodes: ".format(value["id"], value["name"]), end="")
    [print(node.node["name"], end=" ") for node in value["nodes"]]
    print(" ")


### PART 4: VERIFY THE GNS3 NODE OBJECTS

print("Verifying the router list: ")
for node in gns_node_list:
    print(node.node["name"])
  


### PART 5: CREATE THE GNS3 PROJECT AND ADD NODES

gns_ip = "172.28.88.11:3080"

# option to manually set project id

p_id = ""

# create project name with string and random number

r = str(random.randint(100,999))
prj_name = "netmodel" + r
print(prj_name)

# Create a project

def create_project():
    p_data = {"name": prj_name}
    p_data = json.dumps(p_data)
    p_url = "http://" + gns_ip + "/v2/projects"
    p_create = requests.post(p_url, data=p_data)
    p_id = json.loads(p_create.text)['project_id']
    return p_id

if p_id == "" :
    p_id = create_project()

# set project url so we can append to it easily

prj_url = "http://" + gns_ip + "/v2/projects/" + p_id

# create routers from appliance templates

app_url = prj_url + "/appliances/fd975642-7656-4c6c-a8db-89e8f15f0006"

def create_gns_node(node, app_url, prj_url):
       
    # generate random graph spot for router

    x = (random.randint(0,300))
    y = (random.randint(0,300))
    node_data = {"x": x, "y": y}
    node_data = json.dumps(node_data)
    node_create = requests.post(app_url, data=node_data)
      
    # update node name

    node_id = json.loads(node_create.text)['node_id']
    node_url = prj_url + "/nodes/" + node_id
    node_data = {"name": node.node["name"]}
    node_data = json.dumps(node_data)
    node_update = requests.put(node_url, data=node_data)

    # add id to node object, will be used when creating links
 
    node.add_id(node_id)
 
for node in gns_node_list:
    create_gns_node(node, app_url, prj_url)



### PART 6: CREATE THE GNS3 LINKS

# create the GNS link likst from the network list we created earlier, we
# do it this way because we may want to keep the network list as is for future

print("Creating the GNS3 Link objects...")
gns_link_list = []
for net in netmap:
    link_obj = Link(net["name"], routers=net["nodes"])
    gns_link_list.append(link_obj)
for link in gns_link_list:
    print(link.name)
    for node in link.nodes:
        print(node.node["name"], node.id)

# this function creates the actual links on the gns server

def create_gns_link(link, port_num, prj_url):
    
    # get the node data for the link and put it in the data object
    # NOTE: need to figure out how to fill these variables
    
    link_data = {}
    link_data["nodes"] = []
    for x in link.nodes:
        port_obj = {}
        port_obj["adapter_number"] = 1
        port_obj["node_id"] = x.id
        port_obj["port_number"] = port_num
        link_data["nodes"].append(port_obj)    
    link_url = prj_url + "/links"
    link_data = json.dumps(link_data)
    link_create = requests.post(link_url, data=link_data)
    print(link_create.text)

port_num = 0
for link in gns_link_list:
    create_gns_link(link, port_num, prj_url)  
    port_num += 1  


# display project info to user

print("Project URL is: ", prj_url)
print("Project name is: ", prj_name)

