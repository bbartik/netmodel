#!/usr/bin/env python3

import paramiko
ssh_client = paramiko.SSHClient()
ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh_client.connect(hostname="172.28.88.11",username="gns3",password="gns3")

ftp_client = ssh_client.open_sftp()
ftp_client.put("test","test")
ftp_client.close()

