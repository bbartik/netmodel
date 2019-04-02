
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


### PART 1: GATHER DATA


# initialize nornir and router list

nr = InitNornir() 
router_list = []
gns_router_list = []

# get all the interface data and store it in the intfs variable

intfs = nr.run(task=napalm_get, getters=["interfaces_ip"])
intfs = intfs.items()


# FUNCTION 1: This function creates an ipv4 interface list per router, each
# object in the list is a dictionary with "interface", "address", "mask" keys

def create_interface_list(intf_result):

    # loop through the items and add only the ones with ipv4 addresses
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



for x in intfs:
    
    # clear out the router list, we create a new router dictionary
    # everytime through. First k/v is the name, second k/v is the interface
    # list which is created using the function above.

    router = {}
    router["name"] = x[0]
    
    intf_result = x[1][0].result
    router["interfaces"] = create_interface_list(intf_result)
    
    router_list.append(router)
    
    gns_router = Node(router["name"], 8)
    gns_router_list.append(gns_router)



### PART 2: Create network list ("Links") and add routers to it


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

# removes duplicates in netlist by converting to setm then back to list:

netlist = list(set(create_netlist(router_list)))


# creates the netmap which is a list of dicts containing name of the network
# and a list of routers (nodes)

id = 0
for network in netlist:
    id += 1
    net_obj = {}
    net_obj["name"] = network
    net_obj["nodes"] = []
    net_obj["id"] = id
    for y in router_list:
        for z in y["networks"]:
            if network == z:
                net_obj["nodes"].append(y["name"])
    netmap.append(net_obj)


### PART 3: Prompt and prune list

for x in netmap[:]:
    if len(x["nodes"]) < 2:
        netmap.remove(x)    

print("These are the links we discovered: ")
for index, value in enumerate(netmap, 1):
    print("{}. Network {} connects nodes: {}".format(value["id"], value["name"], value["nodes"]))

q1 = input("Would you like to delete any links? [y/n]")

if q1 == "y":
    print("Enter link IDs to delete, separated by space: ")
    links = list(map(int, input().split()))

    for x in links:
        netmap[:] = [d for d in netmap if d.get('id') != x]

print("These are the links we will model: ")
for index, value in enumerate(netmap, 1):
    print("{}. Network {} connects nodes: {}".format(value["id"], value["name"], value["nodes"]))
    

### PART 4: CREATE THE GNS3 NODE AND LINK MODEL OBJECTS

print("Verifying the router list: ")
for gr in gns_router_list:
    print(gr.name)

     
print("Creating the GNS3 Link objects...")
linklist = []
for x in netmap:
    link_obj = Link(x["name"], routers=x["nodes"])
    linklist.append(link_obj)
for x in linklist:
    print(x.name)


### PART 5: CREATE THE GNS3 TOPOLOGY

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
    p_url = "http://10.0.0.10:3080/v2/projects"
    p_create = requests.post(p_url, data=p_data)
    p_id = json.loads(p_create.text)['project_id']
    return p_id

if p_id == "" :
    p_id = create_project()

# set project url so we can append to it easily

prj_url = "http://10.0.0.10:3080/v2/projects/" + p_id
print("Project URL is: ", prj_url)

# create routers from appliance templates

app_url = prj_url + "/appliances/daa5a71f-6269-428a-bfd4-b7a4e7f43940"

def create_gns_routers(app_url, prj_url):
    for rtr in gns_router_list:
       
        # generate random graph spot for router

        x = (random.randint(0,300))
        y = (random.randint(0,300))
        r_data = {"x": x, "y": y}
        r_data = json.dumps(r_data)
        rtr_create = requests.post(app_url, data=r_data)
        print(rtr_create.text)
          
        # update node name

        node_id = json.loads(rtr_create.text)['node_id']
        node_url = prj_url + "/nodes/" + node_id
        print(node_url)
        node_data = {"name": rtr.name}
        node_data = json.dumps(node_data)
        node_update = requests.put(node_url, data=node_data)
        print(node_update.text)
        
create_gns_routers(app_url, prj_url)







