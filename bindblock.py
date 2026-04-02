import enum
import json
import requests
import re
import os
import time
from typing import List

class Config:
    def __init__(self, config_file: str):
        with open(config_file, "r") as f:
            config: dict = json.load(f)
        self.passthrough: List[str] = config.get("passthrough", [])
        adlists: List[dict] = config.get("adlists", [])
        self.adlists: List[HostList] = []
        for adlist in adlists:
            name = adlist.get("name")
            url = adlist.get("url")
            list_type_str = adlist.get("type", "DOMAINS").upper()
            list_type = ListType[list_type_str] if list_type_str in ListType else ListType.DOMAINS
            self.adlists.append(HostList(name, url, list_type))

class ListType(enum.StrEnum):
    DOMAINS = "DOMAINS"
    HOSTSFILE = "HOSTSFILE"

class HostList:

    def __init__(self, name: str, url: str, list_type: ListType = ListType.DOMAINS):
        self.name = name
        self.url = url
        self.list_type = list_type
        self.hosts = []

    def filename(self):
        return self.name + ".txt"
    
    def _download_host_list(self) -> str:
        r = requests.get(self.url)
        return r.text

    def update_host_list(self) -> str:
        text = self._download_host_list()
        with open(self.filename(), "w") as f:
            f.write(text)
        return text

    def _parse_hosts_domains(self, text: str) -> List[str]:
        print("Parsing DOMAINS format for {}".format(self.name))
        hosts = []
        expr = r'^((?!-)[A-Za-z0-9-]{1,63}(?<!-)\.)+[A-Za-z]{2,6}$'
        for host in text.split("\n"):
            if re.fullmatch(expr, host.strip()):
                hosts.append(host.strip())
        return hosts

    def _parse_hosts_file(self, text: str) -> List[str]:
        print("Parsing HOSTS file format for {}".format(self.name))
        hosts = []
        expr = r'^\d+\.\d+\.\d+\.\d+\s+(((?!-)[A-Za-z0-9-]{1,63}(?<!-)\.)+[A-Za-z]{2,6})$'
        for line in text.split("\n"):
            line = line.strip()
            if line.startswith("#") or line == "":
                continue
            match = re.fullmatch(expr, line)
            if match:
                hosts.append(match.group(1))
        return hosts

    def load(self) -> None:
        if os.path.isfile(self.filename()):
            with open(self.filename(), "r") as f:
                text = f.read()
        else:
            text = self.update_host_list()
        if self.list_type == ListType.DOMAINS:
            self.hosts = self._parse_hosts_domains(text)
        elif self.list_type == ListType.HOSTSFILE:
            self.hosts = self._parse_hosts_file(text)


class BindBlockBuilder:
    def __init__(self, config: Config):
        self.passthrough = config.passthrough
        self.host_lists = config.adlists

    def build(self, filename) -> None:
        all_hosts = set()
        for host_list in self.host_lists:
            all_hosts.update(host_list.hosts)
        rpz = """$TTL 300
@ IN SOA localhost. need.to.know.only. (
  {} ; Serial number
  60 ; Refresh every minute
  60 ; Retry every minute
  432000 ; Expire in 5 days
  60
)
@ IN NS localhost.
;
;""".format(int(time.time()))
        for host in self.passthrough:
            rpz += "\n{} IN CNAME rpz-passthru.".format(host)
            rpz += "\n*.{} IN CNAME rpz-passthru.".format(host)
        for host in all_hosts:
            rpz += "\n{} IN CNAME .".format(host)
            rpz += "\n*.{} IN CNAME .".format(host)
        with open(filename, "w") as f:
            f.write(rpz)
    
def load_config():
    return Config("config.local.json")

if __name__ == "__main__":
    config = load_config()
    for hostlist in config.adlists:
        hostlist.load()
    BindBlockBuilder(config).build("db.rpz.local")
