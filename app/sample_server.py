#!/usr/bin/env python3
"""
=============================================================================
Sample Web Server with Load Generator
Assignment 3: VCC - Auto-scaling Local VM to Cloud
Author: Samnit Mehandiratta (M25AI2087), IIT Jodhpur
Email: m25ai2087@iitj.ac.in
=============================================================================

This module provides:
1. A simple HTTP server that can simulate CPU-intensive work
2. A load generator to increase resource usage for testing auto-scaling
"""

import os
import http.server
import socketserver
import threading
import multiprocessing
import time
import random
import math
import argparse
import urllib.request
import urllib.error
from datetime import datetime


# =============================================================================
# Part 1: Sample Web Server
# =============================================================================

class AutoScaleHandler(http.server.BaseHTTPRequestHandler):
    """HTTP request handler with health check and load endpoints."""
    
    def log_message(self, format, *args):
        """Custom log format."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {args[0]}")
    
    def do_GET(self):
        """Handle GET requests."""
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status": "healthy", "timestamp": "' + 
                           datetime.now().isoformat().encode() + b'"}')
        
        elif self.path == "/":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Auto-Scale Demo</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 40px; }}
                    h1 {{ color: #2196F3; }}
                    .status {{ padding: 20px; background: #e3f2fd; border-radius: 8px; }}
                    .endpoints {{ margin-top: 20px; }}
                    code {{ background: #f5f5f5; padding: 2px 6px; border-radius: 4px; }}
                </style>
            </head>
            <body>
                <h1>🚀 Auto-Scale Demo Server</h1>
                <div class="status">
                    <h2>Server Status: Running</h2>
                    <p>Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
                    <p>Author: Samnit Mehandiratta (M25AI2087)</p>
                </div>
                <div class="endpoints">
                    <h3>Available Endpoints:</h3>
                    <ul>
                        <li><code>GET /health</code> - Health check endpoint</li>
                        <li><code>GET /compute?seconds=5</code> - CPU-intensive computation</li>
                        <li><code>GET /memory?mb=100</code> - Allocate memory</li>
                    </ul>
                </div>
            </body>
            </html>
            """
            self.wfile.write(html.encode())
        
        elif self.path.startswith("/compute"):
            # CPU-intensive endpoint
            query = self.path.split("?")[1] if "?" in self.path else ""
            params = dict(p.split("=") for p in query.split("&") if "=" in p)
            seconds = int(params.get("seconds", 5))
            
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(f"Starting CPU-intensive task for {seconds} seconds...\n".encode())
            
            # Perform CPU-intensive calculation
            start = time.time()
            result = 0
            while time.time() - start < seconds:
                result += math.sqrt(random.random()) * math.sin(random.random())
            
            self.wfile.write(f"Task completed. Result: {result:.6f}\n".encode())
        
        elif self.path.startswith("/memory"):
            # Memory allocation endpoint
            query = self.path.split("?")[1] if "?" in self.path else ""
            params = dict(p.split("=") for p in query.split("&") if "=" in p)
            mb = int(params.get("mb", 100))
            
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(f"Allocating {mb}MB memory...\n".encode())
            
            # Allocate memory (roughly)
            data = bytearray(mb * 1024 * 1024)
            for i in range(0, len(data), 1024):
                data[i] = i % 256
            
            self.wfile.write(f"Memory allocated. Holding for 30 seconds...\n".encode())
            time.sleep(30)
            del data
            self.wfile.write(b"Memory released.\n")
        
        else:
            self.send_response(404)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"404 Not Found")


def run_server(port: int = 8080, host: str = ""):
    """Run the HTTP server."""
    with socketserver.TCPServer((host, port), AutoScaleHandler) as httpd:
        print(f"🚀 Server running on http://{host or 'localhost'}:{port}")
        print(f"   Health check: http://{host or 'localhost'}:{port}/health")
        print(f"   Press Ctrl+C to stop")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n👋 Server stopped")


# =============================================================================
# Part 2: Load Generator
# =============================================================================

def _cpu_stress_worker(duration: int):
    """Standalone worker for multiprocessing — bypasses GIL so each process uses a full core."""
    end = time.time() + duration
    while time.time() < end:
        result = 0.0
        for _ in range(500000):
            result += math.sqrt(random.random()) * math.sin(random.random())
            result *= math.cos(random.random())


