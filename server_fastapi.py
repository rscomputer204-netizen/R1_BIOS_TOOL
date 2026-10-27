import os
import shutil
import uuid
import time
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from typing import Dict

# Import local engines (ensure these are in your python path)
from bios_parser import get_bios_metadata
import smart_repair_engine
from analysis_suite import AnalysisSuite
from mea_parser import parse_mea_output
from bios_region_fixer import BIOSRegionFixer
from hp_repair_tool import HPBIOSRepairer
from utils.archiver import archive_session


app = FastAPI(title="R1 BIOS Service VPS")

# Directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "server_data", "uploads")
OUTPUT_DIR = os.path.join(BASE_DIR, "server_data", "outputs")
STATIC_DIR = os.path.join(BASE_DIR, "web")

for d in [UPLOAD_DIR, OUTPUT_DIR, STATIC_DIR]:
    os.makedirs(d, exist_ok=True)

# Mount static files (for the landing page and client downloads)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# In-memory task tracking (In production, use Redis/DB)
tasks: Dict[str, dict] = {}

def prepare_client_download(force=False):
    """Zips the dist folder for web download in the background."""
    import threading
    
    def _zip_worker():
        dist_dir = os.path.join(BASE_DIR, "dist", "BIOS_TOOL_PREMIUM")
        zip_name = os.path.join(STATIC_DIR, "R1_BIOS_TOOL_PREMIUM.zip")
        
        if os.path.exists(dist_dir):
            if os.path.exists(zip_name) and not force:
                print(f"[*] Client zip already exists at {zip_name}. Skipping background re-zip.")
                return

            try:
                print(f"[*] [BACKGROUND] Preparing client download zip: {zip_name}")
                # shutil.make_archive adds .zip automatically if not present in the base_name
                shutil.make_archive(zip_name.replace(".zip", ""), 'zip', dist_dir)
                print("[*] [BACKGROUND] Client zip ready.")
            except Exception as e:
                print(f"[!] [BACKGROUND] Error creating client zip: {str(e)}")
        else:
            print(f"[!] [BACKGROUND] Warning: dist directory not found at {dist_dir}. Download will be unavailable.")

    # Start zipping in a background thread so the server doesn't hang
    thread = threading.Thread(target=_zip_worker, daemon=True)
    thread.start()

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    favicon_path = os.path.join(STATIC_DIR, "assets", "logo.png")
    if os.path.exists(favicon_path):
        return FileResponse(favicon_path)
    return HTMLResponse(content="", status_code=204)

@app.get("/", response_class=HTMLResponse)
async def read_index():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>R1 BIOS Server Active</h1><p>Landing page missing.</p>"

@app.post("/upload")
async def upload_file(file: UploadFile = File(...), donor: UploadFile = File(None)):
    task_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{task_id}_{file.filename}")
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    donor_path = None
    if donor:
        donor_path = os.path.join(UPLOAD_DIR, f"{task_id}_donor_{donor.filename}")
        with open(donor_path, "wb") as buffer:
            shutil.copyfileobj(donor.file, buffer)

    tasks[task_id] = {
        "filename": file.filename,
        "path": file_path,
        "donor_path": donor_path,
        "status": "uploaded",
        "created_at": time.time(),
        "logs": []
    }
    
    return {"task_id": task_id, "status": "uploaded"}

