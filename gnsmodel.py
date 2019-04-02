
class Node():

    def __init__(self, node, num_intfs):

        self.node = node
        self.num_intfs = num_intfs
        self.intfs = []
        self.intfs = self.add_intf()

    def add_intf(self):
        
        for x in range(self.num_intfs):
            intf_name = "E" + str(x)
            self.intfs.append(intf_name)
        return self.intfs

    def add_id(self, node_id):
        self.id = node_id

class Link():

    def __init__(self, name, *args, **kwargs):

        self.name = name
        self.nodes = kwargs.get("routers")
