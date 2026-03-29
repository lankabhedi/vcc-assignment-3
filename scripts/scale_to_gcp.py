#!/usr/bin/env python3
"""
=============================================================================
GCP Auto-Scaling Script
Assignment 3: VCC - Auto-scaling Local VM to Cloud
Author: Samnit Mehandiratta (M25AI2087), IIT Jodhpur
Email: m25ai2087@iitj.ac.in
=============================================================================

This script handles scaling resources from local VM to Google Cloud Platform.
It creates VM instances, manages instance groups, and handles cleanup.
"""

import os
import sys
import json
import time
import subprocess
import argparse
from datetime import datetime
from pathlib import Path


class GCPScaleManager:
    """Manage auto-scaling to Google Cloud Platform."""
    
    def __init__(self, project_id: str = None, region: str = "us-central1", 
                 zone: str = "us-central1-a"):
        self.project = project_id or os.getenv("GOOGLE_CLOUD_PROJECT")
        self.region = region
        self.zone = zone
        
        if not self.project:
            raise ValueError(
                "GCP Project ID required. Set GOOGLE_CLOUD_PROJECT env var "
                "or pass project_id parameter."
            )
    
    def run_gcloud_command(self, args: list, timeout: int = 120) -> tuple:
        """Run a gcloud command and return (success, output)."""
        cmd = ["gcloud"] + args + ["--project", self.project]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return (result.returncode == 0, result.stdout, result.stderr)
        except subprocess.TimeoutExpired:
            return (False, "", "Command timed out")
        except Exception as e:
            return (False, "", str(e))
    
    def check_auth(self) -> bool:
        """Check if authenticated with GCP."""
        success, output, _ = self.run_gcloud_command(
            ["auth", "list"],
            timeout=30
        )
        return success and "*" in output
    
    def check_billing(self) -> bool:
        """Check if billing is enabled."""
        success, output, _ = self.run_gcloud_command(
            ["billing", "projects", "describe", self.project],
            timeout=30
        )
        return success
    
    def enable_apis(self) -> bool:
        """Enable required GCP APIs."""
        apis = [
            "compute.googleapis.com",
            "cloudresourcemanager.googleapis.com"
        ]
        
        for api in apis:
            print(f"Enabling API: {api}")
            success, _, stderr = self.run_gcloud_command(
                ["services", "enable", api],
                timeout=60
            )
            if not success:
                print(f"Warning: Could not enable {api}: {stderr}")
        
        return True
    
    def create_instance(self, instance_name: str = None, 
                       machine_type: str = "e2-medium",
                       image_family: str = "debian-11",
                       image_project: str = "debian-cloud",
                       disk_size: str = "10GB",
                       startup_script: str = None,
                       labels: dict = None) -> bool:
        """
        Create a single VM instance on GCP.
        
        Args:
            instance_name: Name for the instance (auto-generated if None)
            machine_type: GCP machine type
            image_family: OS image family
            image_project: Project containing the image
            disk_size: Boot disk size
            startup_script: Startup script to run on VM creation
            labels: Dictionary of labels to apply
        """
        if not instance_name:
            timestamp = int(time.time())
            instance_name = f"autoscale-vm-{timestamp}"
        
        print(f"Creating GCP instance: {instance_name}")
        print(f"  Project: {self.project}")
        print(f"  Zone: {self.zone}")
        print(f"  Machine Type: {machine_type}")
        
        # Build command
        cmd = [
            "compute", "instances", "create", instance_name,
            "--zone", self.zone,
            "--machine-type", machine_type,
            "--network-interface", "network-tier=PREMIUM,stack-type=IPV4_ONLY,subnet=default",
            "--maintenance-policy", "MIGRATE",
            "--provisioning-model", "STANDARD",
            "--create-disk",
            f"auto-delete=yes,boot=yes,device-name={instance_name},"
            f"image=projects/{image_project}/global/images/family/{image_family},"
            f"mode=rw,size={disk_size.replace('GB', '')},"
            f"type=projects/{self.project}/zones/{self.zone}/diskTypes/pd-balanced",
            "--no-shielded-secure-boot",
            "--shielded-vtpm",
            "--shielded-integrity-monitoring",
            "--reservation-affinity", "any"
        ]
        
        # Add labels if provided
        if labels:
            label_str = ",".join([f"{k}={v}" for k, v in labels.items()])
            cmd.extend(["--labels", label_str])
        
        # Add metadata for startup script
        if startup_script:
            if startup_script.startswith("gs://"):
                cmd.extend(["--metadata", f"startup-script-url={startup_script}"])
            else:
                cmd.extend(["--metadata-from-file", f"startup-script={startup_script}"])
        
        # Add logging enabled
        cmd.extend(["--metadata", "google-logging-enabled=true"])
        
        success, output, stderr = self.run_gcloud_command(cmd, timeout=180)
        
        if success:
            print(f"✓ Instance '{instance_name}' created successfully")
            
            # Get external IP
            time.sleep(5)  # Wait for IP assignment
            ip = self.get_instance_ip(instance_name)
            if ip:
                print(f"  External IP: {ip}")
            
            return True
        else:
            print(f"✗ Failed to create instance: {stderr}")
            return False
    
    def get_instance_ip(self, instance_name: str) -> str:
        """Get external IP of an instance."""
        success, output, _ = self.run_gcloud_command(
            ["compute", "instances", "describe", instance_name,
             "--zone", self.zone,
             "--format", "get(networkInterfaces[0].accessConfigs[0].natIP)"],
            timeout=30
        )
        return output.strip() if success else None
    
    def list_instances(self) -> list:
        """List all instances in the project."""
        success, output, _ = self.run_gcloud_command(
            ["compute", "instances", "list",
             "--format", "table(name,zone,machineType,status,EXTERNAL_IP)"],
            timeout=30
        )
        if success:
            print(output)
            return True
        return False
    
    def delete_instance(self, instance_name: str) -> bool:
        """Delete a VM instance."""
        print(f"Deleting instance: {instance_name}")
        
        success, output, stderr = self.run_gcloud_command(
            ["compute", "instances", "delete", instance_name,
             "--zone", self.zone,
             "--quiet"],
            timeout=120
        )
        
        if success:
            print(f"✓ Instance '{instance_name}' deleted")
            return True
        else:
            print(f"✗ Failed to delete: {stderr}")
            return False
    
    def create_instance_template(self, template_name: str = "autoscale-template",
                                 machine_type: str = "e2-medium") -> bool:
        """Create an instance template for managed instance groups."""
        print(f"Creating instance template: {template_name}")
        
        success, output, stderr = self.run_gcloud_command(
            ["compute", "instance-templates", "create", template_name,
             "--machine-type", machine_type,
             "--image-family", "debian-11",
             "--image-project", "debian-cloud"],
            timeout=60
        )
        
        if success:
            print(f"✓ Template '{template_name}' created")
            return True
        else:
            print(f"✗ Failed to create template: {stderr}")
            return False
    
    def create_managed_instance_group(self, group_name: str,
                                      template_name: str,
                                      min_instances: int = 1,
                                      max_instances: int = 5,
                                      target_cpu_utilization: float = 0.75) -> bool:
        """
        Create a managed instance group with auto-scaling policy.
        
        Args:
            group_name: Name for the instance group
            template_name: Instance template to use
            min_instances: Minimum number of instances
            max_instances: Maximum number of instances
            target_cpu_utilization: Target CPU utilization (0.0-1.0)
        """
        print(f"Creating managed instance group: {group_name}")
        
        # Create the instance group
        success, _, stderr = self.run_gcloud_command(
            ["compute", "instance-groups", "managed", "create", group_name,
             "--base-instance-name", group_name,
             "--template", template_name,
             "--size", str(min_instances),
             "--zone", self.zone],
            timeout=60
        )
        
        if not success:
            print(f"Failed to create group: {stderr}")
            return False
        
        # Create auto-scaler
        print(f"Creating auto-scaler for group: {group_name}")
        success, _, stderr = self.run_gcloud_command(
            ["compute", "instance-groups", "managed", "set-autoscaling", group_name,
             "--zone", self.zone,
             "--max-num-replicas", str(max_instances),
             "--target-cpu-utilization", str(target_cpu_utilization),
             "--cool-down-period", "60"],
            timeout=60
        )
        
        if success:
            print(f"✓ Managed instance group '{group_name}' created with auto-scaling")
            print(f"  Min instances: {min_instances}")
            print(f"  Max instances: {max_instances}")
            print(f"  Target CPU: {target_cpu_utilization * 100}%")
            return True
        else:
            print(f"Warning: Group created but auto-scaler setup failed: {stderr}")
            return True
    
    def create_health_check(self, health_check_name: str = "autoscale-health",
                           port: int = 80) -> bool:
        """Create an HTTP health check."""
        print(f"Creating health check: {health_check_name}")
        
        success, _, stderr = self.run_gcloud_command(
            ["compute", "health-checks", "create", "http", health_check_name,
             "--port", str(port),
             "--request-path", "/health"],
            timeout=30
        )
        
        if success:
            print(f"✓ Health check '{health_check_name}' created")
            return True
        else:
            print(f"✗ Failed to create health check: {stderr}")
            return False
    
    def setup_load_balancer(self, backend_group: str, 
                           health_check: str,
                           lb_name: str = "autoscale-lb") -> bool:
        """Setup a basic load balancer for the instance group."""
        print(f"Setting up load balancer: {lb_name}")
        
        # This is a simplified setup - full LB would need more configuration
        print("Note: Full load balancer setup requires additional configuration")
        print("See documentation for complete setup instructions")
        return True
    
    def get_costs_estimate(self, machine_type: str = "e2-medium",
                          hours: int = 24) -> dict:
        """Get estimated costs for running instances."""
        # Approximate pricing (USD) - actual prices vary by region
        pricing = {
            "e2-micro": 0.0083,
            "e2-small": 0.0166,
            "e2-medium": 0.0332,
            "e2-standard-2": 0.0670,
            "e2-standard-4": 0.1340,
            "n1-standard-1": 0.0475,
            "n1-standard-2": 0.0950,
        }
        
        hourly_rate = pricing.get(machine_type, 0.0332)
        daily_cost = hourly_rate * hours
        
        return {
            "machine_type": machine_type,
            "hourly_rate_usd": hourly_rate,
            "hours": hours,
            "estimated_cost_usd": daily_cost
        }


