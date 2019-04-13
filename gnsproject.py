#!/usr/bin/env python3

import json
import requests

from gnsmodel import Node
from gnsmodel import Link

def create_project(prj_name, gns_url):
    '''
    Create a GNS3 project and return the project ID
    
    INPUT: Project name and the URL for the GNS3 Server
    Return: Project ID
    '''
    p_data = json.dumps({"name": prj_name})
    p_create = requests.post(gns_url, data=p_data)
    return json.loads(p_create.text)['project_id']

# gns_url = "http://10.0.75.1:3080"
# p_id = create_project('test_project', gns_url)
# prj_url = gns_url + "/v2/projects/" + p_id
# app_url = prj_url + "/appliances/55258fc4-42a7-4b1a-b0ca-6775f471d3cb"
# print(prj_url)
# print(app_url)
