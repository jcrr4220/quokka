from ipaddress import ip_network
import socket
import subprocess
from datetime import datetime
from time import sleep

from quokka.models.apis import set_host

from python_arptable import get_arp_table
from pprint import pprint


def learn_mac_addresses():
    arp_table_list = get_arp_table()

    arp_table = dict()
    for arp_entry in arp_table_list:

        if arp_entry["HW address"] != "00:00:00:00:00:00":
            arp_table[arp_entry["IP address"]] = arp_entry["HW address"]

    pprint(arp_table)
    return arp_table


class DiscoverTask:

    def __init__(self):
        self.terminate = False

    def set_terminate(self):
        self.terminate = True
        print(self.__class__.__name__, "Terminate pending")

    def discover(self, interval):

        while True and not self.terminate:

            mac_addresses = learn_mac_addresses()

            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            my_ip_addr = s.getsockname()[0]
            print(f"My IP address is {my_ip_addr}")

            found_hosts = []
            subnet = ip_network(my_ip_addr + "/24", False)
            for ip_addr in subnet.hosts():

                if self.terminate:
                    break

                print(f"--- discovery pinging {str(ip_addr)}")
                try:
                    ping_output = subprocess.check_output(["ping", "-c1", "-n", "-i0.5", "-W2", str(ip_addr)])
                except subprocess.CalledProcessError:
                    continue

                print(f"--- found one: {str(ip_addr)}")
                try:
                    hostname = socket.gethostbyaddr(str(ip_addr))
                except socket.error:
                    hostname = (str(ip_addr), [], [str(ip_addr)])

                if hostname:
                    print(f"--- found its hostname: {hostname}")

                host = dict()
                host["name"] = hostname[0]
                host["ip_address"] = str(ip_addr)
                host["mac_address"] = mac_addresses[str(ip_addr)] if str(ip_addr) in mac_addresses else ""
                host["availability"] = True
                host["last_heard"] = str(datetime.now())

                set_host(host)
                found_hosts.append({"hostname": hostname, "ip": str(ip_addr)})

            for active_host in found_hosts:
                print(f"host: {active_host['hostname'][0]:30}   ip: {str(active_host['ip']):16}")

            for _ in range(0, int(interval/10)):
                sleep(10)
                if self.terminate:
                    break

        print("...gracefully exiting discovery")