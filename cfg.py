#!/usr/bin/env python3

import json
import requests
import netmiko
import os
import pprint

from nornir.core import InitNornir
from nornir.plugins.tasks.networking import netmiko_send_command
from nornir.plugins.tasks.networking import napalm_get
from nornir.plugins.tasks import commands
from nornir.plugins.functions.text import print_result
from napalm import get_network_driver
from ciscoconfparse import CiscoConfParse
from gnsmodel import Node
from gnsmodel import Link




### PART 1: GATHER DATA AND PARSE

# initialize nornir

nr = InitNornir()

# get the config data

router_get = nr.run(task=napalm_get, getters=["config"])
router_get = router_get.items()

node_list = []
gns_node_list = []

for x in router_get:

    # create the node lists

    node = {}
    node["name"] = x[0]
    node_list.append(node)
    gns_node = Node(node, 8)
    gns_node_list.append(gns_node)

    # get each config and parse through it

    for y in nr.inventory.hosts:
        if y == x[0]:
            config = x[1][0].result["config"]
            config = config["running"]
            config_file = str(y) + ".cfg"
            with open(config_file, 'w') as f:
                f.write(config)
            parse = CiscoConfParse(config_file)
            ip_int = parse.find_objects_w_child("interface", "172.28.248.9")
            for int in ip_int:
                for line in int.ioscfg:
                    print(line)
