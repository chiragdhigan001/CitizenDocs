import asyncio
from fastapi import FastAPI, File, UploadFile, Form, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from PIL import Image
import pillow_heif
import pillow_avif
import os
import time
import uuid
import shutil
import io

pillow_heif.register_heif_opener()

app = FastAPI()

OUTPUT_DIR = "converted_files"
os.makedirs(OUTPUT_DIR, exist_ok=True)
history_db = {}

def cleanup_old_files():
    now = time.time()
    cutoff = now - (24 * 3600)
    to_delete = [fid for fid, meta in history_db.items() if meta["timestamp"] < cutoff]
    for fid in to_delete:
        if os.path.exists(history_db[fid]["path"]):
            os.remove(history_db[fid]["path"])
        del history_db[fid]

def process_image_format(img, target_format):
    target_format = target_format.lower()
    save_args = {"optimize": True}
    
    if target_format in ["jpg", "jpeg"]:
        save_format = "JPEG"
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
    elif target_format == "png":
        save_format = "PNG"
        save_args["optimize"] = False
        save_args["compress_level"] = 1 
    elif target_format == "webp":
        save_format = "WEBP"
    elif target_format == "gif":
        save_format = "GIF"
    elif target_format == "ico":
        save_format = "ICO"
        img = img.resize((32, 32))
    else:
        save_format = target_format.upper()
        
    return img, save_format, save_args

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    if os.path.exists("favicon.ico"):
        return FileResponse("favicon.ico")
    raise HTTPException(status_code=404, detail="Favicon not found")

@app.get("/")
async def get_ui():
    with open("index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.get("/api/history")
async def get_history(background_tasks: BackgroundTasks):
    background_tasks.add_task(cleanup_old_files)
    return [{
        "id": fid, "name": meta["name"], "format": meta["format"], 
        "size": f"{os.path.getsize(meta['path']) / 1024:.1f} KB",
        "age": int(time.time() - meta["timestamp"])
    } for fid, meta in history_db.items() if os.path.exists(meta["path"])]

@app.post("/api/convert")
async def convert_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    target_format: str = Form(...)
):
    background_tasks.add_task(cleanup_old_files)
    target_format = target_format.lower().strip()
    file_id = str(uuid.uuid4())
    base_name = os.path.splitext(file.filename)[0]
    output_name = f"{base_name}.{target_format}"
    output_path = os.path.join(OUTPUT_DIR, f"{file_id}.{target_format}")
    
    if target_format == "mp3":
        from moviepy import VideoFileClip
        input_path = os.path.join(OUTPUT_DIR, f"{file_id}_in.mp4")
        with open(input_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        try:
            clip = VideoFileClip(input_path)
            clip.audio.write_audiofile(output_path, logger=None)
            clip.audio.close()
            clip.close()
        finally:
            if os.path.exists(input_path): os.remove(input_path)
    else:
        file_bytes = await file.read()
        
        def process_standard_conversion(data):
            img = Image.open(io.BytesIO(data))
            img, save_format, save_args = process_image_format(img, target_format)
            img.save(output_path, format=save_format, **save_args)
            
        await asyncio.to_thread(process_standard_conversion, file_bytes)
        
    history_db[file_id] = {"name": output_name, "path": output_path, "timestamp": time.time(), "format": target_format}
    return {"id": file_id}

@app.post("/api/compress")
async def compress_image(
    file: UploadFile = File(...), 
    target_format: str = Form(...), 
    target_kb: int = Form(...)
):
    target_format = target_format.lower().strip()
    file_bytes = await file.read() 
    target_bytes = target_kb * 1024
    
    file_id = str(uuid.uuid4())
    output_name = f"compressed_{os.path.splitext(file.filename)[0]}.{target_format}"
    output_path = os.path.join(OUTPUT_DIR, f"{file_id}.{target_format}")

    def perform_compression(data):
        img = Image.open(io.BytesIO(data))
        img, save_format, save_args = process_image_format(img, target_format)
        
        buf = io.BytesIO()
        img.save(buf, format=save_format, **save_args)
        if buf.tell() <= target_bytes: return buf.getvalue()

        best_buffer = buf
        if save_format in ["JPEG", "WEBP"]:
            low, high = 5, 95
            for _ in range(7):
                mid = (low + high) // 2
                temp_buf = io.BytesIO()
                args = save_args.copy()
                args["quality"] = mid
                img.save(temp_buf, format=save_format, **args)
                
                if temp_buf.tell() <= target_bytes:
                    best_buffer = temp_buf
                    low = mid + 1 
                else:
                    high = mid - 1
            if best_buffer.tell() <= target_bytes: return best_buffer.getvalue()

        low, high = 0.01, 1.0
        best_buffer = None
        for _ in range(8):
            mid = (low + high) / 2.0
            new_w, new_h = max(1, int(img.width * mid)), max(1, int(img.height * mid))
            temp_img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            
            temp_buf = io.BytesIO()
            temp_img.save(temp_buf, format=save_format, **save_args)
            if temp_buf.tell() <= target_bytes:
                best_buffer = temp_buf
                low = mid + 0.01 
            else:
                high = mid - 0.01
                
        return best_buffer.getvalue() if best_buffer else temp_buf.getvalue()

    compressed_data = await asyncio.to_thread(perform_compression, file_bytes)
    with open(output_path, "wb") as f: f.write(compressed_data)
    history_db[file_id] = {"name": output_name, "path": output_path, "timestamp": time.time(), "format": target_format}
    return {"id": file_id}

@app.post("/api/merge-pdf")
async def merge_to_pdf(file_ids: str = Form(None), files: list[UploadFile] = File(None)):
    image_list = []
    if file_ids:
        for fid in [f.strip() for f in file_ids.split(",") if f.strip()]:
            if fid in history_db and os.path.exists(history_db[fid]["path"]):
                img = Image.open(history_db[fid]["path"])
                if img.mode in ("RGBA", "P"): img = img.convert("RGB")
                image_list.append(img)
                
    if files:
        for f in files:
            if f.filename != "":
                img = Image.open(f.file)
                if img.mode in ("RGBA", "P"): img = img.convert("RGB")
                image_list.append(img)

    if not image_list: raise HTTPException(status_code=400, detail="No images selected.")
        
    pdf_id = str(uuid.uuid4())
    pdf_path = os.path.join(OUTPUT_DIR, f"{pdf_id}.pdf")
    image_list[0].save(pdf_path, save_all=True, append_images=image_list[1:])
    history_db[pdf_id] = {"name": "compiled_images.pdf", "path": pdf_path, "timestamp": time.time(), "format": "pdf"}
    return {"id": pdf_id}

@app.put("/api/rename/{file_id}")
async def rename_file(file_id: str, new_name: str = Form(...)):
    if file_id not in history_db: raise HTTPException(status_code=404, detail="File not found")
    for fid, meta in history_db.items():
        if fid != file_id and meta["name"].lower() == new_name.lower():
            raise HTTPException(status_code=400, detail="Name already exists in session.")
    history_db[file_id]["name"] = new_name
    return {"status": "success"}

@app.get("/api/download/{file_id}")
async def download_file(file_id: str):
    return FileResponse(history_db[file_id]["path"], filename=history_db[file_id]["name"])

@app.delete("/api/delete/{file_id}")
async def delete_file(file_id: str):
    if file_id in history_db:
        if os.path.exists(history_db[file_id]["path"]): os.remove(history_db[file_id]["path"])
        del history_db[file_id]
    return {"status": "success"}