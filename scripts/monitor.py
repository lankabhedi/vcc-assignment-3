#!/usr/bin/env python3
"""
=============================================================================
Resource Monitoring Script with Auto-Scaling Trigger
Assignment 3: VCC - Auto-scaling Local VM to Cloud
Author: Samnit Mehandiratta (M25AI2087), IIT Jodhpur
Email: m25ai2087@iitj.ac.in
=============================================================================

This script monitors CPU and RAM usage on the local VM and triggers
auto-scaling to GCP when resource usage exceeds 75%.
"""

import os
import sys
import time
import json
import logging
import subprocess
from datetime import datetime
from pathlib import Path

# Configuration
CONFIG = {
    "cpu_threshold": 75.0,        # CPU threshold percentage
    "ram_threshold": 75.0,        # RAM threshold percentage
    "check_interval": 5,          # Check every 5 seconds
    "consecutive_triggers": 3,    # Number of consecutive triggers before scaling
    "log_file": "monitor.log",
    "state_file": "monitor_state.json",
    "cooldown_period": 300,       # 5 minutes cooldown after scaling
    "gcp_project": "vm-scaling-assignment",  # GCP project ID
    "gcp_region": "us-central1",
    "gcp_zone": "us-central1-a",
    "instance_name": "autoscale-vm",
    "machine_type": "e2-medium",
}

# Setup logging
def setup_logging():
    """Configure logging to both file and console."""
    log_dir = Path(__file__).parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / CONFIG["log_file"]),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()


