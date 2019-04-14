#!/usr/bin/env python3

import json
import requests
import yaml
import random

class GnsProject():
    
    def __init__(self, prj_name=''):
        '''
        Create a GNS3 project and return the project ID

        INPUT:  (Optional) prj_name allows you to name the project.  
                It will default to netmodel + random number if a name is not provided.
        '''
        #default values to build the server URL
        url_ip = 'localhost'
        url_port = '3080'
        
        #Tries to open the server config file and find the IP and port for the URL.
        #Will fall back to default value if unable to find IP or Port.
        #TODO: A way to pass in a file name and path with instance creation should be added. 
        try:
            with open('serverconfig.yaml', "r") as file_descriptor:
                data = yaml.load(file_descriptor)
        except:
            print('serverconfig.yaml not found.')
        else:
            if 'gns3' in data['server'].keys():
                if 'ip' in data['server']['gns3']:
                    url_ip = data['server']['gns3']['ip']
                if 'port' in data['server']['gns3']:
                    url_port = data['server']['gns3']['port']
        
        self.gns_url = f"http://{url_ip}:{url_port}/v2/"
        prj_url = self.gns_url + 'projects'
        
        #Pulls a list of existing project names to check for conflict.
        existing_projects = json.loads(requests.get(prj_url).content)
        
        #Creates default name if a project name is not passed in when instance is created. 
        if prj_name == '':
            prj_name = 'netmodel' + str(random.randint(100, 999))
        
        #If server is already using the project name a single random number will be added to the name.
        #Name is rechecked and a single number will be added until it is a unique project name. 
        while True:
            recheck = False
            for project in existing_projects:
                if prj_name == project['name']:
                    prj_name += str(random.randint(1, 9))
                    recheck = True
            if not recheck:
                break
        
        #Creates the project on the GNS3 server.
        p_data = json.dumps({"name": prj_name})
        p_create = requests.post(prj_url, data=p_data)
        
        #Set the project name, ID, URL.
        self.prj_name = prj_name
        self.prj_id = json.loads(p_create.text)['project_id']
        self.prj_url = f"{prj_url}/{self.prj_id}"
            
    def __str__(self):
        '''
        Return Project name and URL when the print() function is called.
        '''
        return f"Project Name: {self.prj_name}\nBase URL: {self.gns_url}\nServer URL: {self.prj_url}\nProject ID: {self.prj_id}"


if __name__ == "__main__":
    #This allows you to call this script directly for testing.  ex. - python gnsproject.py
    #TODO: This will be removed after unit test has been created. 
    project = GnsProject('Test Project')
    print(project)
