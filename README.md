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
- 🐧 Debian (or Debian-based system)
- 🛠️ `tc` and `netem` utilities

### 💻 Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/4S7xfPcbp1Hfayz/WANem.git
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

You can view the API documentation for WANem using Swagger at the following link:

[Swagger API Documentation](https://editor.swagger.io/?url=https://raw.githubusercontent.com/4S7xfPcbp1Hfayz/WANem/main/openapi.yaml)

### 📝 Logging

Logging is configured to output messages to the console. You can adjust the logging level and format as needed.

### 🤝 Contributing

Feel free to fork this project and submit pull requests. For major changes, please open an issue first to discuss what you would like to change.

### 📄 License

This project is licensed under the MIT License. See the `LICENSE` file for more details.
