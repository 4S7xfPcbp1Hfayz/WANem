from flask import Flask, jsonify, request, abort
import subprocess
import re
import os
import ipaddress
import logging

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def run_command(command, shell=False):
    """Execute a command and return its output and error (if any)."""
    try:
        result = subprocess.run(command, shell=shell, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return result.stdout.decode('utf-8').strip(), None
    except subprocess.CalledProcessError as e:
        logging.error(f"Command '{command}' failed: {e.stderr.decode('utf-8').strip()}")
        return None, f"Command '{command}' failed: {e.stderr.decode('utf-8').strip()}"

def get_interface_details(interface):
    """Retrieve details for a given network interface."""
    if not os.path.exists(f"/sys/class/net/{interface}"):
        return {"error": f"Interface {interface} does not exist"}, None

    commands = {
        "mac_address": f"cat /sys/class/net/{interface}/address",
        "mtu": f"cat /sys/class/net/{interface}/mtu",
        "speed": f"ethtool {interface} | grep 'Speed'",
        "duplex": f"ethtool {interface} | grep 'Duplex'",
        "status": f"cat /sys/class/net/{interface}/operstate",
        "ipv4": f"ip addr show {interface}"
    }

    details = {}
    errors = {}

    for key, command in commands.items():
        output, error = run_command(command, shell=True)
        if error:
            errors[key] = error
            details[key] = "Error"
        else:
            details[key] = output

    if errors:
        return details, errors

    # Process specific fields
    speed_value = "Unknown"
    duplex_value = "Unknown"
    ipv4_address = "Unknown"
    netmask = "Unknown"

    if details["speed"]:
        speed_match = re.search(r'Speed:\s+(\d+\s*\w+)', details["speed"])
        if speed_match:
            speed_value = speed_match.group(1).strip()

    if details["duplex"]:
        duplex_match = re.search(r'Duplex:\s+(\w+)', details["duplex"])
        if duplex_match:
            duplex_value = duplex_match.group(1).strip()

    ipv4_lines = details["ipv4"].splitlines()
    for line in ipv4_lines:
        if 'inet ' in line:
            parts = line.split()
            address_with_netmask = parts[1]
            address, netmask = address_with_netmask.split('/')
            ipv4_address = address

    vlan_info = get_vlan_info(interface)

    return {
        "mac_address": details["mac_address"],
        "mtu": details["mtu"],
        "speed": speed_value,
        "duplex": duplex_value,
        "status": details["status"],
        "ipv4": {
            "address": ipv4_address,
            "netmask": netmask
        },
        "vlan": vlan_info
    }, None

def get_vlan_info(interface):
    """Retrieve VLAN tagging information for a given interface."""
    vlan_info = {}
    vlan_command = f"ip -d link show {interface}"
    output, error = run_command(vlan_command, shell=True)
    if error:
        return {"error": error}
    
    if "vlan protocol 802.1Q" in output:
        vlan_lines = [line for line in output.splitlines() if "vlan protocol 802.1Q" in line]
        for line in vlan_lines:
            vlan_id_match = re.search(r'id (\d+)', line)
            if vlan_id_match:
                vlan_id = vlan_id_match.group(1)
                vlan_info["id"] = vlan_id
    else:
        vlan_info = {"id": "1"}

    return vlan_info

@app.route('/api/network-info', methods=['GET'])
def network_info():
    """Retrieve information about all network interfaces."""
    interfaces_command = "ls /sys/class/net"
    output, error = run_command(interfaces_command, shell=True)

    if error:
        logging.error(error)
        return jsonify({"error": error}), 500

    interfaces = output.split()
    responses = {}
    for interface in interfaces:
        if os.path.isdir(f"/sys/class/net/{interface}") and interface != "lo":
            details, details_error = get_interface_details(interface)
            if details_error:
                responses[interface] = {"error": details_error}
            else:
                responses[interface] = details

    return jsonify({"status": "success", "interfaces": responses}), 200

@app.route('/api/ip-forwarding', methods=['GET', 'POST'])
def ip_forwarding():
    """Retrieve or modify the IP forwarding status."""
    if request.method == 'POST':
        action = request.json.get('action')
        if action not in ['enable', 'disable']:
            return jsonify({"error": "Invalid action. Must be 'enable' or 'disable'"}), 400

        value = '1' if action == 'enable' else '0'
        command = f"echo {value} > /proc/sys/net/ipv4/ip_forward"
        _, error = run_command(command, shell=True)
        if error:
            return jsonify({"error": error}), 500

        return jsonify({"status": f"IP forwarding {action}d"}), 200

    ip_forwarding_command = "cat /proc/sys/net/ipv4/ip_forward"
    result, error = run_command(ip_forwarding_command, shell=True)

    if error:
        return jsonify({"error": error}), 500

    ip_forwarding_status = result
    status_message = "enabled" if ip_forwarding_status == "1" else "disabled"

    return jsonify({"ip_forwarding": status_message}), 200

@app.route('/api/dns-info', methods=['GET'])
def dns_info():
    """Retrieve the current DNS servers from /etc/resolv.conf."""
    try:
        with open('/etc/resolv.conf', 'r') as f:
            lines = f.readlines()

        dns_servers = [line.split()[1] for line in lines if line.startswith('nameserver')]

        return jsonify({"status": "success", "dns_servers": dns_servers}), 200
    except Exception as e:
        logging.error(str(e))
        return jsonify({"error": str(e)}), 500

@app.route('/api/dns-setup', methods=['POST'])
def dns_setup():
    """Update the DNS servers in /etc/resolv.conf."""
    dns_servers = request.json.get('dns_servers')
    
    if not dns_servers or not isinstance(dns_servers, list):
        return jsonify({"error": "Invalid data. Provide a list of DNS servers."}), 400

    for server in dns_servers:
        try:
            ipaddress.ip_address(server)
        except ValueError:
            return jsonify({"error": f"Invalid DNS server address: {server}"}), 400

    try:
        with open('/etc/resolv.conf', 'w') as f:
            for server in dns_servers:
                f.write(f"nameserver {server}\n")
        return jsonify({"status": "success", "message": "DNS servers updated successfully."}), 200
    except Exception as e:
        logging.error(str(e))
        return jsonify({"error": str(e)}), 500

@app.errorhandler(404)
def not_found(error):
    """Custom 404 error handler."""
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    """Custom 500 error handler."""
    return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
