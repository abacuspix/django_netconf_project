from os import getenv

from jnpr.junos import Device


class JunosDevice:

    """Base class for Junos devices.

    :attr:`hostname`: router hostname
    :attr:`user`: user for logging into `hostname`
    :attr:`password`: password for logging into `hostname`
    :attr:`timeout`: time to wait for a response
    :attr:`connection`: connection to `hostname`
    """

    @property
    def arp_table(self):
        """
        A list of ARP entries.

        :returns: ARP entries
        :rtype: list
        """
        table = []
        old_table = self._connection.rpc.get_arp_table_information(vpn=self.vpn)
        for old_entry in old_table:
            if old_entry.tag != 'arp-table-entry':
                continue
            entry = dict(ip_address=old_entry.findtext('ip-address').strip(),
                         interface=old_entry.findtext('interface-name').strip(),
                         hostname=self.hostname.strip(), vpn=self.vpn,
                         mac_address=old_entry.findtext('mac-address').strip())
            table.append(entry)
        return table

    @property
    def route_table(self):
        """
        A list of routes bound to current route-tables

        :return: list
        """
        table = []
        root = self._connection.rpc.get_route_information(all=True)
        for route_table in root:
            table_name = route_table.findtext('table-name')
            for route in route_table.findall('rt'):
                entry = dict((elt.tag, elt.text) for elt in route.iter() if not len(elt) and elt.text is not None)
                entry['table_name'] = table_name
                table.append(entry)
        return table

    @property
    def interface_list(self):
        """
        A list of interfaces with thier parameters

        :return: list
        """
        table = []
        root = self._connection.rpc.get_interface_information()
        for phy_int in root:
            entry = dict(
                (elt.tag, elt.text.strip()) for elt in phy_int.iter() if not len(elt) and elt.text is not None)
            entry['int-type'] = 'physical-interface'
            table.append(entry)
            for log_int in phy_int.findall('logical-interface'):
                entry = dict(
                    (elt.tag, elt.text.strip()) for elt in log_int.iter() if not len(elt) and elt.text is not None)
                entry['int-type'] = 'logical-interface'
                table.append(entry)
        return table

    @property
    def route_instance_list(self):
        """
        A list of routing instances with parameters

        :return: list
        """
        table = []
        root = self._connection.rpc.get_instance_information(detail=True)
        for route_inst in root:
            entry = {}
            for elt in route_inst.findall('*'):
                if not len(elt):
                    entry[elt.tag] = elt.text
                if elt.tag == 'instance-interface':
                    entry['instance-interface_list'] = list(int_elt.text for int_elt in elt)
                if elt.tag == 'instance-rib':
                    entry['instance-rib_list'] = list(rib_elt.text for rib_elt in elt if rib_elt.tag == 'irib-name')
            table.append(entry)
        return table

    @property
    def facts(self):
        return self._facts

    def __init__(self, *args, **kwargs):
        self.hostname = args[0] if len(args) else kwargs.get('host')
        self.user = kwargs.get('user', getenv('USER'))
        self.password = kwargs.get('password')
        self.timeout = kwargs.get('timeout')
        self.vpn = kwargs.get('vpn', 'default')

    def connect(self):
        """Connect to a device.
        :returns: a connection to a Juniper Networks device.
        :rtype: ``Device``
        """
        dev = Device(host=self.hostname, user=self.user, passwd=self.password)
        dev.open()
        dev.timeout = self.timeout
        self._connection = dev
        self._facts = dev.facts
        return self

    def disconnect(self):
        if self._connection:
            self._connection.close()
