#!/usr/bin/env python3

import fileinput
import re


def mod_intf(filename, intfs):

    with fileinput.FileInput(filename, inplace=True, backup='.bak') as file:
        for line in file:
                line = re.sub(intfs[0], intfs[1], line.rstrip())
                print(line)


for intfs in mod_list:
    mod_intf(filename, intfs)
