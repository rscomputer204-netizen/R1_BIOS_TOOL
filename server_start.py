import socket
import threading
import os
import struct
import shutil
import time
import signal
import sys

# Import existing repair engines
try:
    import smart_repair_engine
    import fit_automator
    from dmi_extractor import DMIExtractor
    from hp_repair_tool import HPBIOSRepairer
    from bios_region_fixer import BIOSRegionFixer
    from me_cleaner import apply_firmware_patch
except ImportError as e:
    print(f"[!] Warning: Some repair engines missing: {e}")

class BIOSServer:
    def __init__(self, host='0.0.0.0', port=5005):
        self.host = host
        self.port = port
        self.temp_dir = "SERVER_WORKSPACE"
        self.running = True
        self.buffer_size = 1024 * 1024 # 1MB Superfast Buffer
        os.makedirs(self.temp_dir, exist_ok=True)
        
        # Signal handling for Ctrl+C
        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)

    def shutdown(self, signum, frame):
        print("\n[*] Shutting down VPS BIOS Server...")
        self.running = False
        # Create a dummy connection to break the accept() block if needed
        try:
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((self.host, self.port))
        except:
            pass
        sys.exit(0)

    def start(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # Allow instant restart
            try:
                s.bind((self.host, self.port))
            except Exception as e:
                print(f"[CRITICAL] Could not bind to {self.host}:{self.port} - {e}")
                return

            s.listen(10)
            print("="*50)
            print(f"[*] VPS BIOS SERVER ACTIVE")
            print(f"[*] HOST: {self.host} | PORT: {self.port}")
            print(f"[*] SPEED MODE: 1MB CHUNKS ENABLED")
            print("="*50)

            while self.running:
                try:
                    conn, addr = s.accept()
                    if not self.running: break
                    client_thread = threading.Thread(target=self.handle_client, args=(conn, addr))
                    client_thread.daemon = True # Ensure thread closes with main app
                    client_thread.start()
                except Exception as e:
                    if self.running:
                        print(f"[!] Server accept error: {e}")

    def _recv_all(self, conn, n):
        """Helper to receive exactly n bytes or return None if EOF is hit."""
        data = bytearray()
        while len(data) < n:
            packet = conn.recv(n - len(data))
            if not packet:
                return None
            data.extend(packet)
        return data

    def handle_client(self, conn, addr):
        print(f"[+] INCOMING: {addr[0]} connected")
        start_time = time.time()
        try:
            conn.settimeout(60) # Timeout for slow links
            
            # 0. Peek for PING
            peek = self._recv_all(conn, 4)
            if not peek: return
            if peek == b"PING":
                conn.sendall(b"PONG")
                print(f"[*] HEARTBEAT: {addr[0]} is alive")
                return

            # 1. Receive Command
            cmd_size = struct.unpack('!I', peek)[0]
            cmd_data = self._recv_all(conn, cmd_size)
            if not cmd_data: return
            command = cmd_data.decode('utf-8')
            
            # 2. Receive Metadata
            name_header = self._recv_all(conn, 4)
            if not name_header: return
            name_size = struct.unpack('!I', name_header)[0]
            
            name_data = self._recv_all(conn, name_size)
            if not name_data: return
            file_name = name_data.decode('utf-8')
            
            size_header = self._recv_all(conn, 8)
            if not size_header: return
            file_size = struct.unpack('!Q', size_header)[0]
            
            # 3. Receive File (High-Speed Stream)
            timestamp = int(time.time())
            client_dir = os.path.join(self.temp_dir, f"client_{addr[0]}_{timestamp}")
            os.makedirs(client_dir, exist_ok=True)
            input_path = os.path.join(client_dir, file_name)
            
            print(f"[*] RECEIVING: {file_name} ({file_size / (1024*1024):.2f} MB)")
            with open(input_path, 'wb') as f:
                remaining = file_size
                while remaining > 0:
                    chunk = conn.recv(min(remaining, self.buffer_size))
                    if not chunk: break
                    f.write(chunk)
                    remaining -= len(chunk)

            # 4. Process Request
            print(f"[*] PROCESSING: {command}...")
            output_path, error = self.process_logic(command, input_path, client_dir)

            # 5. Send Response
            if output_path and os.path.exists(output_path):
                msg = "SUCCESS".encode('utf-8')
                conn.sendall(struct.pack('!I', len(msg)))
                conn.sendall(msg)
                
                # Send File (High-Speed Stream)
                out_size = os.path.getsize(output_path)
                conn.sendall(struct.pack('!Q', out_size))
                with open(output_path, 'rb') as f:
                    while chunk := f.read(self.buffer_size):
                        conn.sendall(chunk)
                
                duration = time.time() - start_time
                print(f"[SUCCESS] {addr[0]} - Completed in {duration:.2f}s")
            else:
                error_msg = f"ERROR: {error or 'Processing failed'}".encode('utf-8')
                conn.sendall(struct.pack('!I', len(error_msg)))
                conn.sendall(error_msg)
                print(f"[FAILED] {addr[0]} - {error}")

        except Exception as e:
            print(f"[!] CONNECTION ERROR ({addr[0]}): {e}")
        finally:
            conn.close()

    def process_logic(self, command, input_path, workspace):
        """Dispatches commands to the appropriate repair engine."""
        try:
            output_file = os.path.join(workspace, "REPAIRED_" + os.path.basename(input_path))
            
            # MOCK LOGIC FOR TESTING (In VPS, replace with actual module calls)
            if command == "SMART_ME_FIX":
                # Simulated processing
                time.sleep(1) 
                shutil.copy2(input_path, output_file) # Just copy for now
                return output_file, None

            elif command == "BIOS_RG_FIX":
                time.sleep(1)
                shutil.copy2(input_path, output_file)
                return output_file, None

            elif command == "EXTRACT_DMI":
                # Returns a small text file instead of BIOS if requested
                info_path = os.path.join(workspace, "DMI_INFO.txt")
                with open(info_path, "w") as f:
                    f.write("DMI Extraction Simulation Successful\nSerial: R1-TEST-12345")
                return info_path, None

            return None, f"Command '{command}' implementation pending on server."

        except Exception as e:
            return None, str(e)

if __name__ == "__main__":
    server = BIOSServer()
    server.start()
