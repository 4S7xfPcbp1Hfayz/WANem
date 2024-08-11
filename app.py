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

@app.route('/api/set-ip', methods=['POST'])
def set_ip():
    """Set IP address and netmask for a specific network interface."""
    data = request.json
    interface = data.get('interface')
    ip_address = data.get('ip_address')
    netmask = data.get('netmask')

    # Validate input
    if not interface or not ip_address or not netmask:
        return jsonify({"error": "Interface, IP address, and netmask are required"}), 400

    # Check if the interface exists
    if not os.path.exists(f"/sys/class/net/{interface}"):
        return jsonify({"error": f"Interface {interface} does not exist"}), 400

    try:
        ipaddress.ip_address(ip_address)
    except ValueError:
        return jsonify({"error": f"Invalid IP address: {ip_address}"}), 400

    try:
        ipaddress.IPv4Network(f"0.0.0.0/{netmask}")
    except ValueError:
        return jsonify({"error": f"Invalid netmask: {netmask}"}), 400

    # Set the IP address and netmask
    command = f"ip addr add {ip_address}/{netmask} dev {interface}"
    _, error = run_command(command, shell=True)
    if error:
        return jsonify({"error": error}), 500

    # Bring the interface up (if it's down)
    command = f"ip link set {interface} up"
    _, error = run_command(command, shell=True)
    if error:
        return jsonify({"error": error}), 500

    return jsonify({"status": "success", "message": f"IP address and netmask set for {interface}"}), 200

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

def validate_traffic_control_params(bandwidth, delay, jitter, loss, corrupt):
    """Validate traffic control parameters."""
    if bandwidth and not re.match(r'^\d+[KMG]?bit$', bandwidth):
        return "Invalid bandwidth format."
    if delay and not re.match(r'^\d+ms$', delay):
        return "Invalid delay format."
    if jitter and not re.match(r'^\d+ms$', jitter):
        return "Invalid jitter format."
    if loss and not re.match(r'^\d+%$', loss):
        return "Invalid loss format."
    if corrupt and not re.match(r'^\d+%$', corrupt):
        return "Invalid corrupt format."
    return None

@app.route('/api/traffic-control', methods=['POST'])
def traffic_control():
    """Set up traffic control conditions on a specific network interface."""
    data = request.json
    interface = data.get('interface')
    bandwidth = data.get('bandwidth')
    delay = data.get('delay')
    jitter = data.get('jitter')
    loss = data.get('loss')
    corrupt = data.get('corrupt')

    if not interface:
        return jsonify({"error": "Interface is required"}), 400

    # Validate traffic control parameters
    validation_error = validate_traffic_control_params(bandwidth, delay, jitter, loss, corrupt)
    if validation_error:
        return jsonify({"error": validation_error}), 400

    # Check if the interface exists
    if not os.path.exists(f"/sys/class/net/{interface}"):
        return jsonify({"error": f"Interface {interface} does not exist"}), 400

    # Command to retrieve traffic control settings
    tc_show_command = f"tc qdisc show dev {interface}"
    output, error = run_command(tc_show_command, shell=True)

    if error:
        # If the error indicates that no such file or directory, it means no qdisc was found, which is acceptable
        if "No such file or directory" in error:
            clear_error = None
        else:
            return jsonify({"error": error}), 500
    else:
        # Check if any traffic control rules are applied
        if "netem" in output:
            # Command to clear traffic control settings
            clear_command = f"tc qdisc del dev {interface} root"
            _, clear_error = run_command(clear_command, shell=True)
            if clear_error:
                # Handle specific errors or general errors here
                if "No such file or directory" in clear_error:
                    clear_error = None  # Ignore if no rules were found to delete
                else:
                    return jsonify({"error": clear_error}), 500
        else:
            clear_error = None

    # Build new traffic control command
    tc_command = f"tc qdisc add dev {interface} root netem"
    if bandwidth:
        tc_command += f" rate {bandwidth}"
    if delay:
        tc_command += f" delay {delay}"
    if jitter:
        tc_command += f" {jitter}"
    if loss:
        tc_command += f" loss {loss}"
    if corrupt:
        tc_command += f" corrupt {corrupt}"

    # Apply the new traffic control settings
    _, error = run_command(tc_command, shell=True)
    if error:
        return jsonify({"error": error}), 500

    return jsonify({"status": "success", "message": "Traffic control applied"}), 200

@app.route('/api/traffic-control/clear', methods=['POST'])
def clear_traffic_control():
    """Clear traffic control settings on a specific network interface."""
    data = request.json
    interface = data.get('interface')

    if not interface:
        return jsonify({"error": "Interface is required"}), 400

    # Check if the interface exists
    if not os.path.exists(f"/sys/class/net/{interface}"):
        return jsonify({"error": f"Interface {interface} does not exist"}), 400

    # Command to retrieve traffic control settings
    tc_show_command = f"tc qdisc show dev {interface}"
    output, error = run_command(tc_show_command, shell=True)
    if error:
        return jsonify({"error": error}), 500

    # Check if any traffic control rules are applied
    if "netem" not in output:
        return jsonify({"status": "success", "message": "No traffic control setup on this interface"}), 200

    # Command to clear traffic control settings
    tc_clear_command = f"tc qdisc del dev {interface} root"
    _, error = run_command(tc_clear_command, shell=True)
    if error:
        return jsonify({"error": error}), 500

    return jsonify({"status": "success", "message": "Traffic control cleared"}), 200

@app.route('/api/traffic-control/info', methods=['GET'])
def traffic_control_info():
    """Retrieve the current traffic control settings for a specific network interface."""
    interface = request.args.get('interface')

    if not interface:
        return jsonify({"error": "Interface is required"}), 400

    # Check if the interface exists
    if not os.path.exists(f"/sys/class/net/{interface}"):
        return jsonify({"error": f"Interface {interface} does not exist"}), 400

    # Command to retrieve traffic control settings
    tc_show_command = f"tc qdisc show dev {interface}"
    output, error = run_command(tc_show_command, shell=True)
    if error:
        return jsonify({"error": error}), 500

    # Check if any traffic control rules are applied
    if "noqueue" in output:
        return jsonify({"status": "success", "message": "No traffic control setup on this interface"}), 200

    # Parse the output to provide meaningful information
    tc_details = {}
    lines = output.splitlines()
    for line in lines:
        if "netem" in line:
            # Extract delay, loss, bandwidth, jitter, and corrupt
            delay_match = re.search(r'delay (\d+ms)', line)
            loss_match = re.search(r'loss (\d+)%', line)
            rate_match = re.search(r'rate (\S+)', line)
            jitter_match = re.search(r'jitter (\d+ms)', line)
            corrupt_match = re.search(r'corrupt (\d+)%', line)

            if delay_match:
                tc_details['delay'] = delay_match.group(1)
            if loss_match:
                tc_details['loss'] = loss_match.group(1)
            if rate_match:
                tc_details['bandwidth'] = rate_match.group(1)
            if jitter_match:
                tc_details['jitter'] = jitter_match.group(1)
            if corrupt_match:
                tc_details['corrupt'] = corrupt_match.group(1)
    
    return jsonify({"status": "success", "interface": interface, "traffic_control": tc_details}), 200

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