class ResourceMonitor:
    """Monitor system resources (CPU, RAM, Disk)."""
    
    def __init__(self):
        self.cpu_count = os.cpu_count() or 1
    
    def get_cpu_usage(self) -> float:
        """
        Get current CPU usage percentage.
        Works on Linux using /proc/stat.
        """
        try:
            # Read /proc/stat twice with a small delay
            def read_cpu_stats():
                with open('/proc/stat', 'r') as f:
                    line = f.readline()
                    parts = line.split()
                    # user, nice, system, idle, iowait, irq, softirq, steal
                    return [int(x) for x in parts[1:9]]
            
            stats1 = read_cpu_stats()
            time.sleep(0.5)
            stats2 = read_cpu_stats()
            
            # Calculate deltas
            deltas = [stats2[i] - stats1[i] for i in range(len(stats1))]
            
            # Total CPU time
            total = sum(deltas)
            # Idle time
            idle = deltas[3] + deltas[4]  # idle + iowait
            
            if total == 0:
                return 0.0
            
            cpu_usage = ((total - idle) / total) * 100
            return round(cpu_usage, 2)
        
        except Exception as e:
            logger.error(f"Error getting CPU usage: {e}")
            # Fallback: try using top command
            try:
                result = subprocess.run(
                    ["top", "-bn1"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                for line in result.stdout.split('\n'):
                    if 'Cpu(s)' in line or '%Cpu' in line:
                        parts = line.split(',')
                        for part in parts:
                            if 'us' in part.lower() or 'user' in part.lower():
                                usage = float(part.split(':')[1].strip().split()[0])
                                return round(usage, 2)
            except:
                pass
            return 0.0
    
    def get_ram_usage(self) -> float:
        """
        Get current RAM usage percentage.
        Works on Linux using /proc/meminfo.
        """
        try:
            with open('/proc/meminfo', 'r') as f:
                meminfo = {}
                for line in f:
                    parts = line.split(':')
                    if len(parts) == 2:
                        key = parts[0].strip()
                        value = int(parts[1].strip().split()[0])
                        meminfo[key] = value
            
            total = meminfo.get('MemTotal', 0)
            available = meminfo.get('MemAvailable', meminfo.get('MemFree', 0))
            
            if total == 0:
                return 0.0
            
            used = total - available
            ram_usage = (used / total) * 100
            return round(ram_usage, 2)
        
        except Exception as e:
            logger.error(f"Error getting RAM usage: {e}")
            # Fallback: try using free command
            try:
                result = subprocess.run(
                    ["free", "-m"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                lines = result.stdout.split('\n')
                for line in lines:
                    if line.startswith('Mem:'):
                        parts = line.split()
                        total = float(parts[1])
                        used = float(parts[2])
                        if total > 0:
                            return round((used / total) * 100, 2)
            except:
                pass
            return 0.0
    
    def get_disk_usage(self) -> float:
        """Get root disk usage percentage."""
        try:
            stat = os.statvfs('/')
            total = stat.f_blocks * stat.f_frsize
            free = stat.f_bfree * stat.f_frsize
            
            if total == 0:
                return 0.0
            
            used = total - free
            disk_usage = (used / total) * 100
            return round(disk_usage, 2)
        
        except Exception as e:
            logger.error(f"Error getting disk usage: {e}")
            return 0.0
    
    def get_all_metrics(self) -> dict:
        """Get all resource metrics."""
        return {
            "timestamp": datetime.now().isoformat(),
            "cpu_usage": self.get_cpu_usage(),
            "ram_usage": self.get_ram_usage(),
            "disk_usage": self.get_disk_usage(),
            "cpu_count": self.cpu_count
        }


class AutoScaler:
    """Handle auto-scaling to GCP."""
    
    def __init__(self, config: dict):
        self.config = config
        self.project = config.get("gcp_project") or os.getenv("GOOGLE_CLOUD_PROJECT")
        self.region = config.get("gcp_region", "us-central1")
        self.zone = config.get("gcp_zone", "us-central1-a")
    
    def check_gcp_auth(self) -> bool:
        """Check if GCP authentication is configured."""
        try:
            result = subprocess.run(
                ["gcloud", "auth", "list"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0 and "*" in result.stdout
        except Exception as e:
            logger.error(f"GCP auth check failed: {e}")
            return False
    
    def scale_to_gcp(self, reason: str) -> bool:
        """
        Create a VM instance on GCP.
        Returns True if scaling was successful.
        """
        if not self.project:
            logger.error("GCP project not configured. Set GOOGLE_CLOUD_PROJECT env var.")
            return False
        
        instance_name = f"{self.config['instance_name']}-{int(time.time())}"
        machine_type = self.config.get("machine_type", "e2-medium")
        
        logger.info(f"Initiating scale to GCP: {instance_name}")
        logger.info(f"Project: {self.project}, Zone: {self.zone}, Machine: {machine_type}")
        
        try:
            # Create GCP VM instance
            cmd = [
                "gcloud", "compute", "instances", "create", instance_name,
                "--project", self.project,
                "--zone", self.zone,
                "--machine-type", machine_type,
                "--network-interface", "network-tier=PREMIUM,stack-type=IPV4_ONLY,subnet=default",
                "--metadata", "google-logging-enabled=true",
                "--maintenance-policy", "MIGRATE",
                "--provisioning-model", "STANDARD",
                "--create-disk", f"auto-delete=yes,boot=yes,device-name={instance_name},"
                               f"image=projects/debian-cloud/global/images/family/debian-11,"
                               f"mode=rw,size=10,type=projects/{self.project}/zones/{self.zone}/diskTypes/pd-balanced",
                "--no-shielded-secure-boot",
                "--shielded-vtpm",
                "--shielded-integrity-monitoring",
                "--labels", "autoscale=true",
                "--reservation-affinity", "any"
            ]
            
            logger.info(f"Executing: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0:
                logger.info(f"Successfully created GCP instance: {instance_name}")
                logger.info(f"External IP will be assigned shortly. Reason: {reason}")
                return True
            else:
                logger.error(f"GCP instance creation failed: {result.stderr}")
                return False
        
        except subprocess.TimeoutExpired:
            logger.error("GCP instance creation timed out")
            return False
        except Exception as e:
            logger.error(f"Error scaling to GCP: {e}")
            return False
    
    def create_instance_template(self) -> bool:
        """Create an instance template for managed instance group (optional)."""
        template_name = "autoscale-template"
        
        try:
            cmd = [
                "gcloud", "compute", "instance-templates", "create", template_name,
                "--project", self.project,
                "--machine-type", self.config.get("machine_type", "e2-medium"),
                "--image-family", "debian-11",
                "--image-project", "debian-cloud"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            return result.returncode == 0
        
        except Exception as e:
            logger.error(f"Error creating instance template: {e}")
            return False


class MonitorState:
    """Persist and manage monitor state."""
    
    def __init__(self, state_file: str):
        self.state_file = Path(state_file)
        self.state = self.load()
    
    def load(self) -> dict:
        """Load state from file."""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {
            "consecutive_high_usage": 0,
            "last_scale_time": None,
            "total_scales": 0,
            "alerts_triggered": 0
        }
    
    def save(self):
        """Save state to file."""
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)
    
    def reset_consecutive(self):
        """Reset consecutive counter."""
        self.state["consecutive_high_usage"] = 0
        self.save()
    
    def increment_consecutive(self):
        """Increment consecutive counter."""
        self.state["consecutive_high_usage"] += 1
        self.save()
        return self.state["consecutive_high_usage"]
    
    def record_scale(self):
        """Record a scaling event."""
        self.state["last_scale_time"] = datetime.now().isoformat()
        self.state["total_scales"] += 1
        self.save()
    
    def is_in_cooldown(self, cooldown_seconds: int) -> bool:
        """Check if we're in cooldown period."""
        if not self.state["last_scale_time"]:
            return False
        
        last_scale = datetime.fromisoformat(self.state["last_scale_time"])
        elapsed = (datetime.now() - last_scale).total_seconds()
        return elapsed < cooldown_seconds


def main():
    """Main monitoring loop."""
    logger.info("=" * 70)
    logger.info("Resource Monitor with Auto-Scaling")
    logger.info("Author: Samnit Mehandiratta (M25AI2087), IIT Jodhpur")
    logger.info("=" * 70)
    
    # Initialize components
    monitor = ResourceMonitor()
    scaler = AutoScaler(CONFIG)
    state = MonitorState(Path(__file__).parent.parent / "config" / CONFIG["state_file"])
    
    # Check GCP authentication
    if scaler.check_gcp_auth():
        logger.info("GCP authentication verified")
    else:
        logger.warning("GCP not authenticated. Run: gcloud auth login")
        logger.warning("Auto-scaling will not work until GCP is configured")
    
    logger.info(f"Monitoring started. Check interval: {CONFIG['check_interval']}s")
    logger.info(f"CPU Threshold: {CONFIG['cpu_threshold']}%, RAM Threshold: {CONFIG['ram_threshold']}%")
    logger.info("-" * 70)
    
    try:
        while True:
            # Get current metrics
            metrics = monitor.get_all_metrics()
            
            # Log metrics
            logger.info(
                f"CPU: {metrics['cpu_usage']:5.1f}% | "
                f"RAM: {metrics['ram_usage']:5.1f}% | "
                f"Disk: {metrics['disk_usage']:5.1f}%"
            )
            
            # Check thresholds
            cpu_exceeded = metrics['cpu_usage'] >= CONFIG['cpu_threshold']
            ram_exceeded = metrics['ram_usage'] >= CONFIG['ram_threshold']
            
            if cpu_exceeded or ram_exceeded:
                state.increment_consecutive()
                consecutive = state.state["consecutive_high_usage"]
                
                reason = []
                if cpu_exceeded:
                    reason.append(f"CPU={metrics['cpu_usage']}%")
                if ram_exceeded:
                    reason.append(f"RAM={metrics['ram_usage']}%")
                
                logger.warning(
                    f"Threshold exceeded! ({', '.join(reason)}) "
                    f"Consecutive: {consecutive}/{CONFIG['consecutive_triggers']}"
                )
                
                # Check if we should trigger scaling
                if consecutive >= CONFIG['consecutive_triggers']:
                    if not state.is_in_cooldown(CONFIG["cooldown_period"]):
                        logger.critical("=" * 50)
                        logger.critical("AUTO-SCALE TRIGGERED!")
                        logger.critical(f"Reason: {', '.join(reason)}")
                        logger.critical("=" * 50)
                        
                        # Trigger scaling
                        if scaler.scale_to_gcp(reason=', '.join(reason)):
                            state.record_scale()
                            logger.info("Scaling successful. Entering cooldown period.")
                        else:
                            logger.error("Scaling failed. Check GCP configuration.")
                        
                        state.reset_consecutive()
                    else:
                        logger.info("In cooldown period. Skipping scale trigger.")
            else:
                state.reset_consecutive()
            
            # Wait for next check
            time.sleep(CONFIG["check_interval"])
    
    except KeyboardInterrupt:
        logger.info("\nMonitor stopped by user")
    except Exception as e:
        logger.error(f"Monitor error: {e}")
        raise


if __name__ == "__main__":
    main()
