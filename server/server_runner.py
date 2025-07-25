#!/usr/bin/env python3
"""
Development server startup script for FeedMerge API
Usage: python server_runner.py
"""

import uvicorn
import sys
import socket
import subprocess
import signal
import os
import time
from typing import List, Optional


def check_port_in_use(port: int) -> bool:
    """Check if a port is currently in use"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        result = sock.connect_ex(('localhost', port))
        return result == 0


def get_processes_using_port(port: int) -> List[dict]:
    """Get list of processes using a specific port"""
    processes = []
    try:
        if os.name == 'nt':  # Windows
            # Use netstat to find processes using the port
            result = subprocess.run(
                ['netstat', '-ano'], 
                capture_output=True, 
                text=True, 
                check=True
            )
            
            for line in result.stdout.split('\n'):
                if f':{port}' in line and 'LISTENING' in line:
                    parts = line.split()
                    if len(parts) >= 5:
                        pid = parts[-1]
                        try:
                            # Get process name
                            tasklist_result = subprocess.run(
                                ['tasklist', '/FI', f'PID eq {pid}', '/FO', 'CSV'],
                                capture_output=True,
                                text=True,
                                check=True
                            )
                            if len(tasklist_result.stdout.split('\n')) > 1:
                                process_line = tasklist_result.stdout.split('\n')[1]
                                process_name = process_line.split(',')[0].strip('"')
                                processes.append({
                                    'pid': int(pid),
                                    'name': process_name,
                                    'port': port
                                })
                        except (subprocess.CalledProcessError, ValueError, IndexError):
                            processes.append({
                                'pid': int(pid) if pid.isdigit() else 0,
                                'name': 'Unknown',
                                'port': port
                            })
        else:  # Unix/Linux/Mac
            result = subprocess.run(
                ['lsof', '-ti', f':{port}'], 
                capture_output=True, 
                text=True
            )
            for pid in result.stdout.strip().split('\n'):
                if pid and pid.isdigit():
                    processes.append({
                        'pid': int(pid),
                        'name': 'Unknown',
                        'port': port
                    })
    except subprocess.CalledProcessError:
        pass
    
    return processes


def kill_processes_on_port(port: int) -> bool:
    """Kill all processes using a specific port"""
    processes = get_processes_using_port(port)
    
    if not processes:
        return False
        
    print(f"⚠️  Found {len(processes)} process(es) using port {port}:")
    for proc in processes:
        print(f"   - PID {proc['pid']}: {proc['name']}")
    
    print(f"🔄 Stopping processes on port {port}...")
    
    killed_any = False
    for proc in processes:
        try:
            if os.name == 'nt':  # Windows
                subprocess.run(['taskkill', '/F', '/PID', str(proc['pid'])], 
                             check=True, capture_output=True)
            else:  # Unix/Linux/Mac
                os.kill(proc['pid'], signal.SIGTERM)
                time.sleep(1)
                # If still running, force kill
                try:
                    os.kill(proc['pid'], signal.SIGKILL)
                except ProcessLookupError:
                    pass  # Process already terminated
            killed_any = True
            print(f"✅ Stopped process {proc['pid']} ({proc['name']})")
        except (subprocess.CalledProcessError, ProcessLookupError, PermissionError) as e:
            print(f"❌ Failed to stop process {proc['pid']}: {e}")
    
    if killed_any:
        # Give processes time to clean up
        time.sleep(2)
    
    return killed_any


def setup_signal_handlers():
    """Set up signal handlers for graceful shutdown"""
    def signal_handler(sig, frame):
        print(f"\n🛑 Received signal {sig}")
        print("👋 Shutting down FeedMerge API server...")
        
        # Kill any remaining processes on port 8000
        if check_port_in_use(8000):
            print("🔄 Cleaning up remaining processes...")
            kill_processes_on_port(8000)
        
        print("✅ Server stopped gracefully.")
        sys.exit(0)
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
    if hasattr(signal, 'SIGTERM'):
        signal.signal(signal.SIGTERM, signal_handler)  # Termination signal


def main():
    """Start the development server with sensible defaults"""
    
    # Set up signal handlers for graceful shutdown
    setup_signal_handlers()
    
    # Default configuration
    config = {
        "app": "app.main:app",
        "host": "localhost",
        "port": 8000,
        "reload": True,
        "log_level": "info",
    }
    
    # Parse simple command line arguments
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            if arg.startswith("--port="):
                config["port"] = int(arg.split("=")[1])
            elif arg.startswith("--host="):
                config["host"] = arg.split("=")[1]
            elif arg == "--help" or arg == "-h":
                print("FeedMerge Development Server")
                print("Usage: python server_runner.py [options]")
                print("\nOptions:")
                print("  --host=HOST     Host to bind to (default: localhost)")
                print("  --port=PORT     Port to bind to (default: 8000)")
                print("  --help, -h      Show this help message")
                print("\nExamples:")
                print("  python server_runner.py                    # Start on localhost:8000")
                print("  python server_runner.py --port=8080        # Start on localhost:8080")
                print("  python server_runner.py --host=0.0.0.0     # Start on all interfaces")
                print("\nControls:")
                print("  Ctrl+C          Stop the server gracefully")
                return
    
    port = config["port"]
    host = config["host"]
    
    print(f"🚀 Starting FeedMerge API development server...")
    print(f"📍 Server: http://{host}:{port}")
    print(f"📚 Docs: http://{host}:{port}/docs")
    print(f"🔄 Auto-reload: enabled")
    print(f"🛑 Press Ctrl+C to stop the server")
    print("=" * 50)
    
    # Check if port is already in use
    if check_port_in_use(port):
        print(f"⚠️  Port {port} is already in use!")
        killed = kill_processes_on_port(port)
        
        if killed:
            print(f"✅ Port {port} is now available")
        else:
            print(f"❌ Could not free port {port}. Try using a different port.")
            print(f"💡 Use: python server_runner.py --port=8080")
            return
    
    try:
        print(f"🌟 Starting server on {host}:{port}...")
        uvicorn.run(**config)
    except KeyboardInterrupt:
        print("\n🛑 Received Ctrl+C")
        print("👋 FeedMerge API server stopped.")
    except Exception as e:
        print(f"❌ Server error: {e}")
        # Clean up on error
        if check_port_in_use(port):
            kill_processes_on_port(port)
    finally:
        print("🧹 Cleaning up...")


if __name__ == "__main__":
    main()
