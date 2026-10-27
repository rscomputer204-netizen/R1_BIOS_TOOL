import requests
import os
import time

class NetworkManager:
    """
    Handles communication between the BIOS Client and the FastAPI VPS Server.
    Uses HTTP REST API for robust and scalable communication.
    """
    def __init__(self, host='127.0.0.1', port=8000):
        self.base_url = f"http://{host}:{port}"
        self.session = requests.Session()

    def check_connection(self):
        """Checks if the server is alive."""
        try:
            # We can just hit the root or a dedicated health check
            response = self.session.get(f"{self.base_url}/", timeout=3)
            return response.status_code == 200
        except:
            return False

    def send_and_process(self, file_path, command, callback=None, donor_path=None, migrate_dmi=True):
        """
        Full REST workflow: Upload -> Process -> Poll -> Download
        """
        try:
            if callback: callback(f"[INFO] Connecting to VPS @ {self.base_url}...")
            
            # 1. Upload
            if callback: callback(f"[INFO] Uploading {os.path.basename(file_path)}...")
            with open(file_path, 'rb') as f:
                files = {'file': (os.path.basename(file_path), f, 'application/octet-stream')}
                
                # Add donor file if provided
                donor_file_handle = None
                if donor_path and os.path.exists(donor_path):
                    if callback: callback(f"[INFO] Attaching Donor: {os.path.basename(donor_path)}...")
                    donor_file_handle = open(donor_path, 'rb')
                    files['donor'] = (os.path.basename(donor_path), donor_file_handle, 'application/octet-stream')
                
                resp = self.session.post(f"{self.base_url}/upload", files=files, timeout=60)
                
                if donor_file_handle:
                    donor_file_handle.close()
            
            if resp.status_code != 200:
                error_msg = f"Upload failed ({resp.status_code}): {resp.text[:100]}"
                if callback: callback(f"[ERROR] {error_msg}")
                return None
            
            task_id = resp.json().get("task_id")
            if callback: callback(f"[SUCCESS] Uploaded. Task ID: {task_id}")

            # 2. Start Processing
            if callback: callback(f"[INFO] Initializing {command} on server...")
            # Pass migrate_dmi flag as query parameter
            process_url = f"{self.base_url}/process/{task_id}/{command}?migrate_dmi={str(migrate_dmi).lower()}"
            resp = self.session.post(process_url, timeout=10)
            
            if resp.status_code != 200:
                if callback: callback(f"[ERROR] Process start failed: {resp.text}")
                return None

            if callback: callback("[INFO] Server processing... please wait.")
            retry_count = 0
            while retry_count < 60: # Max 120 seconds
                try:
                    status_resp = self.session.get(f"{self.base_url}/status/{task_id}", timeout=5)
                    if status_resp.status_code != 200:
                        retry_count += 1
                        time.sleep(2)
                        continue
                    
                    status_data = status_resp.json()
                    status = status_data.get("status")
                    
                    # Display remote logs if available
                    remote_logs = status_data.get("logs", [])
                    if remote_logs:
                        # Only show logs that haven't been printed yet
                        current_log_count = getattr(self, "_last_log_idx", 0)
                        if len(remote_logs) > current_log_count:
                            for i in range(current_log_count, len(remote_logs)):
                                if callback: callback(f"[REMOTE] {remote_logs[i]}")
                            self._last_log_idx = len(remote_logs)
                    
                    if status == "completed":
                        if callback: callback("[SUCCESS] Remote analysis complete.")
                        self._last_log_idx = 0 # Reset for next task
                        break
                    elif status == "failed":
                        err = status_data.get('error', 'Unknown Error')
                        if callback: callback(f"[ERROR] Server failed: {err}")
                        return None
                except Exception as e:
                    if callback: callback(f"[WARNING] Connection glitch, retrying... ({str(e)})")
                
                retry_count += 1
                time.sleep(2)
            
            if retry_count >= 60:
                if callback: callback("[ERROR] VPS request timed out.")
                return None

            # 4. Download Result
            if callback: callback("[INFO] Downloading result...")
            down_resp = self.session.get(f"{self.base_url}/download/{task_id}", stream=True, timeout=60)
            
            if down_resp.status_code == 200:
                output_dir = os.path.join(os.path.dirname(file_path), "REPAIRED_VIA_VPS")
                os.makedirs(output_dir, exist_ok=True)
                output_path = os.path.join(output_dir, f"FIXED_{os.path.basename(file_path)}")
                
                with open(output_path, 'wb') as f:
                    for chunk in down_resp.iter_content(chunk_size=8192):
                        if chunk: f.write(chunk)
                
                if callback: callback(f"[SUCCESS] Downloaded to: {output_path}")
                return output_path
            else:
                if callback: callback(f"[ERROR] Download failed: {down_resp.text}")
                return None

        except Exception as e:
            if callback: callback(f"[ERROR] Network operation failed: {str(e)}")
            return None