class LoadGenerator:
    """Generate load to test auto-scaling triggers."""

    def __init__(self, target_cpu: float = 80.0, target_ram: float = 80.0):
        self.target_cpu = target_cpu
        self.target_ram = target_ram
        self.cpu_processes = []
        self.memory_buffer = bytearray()

    def memory_stress(self, mb: int = 512, duration: int = None):
        """Generate memory load."""
        start_time = time.time()
        chunk_size = mb * 1024 * 1024
        
        try:
            self.memory_buffer = bytearray(chunk_size)
            # Touch memory to ensure it's allocated
            for i in range(0, len(self.memory_buffer), 4096):
                self.memory_buffer[i] = 0xFF
            
            print(f"✓ Allocated {mb}MB memory")
            
            if duration:
                time.sleep(duration)
        except MemoryError:
            print(f"✗ Cannot allocate {mb}MB - system limit reached")
        finally:
            self.memory_buffer = bytearray()
    
    def start_cpu_load(self, threads: int = None, duration: int = 120):
        """Start CPU stress using multiprocessing to bypass the GIL."""
        nproc = threads if threads else os.cpu_count() or 4
        for _ in range(nproc):
            p = multiprocessing.Process(target=_cpu_stress_worker, args=(duration,), daemon=True)
            p.start()
            self.cpu_processes.append(p)
        print(f"✓ Started {nproc} CPU stress processes (multiprocessing)")

    def stop_cpu_load(self):
        """Stop CPU load generator."""
        for p in self.cpu_processes:
            p.terminate()
            p.join(timeout=2)
        self.cpu_processes = []
        print("✓ Stopped CPU load")
    
    def http_flood(self, url: str, requests: int = 100, concurrent: int = 5):
        """Send multiple HTTP requests to stress the server."""
        print(f"Sending {requests} requests to {url} (concurrent: {concurrent})")
        
        success = 0
        failed = 0
        start = time.time()
        
        def make_request():
            nonlocal success, failed
            try:
                req = urllib.request.urlopen(url, timeout=10)
                if req.status == 200:
                    success += 1
                else:
                    failed += 1
            except Exception as e:
                failed += 1
        
        threads = []
        for _ in range(requests):
            t = threading.Thread(target=make_request)
            t.start()
            threads.append(t)
            
            # Limit concurrent requests
            if len(threads) >= concurrent:
                threads[0].join()
                threads.pop(0)
        
        # Wait for remaining
        for t in threads:
            t.join()
        
        elapsed = time.time() - start
        print(f"✓ Completed: {success} success, {failed} failed in {elapsed:.2f}s")


def run_load_generator(cpu_percent: int = 80, ram_percent: int = 80, 
                       duration: int = 300):
    """Run the load generator."""
    print("=" * 60)
    print("Load Generator")
    print("=" * 60)
    print(f"Target CPU: {cpu_percent}%")
    print(f"Target RAM: {ram_percent}%")
    print(f"Duration: {duration} seconds")
    print("-" * 60)
    
    generator = LoadGenerator(cpu_percent, ram_percent)
    
    try:
        # Start CPU load — use all cores via multiprocessing to bypass GIL
        generator.start_cpu_load(threads=os.cpu_count(), duration=duration)

        # Start memory load
        ram_mb = max(128, ram_percent * 10)
        generator.memory_stress(ram_mb, duration)
    
    except KeyboardInterrupt:
        print("\nStopping load generator...")
    finally:
        generator.stop_cpu_load()
        print("Load generator stopped")


# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Sample Web Server with Load Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run the web server
  %(prog)s server --port 8080
  
  # Run load generator
  %(prog)s load --cpu 80 --ram 80 --duration 300
  
  # Send HTTP flood to test server
  %(prog)s flood --url http://localhost:8080/health --requests 1000
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Server command
    server_parser = subparsers.add_parser("server", help="Run web server")
    server_parser.add_argument("--port", type=int, default=8080, help="Port to listen on")
    server_parser.add_argument("--host", default="", help="Host to bind to")
    
    # Load command
    load_parser = subparsers.add_parser("load", help="Run load generator")
    load_parser.add_argument("--cpu", type=int, default=80, help="Target CPU percentage")
    load_parser.add_argument("--ram", type=int, default=80, help="Target RAM percentage")
    load_parser.add_argument("--duration", type=int, default=300, help="Duration in seconds")
    
    # Flood command
    flood_parser = subparsers.add_parser("flood", help="HTTP flood test")
    flood_parser.add_argument("--url", required=True, help="Target URL")
    flood_parser.add_argument("--requests", type=int, default=100, help="Number of requests")
    flood_parser.add_argument("--concurrent", type=int, default=5, help="Concurrent requests")
    
    args = parser.parse_args()
    
    if args.command == "server":
        print("=" * 60)
        print("Sample Web Server")
        print("Author: Samnit Mehandiratta (M25AI2087), IIT Jodhpur")
        print("=" * 60)
        run_server(args.port, args.host)
    
    elif args.command == "load":
        run_load_generator(args.cpu, args.ram, args.duration)
    
    elif args.command == "flood":
        generator = LoadGenerator()
        generator.http_flood(args.url, args.requests, args.concurrent)
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
