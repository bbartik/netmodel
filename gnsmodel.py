
class Node():

    def __init__(self, node):
        self.node = node
        self.intfs = []

    def add_intf(self, intf_mod):
        mod, intfs = (self.intf_mod)
        for x in range(intfs):
            intf_name = "Ethernet" + str(mod) + "/" + str(x)
            intf_obj = self.Interface(intf_name)
            self.intfs.append(intf_obj)
        return self.intfs
        self.intfs = self.add_intf()

    def add_id(self, node_id):
        self.id = node_id

    def add_startup(self, startup_config):
        self.startup = startup_config

    def add_config(self, config):
        self.config = str(config)

    def del_intf(self, ip):
        self.intfs.pop(ip)

    def add_dir(self, node_dir):
        self.dir = node_dir

class Interface():

    def __init__(self, adapter, port, node_id):
        self.adapter = adapter
        self.port = port
        self.node_id = node_id


class Link():

    def __init__(self, name, *args, **kwargs):
        self.name = name
        self.nodes = kwargs.get("routers")
        self.interfaces = []

    def add_intf(self, interface):
        self.interfaces.append(interface)