@app.post("/process/{task_id}/{command}")
async def process_task(task_id: str, command: str, background_tasks: BackgroundTasks, migrate_dmi: bool = True):
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = tasks[task_id]
    input_path = task["path"]
    
    # Define output path
    output_filename = f"REPAIRED_{task['filename']}"
    output_path = os.path.join(OUTPUT_DIR, f"{task_id}_{output_filename}")
    
    # Logic Dispatcher
    def run_repair():
        try:
            tasks[task_id]["status"] = "processing"
            log_lines = []
            def log_cb(msg):
                print(f"[{task_id}] {msg}")
                if "logs" not in tasks[task_id]:
                    tasks[task_id]["logs"] = []
                tasks[task_id]["logs"].append(msg)
            
            # Logic Dispatcher
            if command == "SMART_ME_FIX":
                log_cb(f"[INFO] Starting SMART_ME_FIX for {task['filename']}")
                
                # 1. Run MEA to get metadata
                mea_output = []
                def mea_cb(line):
                    mea_output.append(line)
                    # print(line)
                
                log_cb("[INFO] Running ME Analyzer...")
                AnalysisSuite.run_me_analyzer(input_path, mea_cb)
                full_mea_text = "\n".join(mea_output)
                
                # 2. Parse metadata
                mea_meta = parse_mea_output(full_mea_text)
                if not mea_meta.get("version"):
                    log_cb("[ERROR] Failed to extract ME version from file.")
                    tasks[task_id]["status"] = "failed"
                    tasks[task_id]["error"] = "MEA metadata extraction failed"
                    return

                log_cb(f"[INFO] Detected ME Version: {mea_meta['version']}")
                
                # 3. Run Smart Repair
                result = smart_repair_engine.run_smart_repair(
                    input_path, 
                    mea_meta, 
                    log_cb,
                    deliver_to_final=False # Keep it in output_path
                )
                
                if result.get("success") and result.get("output_path"):
                    shutil.copy2(result["output_path"], output_path)
                    tasks[task_id]["status"] = "completed"
                    tasks[task_id]["output_path"] = output_path
                    
                    # Beautiful Success Message (Synced with main.py)
                    success_msg = (
                        "<font color='#00ff41'><b>[INFO] [SUCCESS] Full CSME Clean Completed! ✅</b></font><br>"
                        "<font color='#00ff41'><b>[INFO] STATUS: Manufacturing Mode: Disabled ✅</b></font>"
                    )
                    log_cb(success_msg)
                    log_cb("[SUCCESS] SMART REPAIR COMPLETE!")
                else:
                    tasks[task_id]["status"] = "failed"
                    fail_msg = (
                        "<font color='#ff3131'><b>[ERROR] Smart Repair Engine reported failure. ⚠️</b></font><br>"
                        "<font color='#ff3131'><b>[INFO] STATUS: Initialized Mode (Repair Incomplete)</b></font>"
                    )
                    log_cb(fail_msg)
                    tasks[task_id]["error"] = "Smart Repair Engine failed to produce result"
            
            elif command == "BIOS_RG_FIX":
                log_cb(f"[INFO] Starting BIOS_RG_FIX for {task['filename']}")
                donor_path = task.get("donor_path")
                
                if not donor_path:
                    tasks[task_id]["status"] = "failed"
                    tasks[task_id]["error"] = "BIOS_RG_FIX requires a donor file."
                    log_cb("[ERROR] BIOS_RG_FIX via VPS requires a donor file.")
                    return

                # Determine if it's HP or Generic
                is_hp_exe = donor_path.lower().endswith(".exe")
                success = False
                
                if is_hp_exe:
                    log_cb("[INFO] HP SoftPaq detected. File Match Complete ✅")
                    log_cb("[INFO] Using Adaptive HP Repair logic...")
                    repairer = HPBIOSRepairer(input_path, donor_path, migrate_dmi=migrate_dmi)
                    # Monkey-patch logs
                    repairer.log_info = lambda msg: log_cb(f"[INFO] {msg}")
                    repairer.log_error = lambda msg: log_cb(f"[ERROR] {msg}")
                    
                    success = repairer.perform_repair(output_path)
                else:
                    log_cb("[INFO] Generic BIOS Region donor detected.")
                    res_path = BIOSRegionFixer.fix_bios_region(
                        input_path, 
                        donor_path, 
                        log_cb, 
                        output_dir=OUTPUT_DIR,
                        migrate_dmi=migrate_dmi
                    )
                    if res_path and os.path.exists(res_path):
                        shutil.copy2(res_path, output_path)
                        success = True

                if success:
                    tasks[task_id]["status"] = "completed"
                    tasks[task_id]["output_path"] = output_path
                    log_cb("[SUCCESS] BIOS_region Clean Complete ✅")
                else:
                    tasks[task_id]["status"] = "failed"
                    tasks[task_id]["error"] = "BIOS Region Fix engine failed"
                    log_cb("[ERROR] BIOS Region Fix failed.")
                
            else:
                tasks[task_id]["status"] = "failed"
                tasks[task_id]["error"] = f"Unknown command: {command}"
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            print(f"[!] Error in run_repair: {error_detail}")
            tasks[task_id]["status"] = "failed"
            tasks[task_id]["error"] = str(e)
        finally:
            # Archiving Integration (Smart Switch)
            repair_status = "SUCCESS" if tasks[task_id].get("status") == "completed" else "FAILED"
            error_log = tasks[task_id].get("error")
            
            repair_info = {
                "command": command,
                "filename": task.get("filename"),
                "has_donor": bool(task.get("donor_path"))
            }

            final_output = tasks[task_id].get("output_path") if repair_status == "SUCCESS" else None
            
            archive_session(
                task_id=task_id,
                source_corrupt=input_path,
                source_fixed=final_output,
                repair_details=repair_info,
                status=repair_status,
                error_log=error_log
            )

    background_tasks.add_task(run_repair)
    return {"status": "queued", "task_id": task_id}

@app.get("/status/{task_id}")
async def get_status(task_id: str):
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    return tasks[task_id]

@app.get("/download/{task_id}")
async def download_result(task_id: str):
    if task_id not in tasks or tasks[task_id]["status"] != "completed":
        raise HTTPException(status_code=400, detail="Result not ready")
    
    return FileResponse(
        tasks[task_id]["output_path"], 
        filename=f"FIXED_{tasks[task_id]['filename']}",
        media_type="application/octet-stream"
    )

@app.get("/download-client")
async def download_client():
    """Endpoint to download the zipped desktop application."""
    zip_path = os.path.join(STATIC_DIR, "R1_BIOS_TOOL_PREMIUM.zip")
    if os.path.exists(zip_path):
        return FileResponse(zip_path, filename="R1_BIOS_TOOL_PREMIUM.zip", media_type="application/zip")
    raise HTTPException(status_code=404, detail="Client download not available. Contact Administrator.")

@app.get("/download-installer")
async def download_installer():
    """Endpoint to download the installer application (.exe)."""
    installer_path = os.path.join(STATIC_DIR, "R1_bios_editor.exe")
    if os.path.exists(installer_path):
        return FileResponse(installer_path, filename="R1 bios editor.exe", media_type="application/octet-stream")
    raise HTTPException(status_code=404, detail="Installer download not available. Contact Administrator.")

if __name__ == "__main__":
    import uvicorn
    import signal
    import sys

    def signal_handler(sig, frame):
        print("\n[!] Shutdown requested... Cleaning up.")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Prepare the client download zip in the background before starting
    prepare_client_download(force=False)

    print("[*] Starting FastAPI Server on http://0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info", access_log=True)
