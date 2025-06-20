import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk, ImageFilter, ImageEnhance
import time, os, threading, multiprocessing, queue
from multiprocessing import Pool, cpu_count, Manager

# Multiprocessing worker for simple filters
def multiprocess_worker(args):
    name, path, filter_name = args
    img = Image.open(path)
    if filter_name == "Grayscale": img = img.convert("L").convert("RGB")
    elif filter_name == "Blur": img = img.filter(ImageFilter.BLUR)
    elif filter_name == "Box Blur": img = img.filter(ImageFilter.BoxBlur(5))
    elif filter_name == "Gaussian Blur": img = img.filter(ImageFilter.GaussianBlur(radius=5))
    elif filter_name == "Contour": img = img.filter(ImageFilter.CONTOUR)
    elif filter_name == "Emboss": img = img.filter(ImageFilter.EMBOSS)
    elif filter_name == "Edge Enhance": img = img.filter(ImageFilter.EDGE_ENHANCE)
    elif filter_name == "Brightness +": img = ImageEnhance.Brightness(img).enhance(1.5)
    elif filter_name == "Brightness -": img = ImageEnhance.Brightness(img).enhance(0.7)
    elif filter_name == "Negative": img = Image.eval(img, lambda x: 255 - x)
    return (name, img)

class ModernImageFilterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Modern Image Filter App")
        self.root.geometry("700x760")
        self.root.configure(bg="#f0f4f8")

        self.original_images = []  # (name, img, path)
        self.filtered_images = []
        self.image_tk_refs = []

        style = ttk.Style(root)
        style.theme_use('clam')
        style.configure("TButton", font=("Segoe UI", 11), padding=6,
                        foreground="#fff", background="#4a90e2", borderwidth=0)
        style.map("TButton", background=[("active", "#357ABD")])
        style.configure("TMenubutton", font=("Segoe UI", 11), padding=5)

        ctrl = ttk.Frame(root, padding=10)
        ctrl.pack(fill='x')

        ttk.Button(ctrl, text="Load Folder", command=self.load_images_folder)\
            .grid(row=0, column=0, padx=5, pady=5)
        self.filter_var = tk.StringVar(root)
        ttk.OptionMenu(ctrl, self.filter_var, "Select Filter",
            "Grayscale", "Blur", "Box Blur", "Gaussian Blur", "Contour", "Emboss",
            "Edge Enhance", "Brightness +", "Brightness -", "Negative")\
            .grid(row=0, column=1, padx=5, pady=5)

        ttk.Button(ctrl, text="Apply Sequential", command=self.apply_filter_sequential)\
            .grid(row=0, column=2, padx=5)
        ttk.Button(ctrl, text="Apply Multithread", command=self.apply_filter_multithread)\
            .grid(row=1, column=0, padx=5)
        ttk.Button(ctrl, text="Apply Multiprocess", command=self.apply_filter_multiprocess)\
            .grid(row=1, column=1, padx=5)
        ttk.Button(ctrl, text="Prod-Cons (Thread)", command=self.apply_filter_producer_consumer_thread)\
            .grid(row=2, column=0, padx=5)
        ttk.Button(ctrl, text="Prod-Cons (Process)", command=self.apply_filter_producer_consumer_process)\
            .grid(row=2, column=1, padx=5)
        ttk.Button(ctrl, text="Dining Philos (Thread)", command=self.apply_filter_dining_thread)\
            .grid(row=3, column=0, padx=5)
        ttk.Button(ctrl, text="Dining Philos (Process)", command=self.apply_filter_dining_process)\
            .grid(row=3, column=1, padx=5)
        ttk.Button(ctrl, text="Save All Filtered", command=self.save_all_filtered_images)\
            .grid(row=4, column=0, columnspan=2, pady=10)

        disp = ttk.Frame(root)
        disp.pack(fill='both', expand=True)
        self.canvas = tk.Canvas(disp, bg="#e7ecf5")
        scrollbar = ttk.Scrollbar(disp, orient="vertical", command=self.canvas.yview)
        scrollbar.pack(side="right", fill="y")
        self.pic_frame = ttk.Frame(self.canvas)
        self.pic_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0,0), window=self.pic_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.pack(fill='both', expand=True)

        self.info = ttk.Label(root, text="Load a folder to start", font=("Segoe UI",10), foreground="#555")
        self.info.pack(pady=5)

        # Semaphore control for threading
        self.thread_semaphore = threading.Semaphore(8)
        self.lock = threading.Lock()
        self.max_threads_used = 0

    def load_images_folder(self):
        d = filedialog.askdirectory()
        if not d:
            return
        self.original_images.clear()
        self.filtered_images.clear()
        self.image_tk_refs.clear()
        for w in self.pic_frame.winfo_children():
            w.destroy()

        exts = ('.jpg', '.jpeg', '.png', '.bmp')
        fns = [fn for fn in os.listdir(d) if fn.lower().endswith(exts)]
        if not fns:
            messagebox.showwarning("No images", "Nothing here!")
            return

        for fn in fns:
            p = os.path.join(d, fn)
            try:
                img = Image.open(p)
                self.original_images.append((fn, img, p))
            except:
                pass

        self.info.config(text=f"Loaded {len(self.original_images)} images")
        self.show_images([(n, i) for n, i, _ in self.original_images])

    def show_images(self, images):
        for w in self.pic_frame.winfo_children():
            w.destroy()
        self.image_tk_refs.clear()
        thumbsiz = (150,150)

        for idx, (n, img) in enumerate(images):
            t = img.copy(); t.thumbnail(thumbsiz)
            tkimg = ImageTk.PhotoImage(t)
            self.image_tk_refs.append(tkimg)
            frame = ttk.Frame(self.pic_frame, relief="ridge", borderwidth=1)
            frame.grid(row=idx//4, column=idx%4, padx=5, pady=5)
            ttk.Label(frame, image=tkimg).pack()
            ttk.Label(frame, text=n, font=("Segoe UI",9)).pack()

    def apply_filter(self, img, filt):
        if filt=="Grayscale": return img.convert("L").convert("RGB")
        if filt=="Blur": return img.filter(ImageFilter.BLUR)
        if filt=="Box Blur": return img.filter(ImageFilter.BoxBlur(5))
        if filt=="Gaussian Blur": return img.filter(ImageFilter.GaussianBlur(radius=5))
        if filt=="Contour": return img.filter(ImageFilter.CONTOUR)
        if filt=="Emboss": return img.filter(ImageFilter.EMBOSS)
        if filt=="Edge Enhance": return img.filter(ImageFilter.EDGE_ENHANCE)
        if filt=="Brightness +": return ImageEnhance.Brightness(img).enhance(1.5)
        if filt=="Brightness -": return ImageEnhance.Brightness(img).enhance(0.7)
        if filt=="Negative": return Image.eval(img, lambda x:255-x)
        return img

    def apply_filter_sequential(self):
        if not self.original_images:
            messagebox.showwarning("Oops", "Load images!")
            return
        f = self.filter_var.get()
        if f=="Select Filter":
            messagebox.showwarning("Oops", "Choose filter!")
            return
        st = time.time()
        out = [(n, self.apply_filter(i, f)) for n, i, _ in self.original_images]
        et = time.time()
        self.filtered_images = out
        self.show_images(out)
        self.info.config(text=f"Sequential done in {et-st:.3f}s")

    def apply_filter_multithread(self):
        if not self.original_images:
            messagebox.showwarning("Oops", "Load images!")
            return
        f = self.filter_var.get()
        if f=="Select Filter":
            messagebox.showwarning("Oops", "Choose filter!")
            return

        st = time.time()
        L = len(self.original_images)
        out = [None]*L
        self.max_threads_used = 0
        active = 0

        def worker(idx, name, img):
            nonlocal active
            with self.thread_semaphore:
                with self.lock:
                    active += 1
                    if active > self.max_threads_used:
                        self.max_threads_used = active
                filtered = self.apply_filter(img, f)
                out[idx] = (name, filtered)
                with self.lock:
                    active -= 1

        threads = []
        for idx, (n, i, _) in enumerate(self.original_images):
            t = threading.Thread(target=worker, args=(idx, n, i))
            threads.append(t)
            t.start()
        for t in threads:
            t.join()
        et = time.time()

        self.filtered_images = out
        self.show_images(out)
        self.info.config(text=f"Multithread done in {et-st:.3f}s | max threads = {self.max_threads_used}")

    def apply_filter_multiprocess(self):
        if not self.original_images:
            messagebox.showwarning("Oops", "Load images!")
            return
        f = self.filter_var.get()
        if f=="Select Filter":
            messagebox.showwarning("Oops", "Choose filter!")
            return

        args = [(n, p, f) for n, _, p in self.original_images]
        st = time.time()
        with Pool(cpu_count()) as pool:
            res = pool.map(multiprocess_worker, args)
        et = time.time()

        self.filtered_images = res
        self.show_images(res)
        self.info.config(text=f"Multiprocess done in {et-st:.3f}s")

    def apply_filter_producer_consumer_thread(self):
        if not self.original_images:
            messagebox.showwarning("Oops", "Load images!")
            return
        f = self.filter_var.get()
        if f=="Select Filter":
            messagebox.showwarning("Oops", "Choose filter!")
            return

        st = time.time()
        q = queue.Queue(maxsize=4)
        L = len(self.original_images)
        out = [None]*L

        def producer():
            for idx, (n, i, _) in enumerate(self.original_images):
                q.put((idx, n, i))
            for _ in range(4):
                q.put(None)

        def consumer():
            while True:
                it = q.get()
                if it is None:
                    break
                idx, n, i = it
                out[idx] = (n, self.apply_filter(i, f))
                q.task_done()

        pt = threading.Thread(target=producer)
        consumers = [threading.Thread(target=consumer) for _ in range(4)]

        pt.start()
        for c in consumers: c.start()
        pt.join()
        for c in consumers: c.join()

        et = time.time()
        self.filtered_images = out
        self.show_images(out)
        self.info.config(text=f"P-C Thread done in {et-st:.3f}s")

    def apply_filter_producer_consumer_process(self):
        if not self.original_images:
            messagebox.showwarning("Oops", "Load images!")
            return
        f = self.filter_var.get()
        if f=="Select Filter":
            messagebox.showwarning("Oops", "Choose filter!")
            return

        st = time.time()
        mgr = Manager()
        task = mgr.Queue()
        done = mgr.Queue()
        L = len(self.original_images)

        def producer():
            for idx, (n, _, p) in enumerate(self.original_images):
                task.put((idx, n, p))
            for _ in range(cpu_count()):
                task.put(None)

        def consumer():
            while True:
                it = task.get()
                if it is None:
                    break
                idx, n, p = it
                img = Image.open(p)
                img = multiprocess_worker((n, p, f))[1]
                done.put((idx, n, img))

        procs = [multiprocessing.Process(target=consumer) for _ in range(cpu_count())]
        p = multiprocessing.Process(target=producer)
        p.start()
        for pr in procs:
            pr.start()

        res = [None]*L
        for _ in range(L):
            idx, n, img = done.get()
            res[idx] = (n, img)

        p.join()
        for pr in procs:
            pr.join()
        et = time.time()

        self.filtered_images = res
        self.show_images(res)
        self.info.config(text=f"P-C Process done in {et-st:.3f}s")

    def apply_filter_dining_thread(self):
        if not self.original_images:
            messagebox.showwarning("Oops", "Load images!")
            return
        f = self.filter_var.get()
        if f=="Select Filter":
            messagebox.showwarning("Oops", "Choose filter!")
            return

        total = len(self.original_images)
        ph = 5
        forks = [threading.Semaphore(1) for _ in range(ph)]
        filtered = [None]*total
        st = time.time()

        for batch_start in range(0, total, ph):
            batch = self.original_images[batch_start:batch_start+ph]
            threads = []

            def philosopher(idx_global, name, img, i_batch):
                left = forks[i_batch]
                right = forks[(i_batch+1)%ph]
                with left, right:
                    filtered[idx_global] = (name, self.apply_filter(img, f))

            for i_batch, (name, img, _) in enumerate(batch):
                idx_global = batch_start + i_batch
                t = threading.Thread(target=philosopher, args=(idx_global, name, img, i_batch))
                threads.append(t)
                t.start()
            for t in threads:
                t.join()

        et = time.time()
        self.filtered_images = filtered
        self.show_images(filtered)
        self.info.config(text=f"Dining(Thread) done in {et-st:.3f}s")

    def apply_filter_dining_process(self):
        if not self.original_images:
            messagebox.showwarning("Oops", "Load images!")
            return
        f = self.filter_var.get()
        if f=="Select Filter":
            messagebox.showwarning("Oops", "Choose filter!")
            return

        total = len(self.original_images)
        ph = 5
        mgr = Manager()
        forks = [mgr.Semaphore(1) for _ in range(ph)]
        filtered = mgr.list([None]*total)
        st = time.time()

        def phil_process(idx_global, name, path, i_batch, forks, filt):
            left = forks[i_batch]
            right = forks[(i_batch+1)%ph]
            with left, right:
                img = Image.open(path)
                img = multiprocess_worker((name, path, filt))[1]
                filtered[idx_global] = (name, img)

        processes = []

        for batch_start in range(0, total, ph):
            batch = self.original_images[batch_start:batch_start+ph]
            for i_batch, (name, _, path) in enumerate(batch):
                idx_global = batch_start + i_batch
                p = multiprocessing.Process(target=phil_process,
                    args=(idx_global, name, path, i_batch, forks, f))
                processes.append(p)
                p.start()
            for p in processes:
                p.join()
            processes.clear()

        et = time.time()
        self.filtered_images = list(filtered)
        self.show_images(self.filtered_images)
        self.info.config(text=f"Dining(Process) done in {et-st:.3f}s")

    def save_all_filtered_images(self):
        if not self.filtered_images:
            messagebox.showwarning("Oops", "Nothing to save!")
            return
        d = filedialog.askdirectory()
        if not d:
            return
        for n, img in self.filtered_images:
            fn, ext = os.path.splitext(n)
            img.save(os.path.join(d, fn + "_filt" + ext))
        messagebox.showinfo("Saved", f"Saved {len(self.filtered_images)} images!")

if __name__ == "__main__":
    multiprocessing.freeze_support()
    root = tk.Tk()
    app = ModernImageFilterApp(root)
    root.mainloop()

