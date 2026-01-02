# BindBlock

Generates a bind9 rpz file for adblocking based on https://www.isc.org/docs/BIND_RPZ.pdf

Uses https://v.firebog.net/hosts/AdguardDNS.txt as the default list but should work with any list of hosts. Update 

## Getting Started

1. Copy `config.json` to `config.local.json` and modify the passthrough for your domain(s).
2. Create a python virtual environment and ensure the `requests` module is installed.
3. Run `bindblock.py`
