#!/usr/bin/env python3

import json
import requests
import yaml
import random

class GnsProject():
    
    def __init__(self, prj_name=''):
        #default values to build the server URL
        url_ip = 'localhost'
        url_port = '3080'
        
        #Creates default name if a project name is not passed in when class is created. 
        if prj_name == '':
            self.prj_name = 'netmodel' + str(random.randint(100, 999))
        else:
            self.prj_name = prj_name
        
        #Tries to open the server config file and find the IP and port for the URL.
        #Will fall back to default value if unable to find IP or Port.
        #TODO: Should add a way to pass in file name and path with instance creation. 
        try:
            with open('serverconfig.yaml', "r") as file_descriptor:
                data = yaml.load(file_descriptor)
        except:
            print('serverconfig.yaml not found.')
        else:
            if data['server']['gns3']:
                if data['server']['gns3']['ip']:
                    url_ip = data['server']['gns3']['ip']
                if data['server']['gns3']['port']:
                    url_port = data['server']['gns3']['port']
        self.gns_url = f"http://{url_ip}:{url_port}/v2/"
    
    def __str__(self):
        '''
        Return Project name and server URL when the print() function is called.
        '''
        return f"Project Name: {self.prj_name}\nServer URL: {self.gns_url}"

    def create_project(self):
        '''
        Create a GNS3 project and return the project ID
        '''
        #Creates the URL
        prj_url = self.gns_url + 'projects'
        
        #Pulls a list of existing project names to check for conflict.
        existing_projects = json.loads(requests.get(prj_url).content)
        
        #If server is already using the project name a single random number will be added to name.
        #Name is rechecked.  A single number will be added until it is a unique project name. 
        while True:
            recheck = False
            for project in existing_projects:
                if self.prj_name == project['name']:
                    self.prj_name += str(random.randint(1, 9))
                    recheck = True
            if not recheck:
                break
        
        #Creates the project on the GNS3 server.
        p_data = json.dumps({"name": self.prj_name})
        p_create = requests.post(self.gns_url + 'projects', data=p_data)
        
        #Returns the project ID.
        return json.loads(p_create.text)['project_id']

#Allows you to call this script directly for testing.  ex. - python gnsproject.py
#TODO: This will be removed after unit test has been created. 
if __name__ == "__main__":
    project = GnsProject('Test Project')
    prj_id = project.create_project()
    print(project)
    print(f"Project ID: {prj_id}")
