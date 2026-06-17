import subprocess
import time
import sys
import os

def main():
    print("Starting NetCourier Services...")
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"

    processes = []
    
    try:
        # 1. Gateway
        print("Starting Gateway (Port 9000)...")
        gw = subprocess.Popen([sys.executable, "-m", "netcourier.gateway.main"], env=env)
        processes.append(gw)
        time.sleep(1)

        # 2. Server S1
        print("Starting Process Server S1 (Port 9101)...")
        s1 = subprocess.Popen([sys.executable, "-m", "netcourier.server.main", "--server-id", "S1", "--port", "9101"], env=env)
        processes.append(s1)
        
        # 3. Server S2
        print("Starting Process Server S2 (Port 9102)...")
        s2 = subprocess.Popen([sys.executable, "-m", "netcourier.server.main", "--server-id", "S2", "--port", "9102"], env=env)
        processes.append(s2)
        time.sleep(1)

        # 4. Web API & UI
        print("Starting Web UI & API Server (Port 8080)...")
        web = subprocess.Popen([sys.executable, "-m", "netcourier.web.api.main"], env=env)
        processes.append(web)

        print("\n" + "="*50)
        print("[OK] All services started successfully!")
        print("[INFO] Access the Web UI at: http://localhost:8080")
        print("[INFO] Press Ctrl+C to gracefully stop all services")
        print("="*50 + "\n")

        for p in processes:
            p.wait()
            
    except KeyboardInterrupt:
        print("\n[INFO] Stopping all services...")
        for p in processes:
            p.terminate()
        for p in processes:
            p.wait()
        print("[OK] All services stopped.")

if __name__ == "__main__":
    main()
