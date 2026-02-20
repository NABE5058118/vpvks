import os
import subprocess
import sys
from pathlib import Path

def check_wireguard_installed():
    """Check if WireGuard tools are installed"""
    try:
        result = subprocess.run(['wg', '--version'], capture_output=True, text=True, check=True)
        print(f"WireGuard tools found: {result.stdout.strip()}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("WireGuard tools not found. Please install WireGuard first.")
        print("On Ubuntu/Debian: sudo apt install wireguard")
        print("On CentOS/RHEL: sudo yum install wireguard-tools")
        print("On macOS: brew install wireguard-tools")
        return False

def generate_server_keys():
    """Generate WireGuard server keys"""
    print("Generating WireGuard server keys...")
    
    try:
        # Generate private key
        result = subprocess.run(['wg', 'genkey'], 
                              capture_output=True, text=True, check=True)
        private_key = result.stdout.strip()
        
        # Generate public key from private key
        result = subprocess.run(['echo', private_key], 
                              stdout=subprocess.PIPE)
        result = subprocess.run(['wg', 'pubkey'], 
                              stdin=result.stdout, 
                              capture_output=True, text=True, check=True)
        public_key = result.stdout.strip()
        
        print("Server keys generated successfully!")
        return private_key, public_key
    except Exception as e:
        print(f"Error generating server keys: {e}")
        return None, None

def create_server_config(private_key, public_key, server_ip="10.0.0.1", port=51820, dns="8.8.8.8"):
    """Create WireGuard server configuration"""
    print(f"Creating server configuration...")
    
    config_content = f"""[Interface]
PrivateKey = {private_key}
Address = {server_ip}/24
ListenPort = {port}
DNS = {dns}
PostUp = iptables -A FORWARD -i %i -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
PostDown = iptables -D FORWARD -i %i -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE
SaveConfig = true

# Client configurations will be added here dynamically
"""
    
    # Write to config file
    config_dir = Path("./wg_configs")
    config_dir.mkdir(exist_ok=True)
    
    server_config_path = config_dir / "wg0.conf"
    with open(server_config_path, 'w') as f:
        f.write(config_content)
    
    print(f"Server configuration saved to {server_config_path}")
    return server_config_path

def setup_wireguard():
    """Complete WireGuard setup process"""
    print("Setting up WireGuard VPN server...")
    
    # Check if WireGuard is installed
    if not check_wireguard_installed():
        return False
    
    # Generate server keys
    private_key, public_key = generate_server_keys()
    if not private_key or not public_key:
        return False
    
    print(f"Server Public Key: {public_key}")
    
    # Create server configuration
    config_path = create_server_config(private_key, public_key)
    if not config_path:
        return False
    
    print("\nWireGuard setup completed!")
    print(f"Configuration file: {config_path}")
    print("\nTo start WireGuard server:")
    print(f"sudo wg-quick up {config_path}")
    print("\nTo stop WireGuard server:")
    print(f"sudo wg-quick down {config_path}")
    
    return True

if __name__ == "__main__":
    success = setup_wireguard()
    if not success:
        print("WireGuard setup failed!")
        sys.exit(1)
    else:
        print("WireGuard setup completed successfully!")