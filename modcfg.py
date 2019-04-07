#!/usr/bin/env python3

import json
import requests
import netmiko
import os
import pprint

from ciscoconfparse import CiscoConfParse

from gnsmodel import Node
from gnsmodel import Link
