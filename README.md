# 🌐 WANem

WANem (Wide Area Network Emulator) is a simple and efficient Flask-based application that allows you to easily set up and control traffic conditions such as bandwidth, latency, packet loss, packet corruption, and more on a network interface using `tc` and `netem` utilities.

It's particularly useful for testing SD-WAN and other network scenarios.

## ✨ Features

- 🔍 **Network Interface Details**: Retrieve detailed information about network interfaces including MAC address, MTU, speed, duplex, status, IPv4 address, netmask, and VLAN info.
- 🔄 **IP Forwarding**: Enable or disable IP forwarding on the system.
- 🛠️ **DNS Configuration**: View and modify DNS server settings directly through the API.

## 🚀 Getting Started

### 📋 Prerequisites

- 🐍 Python 3.6+
- ⚙️ Flask

### 💻 Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/WANem.git
   cd WANem
   ```

2. Create a virtual environment and activate it:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install the required Python packages:
   ```bash
   pip install -r requirements.txt
   ```

4. Run the application:
   ```bash
   python app.py
   ```

   The application will start on `http://0.0.0.0:5000/`.

### 🔌 API Endpoints

#### 🌐 Retrieve Network Interface Information

- **Endpoint**: `/api/network-info`
- **Method**: `GET`
- **Description**: Get detailed information about all network interfaces.
- **Response Example**:
  ```json
  {
    "status": "success",
    "interfaces": {
      "eth0": {
        "mac_address": "00:20:91:AB:34:56",
        "mtu": "1500",
        "speed": "1000Mb/s",
        "duplex": "Full",
        "status": "up",
        "ipv4": {
          "address": "192.168.1.2",
          "netmask": "24"
        },
        "vlan": {
          "id": "1"
        }
      }
    }
  }
  ```

#### 🔄 Enable/Disable IP Forwarding

- **Endpoint**: `/api/ip-forwarding`
- **Method**: `GET` or `POST`
- **Description**: View or modify the IP forwarding status.
- **Request Body Example (for POST)**:
  ```json
  {
    "action": "enable"
  }
  ```
- **Response Example**:
  ```json
  {
    "status": "IP forwarding enabled"
  }
  ```

#### 📡 Retrieve DNS Information

- **Endpoint**: `/api/dns-info`
- **Method**: `GET`
- **Description**: Retrieve the current DNS servers configured in `/etc/resolv.conf`.
- **Response Example**:
  ```json
  {
    "status": "success",
    "dns_servers": [
      "8.8.8.8",
      "8.8.4.4"
    ]
  }
  ```

#### ⚙️ Update DNS Servers

- **Endpoint**: `/api/dns-setup`
- **Method**: `POST`
- **Description**: Update the DNS servers in `/etc/resolv.conf`.
- **Request Body Example**:
  ```json
  {
    "dns_servers": [
      "8.8.8.8",
      "8.8.4.4"
    ]
  }
  ```
- **Response Example**:
  ```json
  {
    "status": "success",
    "message": "DNS servers updated successfully."
  }
  ```

### 📝 Logging

Logging is configured to output messages to the console. You can adjust the logging level and format as needed.

### 🤝 Contributing

Feel free to fork this project and submit pull requests. For major changes, please open an issue first to discuss what you would like to change.

### 📄 License

This project is licensed under the MIT License. See the `LICENSE` file for more details.
