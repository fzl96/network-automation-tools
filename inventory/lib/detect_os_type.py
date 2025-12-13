#!/usr/bin/env python3
import logging
import paramiko
from typing import Optional, Tuple, Dict
from netmiko import SSHDetect, BaseConnection, ConnectHandler
from paramiko import AuthenticationException
import socket

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

class OSDetector:
    """Optimized OS detector using Netmiko with faster detection."""
    
    # Device type priority based on your network (most common first)
    DEVICE_PRIORITY = [
        'cisco_ios',        # Cisco IOS - most common
        'cisco_nxos',       # Cisco NX-OS - for your NX-OS devices
        'cisco_xe',         # Cisco IOS-XE
        'cisco_xr',         # Cisco IOS-XR
        'arista_eos',       # Arista EOS
        'juniper_junos',    # Juniper JunOS
        'cisco_asa',        # Cisco ASA
        'hp_procurve',      # HP ProCurve
    ]
    
    # Quick detection patterns for common devices
    QUICK_PATTERNS = {
        'cisco_ios': [r'[Cc]isco [Ii][Oo][Ss]', r'ios software', r'ios-xe'],
        'cisco_nxos': [r'[Nn]x-[Oo][Ss]', r'nexus', r'NX-OS'],
        'cisco_xe': [r'ios-xe', r'xe software'],
        'cisco_xr': [r'ios xr', r'xr software'],
        'arista_eos': [r'arista', r'eos'],
        'juniper_junos': [r'junos', r'juniper'],
    }
    
    def __init__(self, ip: str, username: Optional[str] = None, password: Optional[str] = None):
        self.ip = ip
        self.username = username
        self.password = password
        self.connection = None
        
    def detect(self) -> Tuple[str, Optional[str]]:
        """Main detection method with optimized flow."""
        
        # First, try APIC detection (special case)
        apic_result = self._detect_apic()
        if apic_result:
            return apic_result
        
        # Try fast detection with common device types first
        fast_result = self._fast_detection()
        if fast_result and fast_result[0] not in ["AUTH_FAIL", "UNREACHABLE"]:
            return fast_result
        
        # If fast detection failed, try comprehensive detection
        return self._comprehensive_detection()
    
    def _detect_apic(self) -> Optional[Tuple[str, str]]:
        """Detect APIC by parsing 'show version' output."""
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            client.connect(
                hostname=self.ip,
                username=self.username,
                password=self.password,
                timeout=8,
                banner_timeout=8,
                auth_timeout=8
            )
            
            logging.debug(f"Connected to {self.ip} for APIC check")
            
            # Execute command to get version info
            stdin, stdout, stderr = client.exec_command("show version", timeout=5)
            output = stdout.read().decode("utf-8", errors="ignore")
            client.close()
            
            # Parse output for APIC controller info
            hostname = self._parse_apic_output(output)
            
            if hostname:
                logging.info(f"Detected APIC on {self.ip} - Hostname: {hostname}")
                return "apic", hostname
            
            # Fallback detection using keywords
            if self._is_apic_by_keywords(output):
                logging.info(f"Detected APIC via keyword match on {self.ip}")
                return "apic", "apic-controller"
                
            return None
            
        except AuthenticationException:
            return "AUTH_FAIL", None # type: ignore
        except Exception as e:
            logging.debug(f"APIC check error on {self.ip}: {e}")
            return None

    def _parse_apic_output(self, output: str) -> Optional[str]:
            """Parse APIC 'show versions' output to extract hostname."""
            for line in output.splitlines():
                line = line.strip()
                low = line.lower()

                # Skip empty lines, headers (Standard & NX-OS), and separators
                if (
                    not line
                    or low.startswith("role")
                    or low.startswith("node type")
                    or all(ch in "- " for ch in line)
                ):
                    continue

                parts = line.split()

                # We need at least 4 columns to match either format
                if len(parts) < 4:
                    continue

                # Check if this line contains controller info
                if parts[0].lower() == "controller":
                    if len(parts) >= 5:
                        name_tokens = parts[3:-1]
                        return " ".join(name_tokens) if name_tokens else parts[3]

                    elif len(parts) == 4:
                        return parts[2]

            return None
    
    def _is_apic_by_keywords(self, output: str) -> bool:
        """Check if output contains APIC-related keywords."""
        apic_keywords = [
            "cisco apic",
            "application policy infrastructure controller",
            "aci fabric",
            "aci version"
        ]
        
        lowered = output.lower()
        return any(keyword in lowered for keyword in apic_keywords)

    def _fast_detection(self) -> Optional[Tuple[str, str]]:
        """Fast detection by trying only the most likely device types."""
        
        # Try the top 2-3 most common device types first
        for device_type in self.DEVICE_PRIORITY[:3]:  # Only try first 3
            result = self._quick_device_check(device_type)
            if result:
                return result
        
        return None
    
    def _quick_device_check(self, device_type: str) -> Optional[Tuple[str, str]]:
        """Quick check for a specific device type."""
        try:
            # Use minimal timeout for quick checks
            device = {
                'device_type': device_type,
                'host': self.ip,
                'username': self.username,
                'password': self.password,
                'secret': self.password,
                'timeout': 3,      # Reduced timeout
                'session_timeout': 5,
                'global_delay_factor': 0.5,  # Reduced delay
                'fast_cli': True,  # Enable fast mode if supported
            }
            
            # Special port adjustments
            if device_type == 'juniper_junos':
                device['port'] = 22  # Use SSH instead of NETCONF for speed
            
            conn = ConnectHandler(**device)
            conn.enable()
            
            # Quick version command
            output = conn.send_command_timing("show version", delay_factor=0.5, max_loops=5)
            
            # Quick pattern matching
            if self._match_device_pattern(device_type, output): # type: ignore
                hostname = self._get_quick_hostname_from_conn(conn, device_type)
                conn.disconnect()
                logging.info(f"Quick detected {device_type} on {self.ip} - Hostname: {hostname}")
                return device_type, hostname
            
            conn.disconnect()
            
        except Exception as e:
            error_msg = str(e).lower()
            if any(auth_term in error_msg for auth_term in ["auth", "password", "authentication"]):
                return "AUTH_FAIL", None # type: ignore
        
        return None
    
    def _match_device_pattern(self, device_type: str, output: str) -> bool:
        """Quick pattern matching for device identification."""
        if device_type in self.QUICK_PATTERNS:
            patterns = self.QUICK_PATTERNS[device_type]
            output_lower = output.lower()
            return any(pattern.lower() in output_lower for pattern in patterns)
        return False
    
    def _get_quick_hostname_from_conn(self, conn: BaseConnection, device_type: str) -> str:
        """Get hostname quickly."""
        try:
            # Device-specific quick hostname commands
            quick_hostname_cmds = {
                'cisco_ios': 'show run | i hostname',
                'cisco_nxos': 'show hostname',
                'cisco_xe': 'show run | i hostname',
                'arista_eos': 'show hostname',
            }
            
            cmd = quick_hostname_cmds.get(device_type, 'show hostname')
            output = conn.send_command_timing(cmd, delay_factor=0.5, max_loops=3)
            
            # Quick parsing
            lines = output.strip().splitlines() # type: ignore
            for line in lines:
                if 'hostname' in line.lower():
                    parts = line.split()
                    if len(parts) > 1:
                        return parts[1].strip()
                elif line.strip() and not line.startswith('#'):
                    return line.strip()
            
            return "Unknown"
            
        except:
            return "Unknown"
    
    def _get_quick_hostname(self, ip: str, username: str, password: str) -> Optional[str]:
        """Get hostname via quick SSH connection."""
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            client.connect(
                hostname=ip,
                username=username,
                password=password,
                timeout=3,
                banner_timeout=3,
                auth_timeout=3
            )
            
            # Try common hostname commands
            for cmd in ["show hostname", "hostname"]:
                try:
                    stdin, stdout, stderr = client.exec_command(cmd, timeout=2)
                    output = stdout.read().decode("utf-8", errors="ignore").strip()
                    if output:
                        client.close()
                        return output
                except:
                    continue
            
            client.close()
            
        except:
            pass
        
        return None
    
    def _comprehensive_detection(self) -> Tuple[str, Optional[str]]:
        """Comprehensive detection when quick methods fail."""
        try:
            # Use optimized SSHDetect
            device = {
                'device_type': 'autodetect',
                'host': self.ip,
                'username': self.username,
                'password': self.password,
                'timeout': 8,           # Balanced timeout
                'auth_timeout': 8,
                'banner_timeout': 8,
                'session_timeout': 12,
                'global_delay_factor': 1,
            }
            
            guesser = SSHDetect(**device)
            
            # Reduce number of device types to try
            guesser.device_type_priority = self.DEVICE_PRIORITY[:5]  # Only try top 5
            
            best_match = guesser.autodetect()
            
            if best_match:
                # Get hostname with detected type
                device['device_type'] = best_match
                conn = ConnectHandler(**device)
                
                # Quick hostname retrieval
                hostname = self._get_quick_hostname_from_conn(conn, best_match)
                
                conn.disconnect()
                
                logging.info(f"Detected {best_match} on {self.ip} - Hostname: {hostname}")
                return best_match, hostname
            
            # If autodetect fails, check if device is reachable
            if self._is_port_open(22):
                return "UNKNOWN_SSH", None
            else:
                return "UNREACHABLE", None
            
        except AuthenticationException:
            return "AUTH_FAIL", None
        except Exception as e:
            error_msg = str(e).lower()
            logging.debug(f"Detection failed for {self.ip}: {error_msg[:100]}")
            
            if any(auth_term in error_msg for auth_term in ["auth", "password", "authentication"]):
                return "AUTH_FAIL", None
            elif any(conn_term in error_msg for conn_term in ["connection refused", "timeout", "unreachable"]):
                return "UNREACHABLE", None
            
            return "UNKNOWN", None
    
    def _is_port_open(self, port: int) -> bool:
        """Check if a port is open."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((self.ip, port))
            sock.close()
            return result == 0
        except:
            return False


def detect_os_type(ip: str, username: Optional[str] = None, password: Optional[str] = None) -> Tuple[str, Optional[str]]:
    """
    Detect the operating system type of a network device.
    
    Args:
        ip: IP address of the device
        username: SSH username
        password: SSH password
    
    Returns:
        Tuple containing (os_type, hostname) or (error_code, None)
        Error codes: "AUTH_FAIL", "UNREACHABLE", "UNKNOWN_SSH"
    """
    detector = OSDetector(ip, username, password)
    return detector.detect()


# Optional: Add a caching mechanism for even faster detection
_detection_cache = {}

def detect_os_type_cached(ip: str, username: Optional[str] = None, password: Optional[str] = None) -> Tuple[str, Optional[str]]:
    """Cached version of OS detection for repeated queries."""
    cache_key = f"{ip}:{username}"
    
    if cache_key in _detection_cache:
        return _detection_cache[cache_key]
    
    result = detect_os_type(ip, username, password)
    
    # Only cache successful detections
    if result[0] not in ["AUTH_FAIL", "UNREACHABLE", "UNKNOWN_SSH"]:
        _detection_cache[cache_key] = result
    
    return result