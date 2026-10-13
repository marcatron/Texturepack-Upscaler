import os
import shutil
import json
import time
import zipfile
import tempfile
import threading
from dataclasses import dataclass
from typing import Callable, Optional, List, Tuple
from concurrent.futures import ThreadPoolExecutor

from PIL import Image
import numpy as np

from .algorithms import upscale_image_array, AVAILABLE_ALGORITHMS

ProgressCallback = Callable[[int, int, str, str], None]

@dataclass
class ProcessingStats:
    total_images: int = 0
    upscaled_images: int = 0
    colormaps_preserved: int = 0
    other_files_copied: int = 0
    errors: int = 0
    elapsed_seconds: float = 0.0
    output_path: str = ""

class ResourcePackProcessor:
    def __init__(
        self,
        algorithm: str = "scale2x",
        factor: int = 2,
        num_workers: Optional[int] = None,
        progress_callback: Optional[ProgressCallback] = None,
        cancel_event: Optional[threading.Event] = None
    ):
        self.algorithm = algorithm
        self.factor = factor
        if algorithm in AVAILABLE_ALGORITHMS:
            self.factor = AVAILABLE_ALGORITHMS[algorithm]["factor"]
        self.num_workers = num_workers or min(32, (os.cpu_count() or 4) + 4)
        self.progress_callback = progress_callback
        self.cancel_event = cancel_event or threading.Event()

    def process(self, input_path: str, output_path: str) -> ProcessingStats:
        t0 = time.time()
        stats = ProcessingStats()

        input_path = os.path.abspath(input_path)
        output_path = os.path.abspath(output_path)

        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Eingabepfad existiert nicht: {input_path}")

        is_input_zip = zipfile.is_zipfile(input_path) or input_path.lower().endswith(".zip")
        is_output_zip = output_path.lower().endswith(".zip")

        temp_input_dir = None
        temp_output_dir = None

        try:
            # 1. Prepare working source directory
            if is_input_zip:
                if self.progress_callback:
                    self.progress_callback(0, 100, os.path.basename(input_path), "Entpacke ZIP-Archiv...")
                temp_input_dir = tempfile.mkdtemp(prefix="mc_pack_in_")
                with zipfile.ZipFile(input_path, 'r') as zf:
                    zf.extractall(temp_input_dir)
                work_src = temp_input_dir
            else:
                work_src = input_path

            # 2. Prepare working destination directory
            if is_output_zip:
                temp_output_dir = tempfile.mkdtemp(prefix="mc_pack_out_")
                work_dst = temp_output_dir
            else:
                work_dst = output_path
                os.makedirs(work_dst, exist_ok=True)

            # 3. Gather all files
            tasks: List[Tuple[str, str, str]] = []
            non_img_tasks: List[Tuple[str, str, str]] = []

            for root, dirs, files in os.walk(work_src):
                if self.cancel_event.is_set():
                    break
                rel_root = os.path.relpath(root, work_src)
                dst_root = work_dst if rel_root == "." else os.path.join(work_dst, rel_root)
                os.makedirs(dst_root, exist_ok=True)

                for f in files:
                    src_f = os.path.join(root, f)
                    dst_f = os.path.join(dst_root, f)
                    rel_f = os.path.join(rel_root, f)

                    ext = os.path.splitext(f)[1].lower()
                    if ext in [".png", ".tga"]:
                        tasks.append((src_f, dst_f, rel_f))
                    else:
                        non_img_tasks.append((src_f, dst_f, rel_f))

            if self.cancel_event.is_set():
                raise InterruptedError("Vorgang wurde vom Benutzer abgebrochen.")

            total_items = len(tasks) + len(non_img_tasks)
            stats.total_images = len(tasks)

            # 4. Copy and process non-image files
            current_count = 0
            for src_f, dst_f, rel_f in non_img_tasks:
                if self.cancel_event.is_set():
                    raise InterruptedError("Vorgang wurde vom Benutzer abgebrochen.")

                filename = os.path.basename(src_f)
                if filename == "pack.mcmeta" and (os.path.dirname(rel_f) in [".", ""]):
                    try:
                        with open(src_f, "r", encoding="utf-8") as pf:
                            meta = json.load(pf)
                        if "pack" in meta and "description" in meta["pack"]:
                            target_res_label = f" ({self.factor * 16}x{self.factor * 16} Upscaled)"
                            if target_res_label not in meta["pack"]["description"]:
                                meta["pack"]["description"] += target_res_label
                        with open(dst_f, "w", encoding="utf-8") as pf:
                            json.dump(meta, pf, indent=4)
                        stats.other_files_copied += 1
                    except Exception:
                        shutil.copy2(src_f, dst_f)
                        stats.other_files_copied += 1
                else:
                    shutil.copy2(src_f, dst_f)
                    stats.other_files_copied += 1

                current_count += 1
                if self.progress_callback and current_count % 50 == 0:
                    self.progress_callback(
                        current_count,
                        total_items,
                        filename,
                        f"Kopiere Konfigurationen ({current_count}/{total_items})"
                    )

            # 5. Process images in parallel
            lock = threading.Lock()

            def worker_fn(item: Tuple[str, str, str]) -> str:
                nonlocal current_count
                if self.cancel_event.is_set():
                    return "cancelled"

                src_f, dst_f, rel_f = item
                status = self._process_single_image(src_f, dst_f, rel_f)

                with lock:
                    current_count += 1
                    c = current_count
                    if status == "upscaled":
                        stats.upscaled_images += 1
                    elif status == "colormap_copied":
                        stats.colormaps_preserved += 1
                    else:
                        stats.errors += 1

                if self.progress_callback and (c % 25 == 0 or c == total_items):
                    self.progress_callback(
                        c,
                        total_items,
                        os.path.basename(src_f),
                        f"Skaliere Texturen ({c}/{total_items})"
                    )
                return status

            with ThreadPoolExecutor(max_workers=self.num_workers) as executor:
                list(executor.map(worker_fn, tasks))

            if self.cancel_event.is_set():
                raise InterruptedError("Vorgang wurde vom Benutzer abgebrochen.")

            # 6. Repack to zip if destination requested zip
            if is_output_zip:
                if self.progress_callback:
                    self.progress_callback(total_items, total_items, os.path.basename(output_path), "Erstelle ZIP-Archiv...")
                out_dir = os.path.dirname(output_path)
                if out_dir:
                    os.makedirs(out_dir, exist_ok=True)
                with zipfile.ZipFile(output_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                    for root, _, files in os.walk(work_dst):
                        for f in files:
                            full_f = os.path.join(root, f)
                            rel_zip = os.path.relpath(full_f, work_dst)
                            zf.write(full_f, rel_zip)

            stats.elapsed_seconds = time.time() - t0
            stats.output_path = output_path
            return stats

        finally:
            if temp_input_dir and os.path.exists(temp_input_dir):
                shutil.rmtree(temp_input_dir, ignore_errors=True)
            if temp_output_dir and os.path.exists(temp_output_dir):
                shutil.rmtree(temp_output_dir, ignore_errors=True)

    def _process_single_image(self, src_path: str, dst_path: str, rel_path: str) -> str:
        # Colormap protection
        rel_norm = rel_path.replace("\\", "/").lower()
        if "textures/colormap" in rel_norm:
            shutil.copy2(src_path, dst_path)
            return "colormap_copied"

        try:
            with Image.open(src_path) as img:
                orig_format = img.format or "PNG"

                # Check if it's an animation
                mcmeta_path = src_path + ".mcmeta"
                has_animation_mcmeta = False
                if os.path.exists(mcmeta_path):
                    try:
                        with open(mcmeta_path, "r", encoding="utf-8") as mf:
                            mdata = json.load(mf)
                            if "animation" in mdata:
                                has_animation_mcmeta = True
                    except Exception:
                        pass

                im_rgba = img.convert("RGBA")
                arr = np.array(im_rgba)
                H, W, _ = arr.shape

                # Multi-frame vertical animation strip
                if has_animation_mcmeta or (H > W and H % W == 0 and W in (8, 16, 32, 64, 128)):
                    frame_h = W
                    num_frames = H // frame_h
                    frames_out = []
                    for i in range(num_frames):
                        frame_arr = arr[i * frame_h : (i + 1) * frame_h, :, :]
                        frames_out.append(upscale_image_array(frame_arr, self.algorithm, self.factor))
                    out_arr = np.concatenate(frames_out, axis=0)
                else:
                    out_arr = upscale_image_array(arr, self.algorithm, self.factor)

                out_img = Image.fromarray(out_arr, "RGBA")
                out_img.save(dst_path, format=orig_format, optimize=True)
                return "upscaled"
        except Exception as e:
            shutil.copy2(src_path, dst_path)
            return f"error: {e}"