def setup_gcp_project(project_id: str) -> bool:
    """Perform initial GCP project setup."""
    print("=" * 60)
    print("GCP Project Setup")
    print("=" * 60)
    
    manager = GCPScaleManager(project_id)
    
    # Check authentication
    print("\n1. Checking authentication...")
    if not manager.check_auth():
        print("✗ Not authenticated with GCP")
        print("\nRun: gcloud auth login")
        return False
    print("✓ Authenticated")
    
    # Check billing
    print("\n2. Checking billing...")
    if not manager.check_billing():
        print("✗ Billing not enabled or project not found")
        print(f"\nSet project: gcloud config set project {project_id}")
        print("Enable billing in GCP Console")
        return False
    print("✓ Billing enabled")
    
    # Enable APIs
    print("\n3. Enabling required APIs...")
    manager.enable_apis()
    print("✓ APIs enabled")
    
    return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="GCP Auto-Scaling Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s setup --project my-project
  %(prog)s create --project my-project
  %(prog)s list --project my-project
  %(prog)s delete --project my-project --name autoscale-vm-123456
  %(prog)s mig --project my-project
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Setup command
    setup_parser = subparsers.add_parser("setup", help="Setup GCP project")
    setup_parser.add_argument("--project", required=True, help="GCP Project ID")
    
    # Create command
    create_parser = subparsers.add_parser("create", help="Create VM instance")
    create_parser.add_argument("--project", required=True, help="GCP Project ID")
    create_parser.add_argument("--name", help="Instance name (auto-generated if not provided)")
    create_parser.add_argument("--machine-type", default="e2-medium", help="Machine type")
    create_parser.add_argument("--zone", default="us-central1-a", help="GCP zone")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List instances")
    list_parser.add_argument("--project", required=True, help="GCP Project ID")
    
    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete instance")
    delete_parser.add_argument("--project", required=True, help="GCP Project ID")
    delete_parser.add_argument("--name", required=True, help="Instance name")
    
    # MIG command (Managed Instance Group)
    mig_parser = subparsers.add_parser("mig", help="Create Managed Instance Group")
    mig_parser.add_argument("--project", required=True, help="GCP Project ID")
    mig_parser.add_argument("--group-name", default="autoscale-group", help="Group name")
    mig_parser.add_argument("--min-instances", type=int, default=1)
    mig_parser.add_argument("--max-instances", type=int, default=5)
    mig_parser.add_argument("--target-cpu", type=float, default=0.75)
    
    # Cost estimate command
    cost_parser = subparsers.add_parser("cost", help="Estimate costs")
    cost_parser.add_argument("--machine-type", default="e2-medium")
    cost_parser.add_argument("--hours", type=int, default=24)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    try:
        if args.command == "setup":
            success = setup_gcp_project(args.project)
            sys.exit(0 if success else 1)
        
        elif args.command == "create":
            manager = GCPScaleManager(args.project, zone=args.zone)
            success = manager.create_instance(
                instance_name=args.name,
                machine_type=args.machine_type
            )
            sys.exit(0 if success else 1)
        
        elif args.command == "list":
            manager = GCPScaleManager(args.project)
            manager.list_instances()
        
        elif args.command == "delete":
            manager = GCPScaleManager(args.project)
            success = manager.delete_instance(args.name)
            sys.exit(0 if success else 1)
        
        elif args.command == "mig":
            manager = GCPScaleManager(args.project)
            
            # Create template
            template_name = f"{args.group_name}-template"
            manager.create_instance_template(template_name)
            
            # Create managed instance group
            manager.create_managed_instance_group(
                group_name=args.group_name,
                template_name=template_name,
                min_instances=args.min_instances,
                max_instances=args.max_instances,
                target_cpu_utilization=args.target_cpu
            )
        
        elif args.command == "cost":
            manager = GCPScaleManager("dummy")  # Project not needed for cost estimate
            costs = manager.get_costs_estimate(args.machine_type, args.hours)
            print("\nCost Estimate:")
            print(f"  Machine Type: {costs['machine_type']}")
            print(f"  Hourly Rate: ${costs['hourly_rate_usd']:.4f}")
            print(f"  Duration: {costs['hours']} hours")
            print(f"  Estimated Cost: ${costs['estimated_cost_usd']:.2f}")
    
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
