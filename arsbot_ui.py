import customtkinter as ctk
import threading
import sys
import os
import webbrowser
import queue
from PIL import Image
from bot import run_bot

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")

class RedirectText:
    def __init__(self, textbox):
        self.textbox = textbox

    def write(self, string):
        self.textbox.insert("end", string)
        self.textbox.see("end")

    def flush(self):
        pass

class ArsBotUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("ARSBOT V1.8 - Multi Account")
        self.geometry("1000x800")
        self.minsize(800, 650)

        try:
            self.iconbitmap("icon.ico")
        except:
            pass
        if getattr(sys, "frozen", False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(__file__)

        self.configure(fg_color="#1a1a1a")

        self.main = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.main.pack(fill="both", expand=True, padx=20, pady=20)

        header_frame = ctk.CTkFrame(self.main, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 20))
        rikka_path = os.path.join(base_path, "rikka111.ico")
        if os.path.exists(rikka_path):
            img = Image.open(rikka_path)
            img = img.resize((100, 100))
            self.avatar = ctk.CTkImage(light_image=img, dark_image=img, size=(100, 100))
            avatar_label = ctk.CTkLabel(header_frame, image=self.avatar, text="")
            avatar_label.pack(pady=5)

        # Tiêu đề
        title = ctk.CTkLabel(
            header_frame,
            text="ARSBOT CONTROL PANEL",
            font=ctk.CTkFont(size=32, weight="bold")
        )
        title.pack()

        # Link Discord, Facebook, Wiki
        link_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        link_frame.pack(pady=10)

        discord = ctk.CTkLabel(
            link_frame,
            text="🌐 Discord",
            text_color="#7289da",
            cursor="hand2",
            font=ctk.CTkFont(size=14, weight="bold", underline=True)
        )
        discord.pack(side="left", padx=10)
        discord.bind("<Button-1>", lambda e: webbrowser.open("https://discord.gg/XjSRYTsjSZ"))

        sep1 = ctk.CTkLabel(link_frame, text="|", text_color="#aaaaaa")
        sep1.pack(side="left")

        facebook = ctk.CTkLabel(
            link_frame,
            text="📘 Facebook",
            text_color="#1877f2",
            cursor="hand2",
            font=ctk.CTkFont(size=14, weight="bold", underline=True)
        )
        facebook.pack(side="left", padx=10)
        facebook.bind("<Button-1>", lambda e: webbrowser.open("https://www.facebook.com/ohieu.001"))

        sep2 = ctk.CTkLabel(link_frame, text="|", text_color="#aaaaaa")
        sep2.pack(side="left")

        wiki = ctk.CTkLabel(
            link_frame,
            text="📖 Wiki",
            text_color="#00d4ff",
            cursor="hand2",
            font=ctk.CTkFont(size=14, weight="bold", underline=True)
        )
        wiki.pack(side="left", padx=10)
        wiki.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/Jpx1209/Auto-app-onluyen-"))

        # ---------- Khu vực chính: chia 2 cột ----------
        columns_frame = ctk.CTkFrame(self.main, fg_color="transparent")
        columns_frame.pack(fill="both", expand=True, pady=10)

        columns_frame.grid_columnconfigure(0, weight=1, uniform="col")
        columns_frame.grid_columnconfigure(1, weight=1, uniform="col")
        columns_frame.grid_rowconfigure(0, weight=1)

        # --- Cột trái: Tài khoản & API ---
        left_panel = ctk.CTkFrame(columns_frame, fg_color="#2b2b2b", corner_radius=15)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        # Accounts section
        account_section = ctk.CTkFrame(left_panel, fg_color="transparent")
        account_section.pack(fill="x", padx=20, pady=(20, 10))

        ctk.CTkLabel(account_section, text="👥 Danh sách tài khoản", font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(account_section, text="Mỗi dòng: username | password", font=ctk.CTkFont(size=12)).pack(anchor="w", pady=(5, 0))
        self.accounts = ctk.CTkTextbox(account_section, height=120, wrap="word")
        self.accounts.pack(fill="x", pady=(10, 10))

        # Gemini API
        api_section = ctk.CTkFrame(left_panel, fg_color="transparent")
        api_section.pack(fill="x", padx=20, pady=(10, 20))

        ctk.CTkLabel(api_section, text="🔑 Gemini API", font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w")
        api_frame = ctk.CTkFrame(api_section, fg_color="transparent")
        api_frame.pack(fill="x", pady=(10, 0))
        self.api = ctk.CTkEntry(api_frame, placeholder_text="key1,key2,key3", show="*")
        self.api.pack(side="left", fill="x", expand=True)
        self.api_show = False
        self.api_btn = ctk.CTkButton(api_frame, text="👁", width=35, command=self.toggle_api)
        self.api_btn.pack(side="right", padx=(5, 0))

        # --- Cột phải: Bài tập ---
        right_panel = ctk.CTkFrame(columns_frame, fg_color="#2b2b2b", corner_radius=15)
        right_panel.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        practice_section = ctk.CTkFrame(right_panel, fg_color="transparent")
        practice_section.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(practice_section, text="📚 Bài tập", font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(practice_section, text="Link bài tập (mỗi link một dòng)").pack(anchor="w", pady=(10, 0))
        self.url = ctk.CTkTextbox(practice_section, height=100, wrap="word")
        self.url.pack(fill="x", pady=(5, 10))

        ctk.CTkLabel(practice_section, text="Số câu hỏi tương ứng (cách nhau dấu phẩy, hoặc một số chung)").pack(anchor="w")
        self.questions = ctk.CTkEntry(practice_section, placeholder_text="VD: 20,10,10,30 hoặc 20")
        self.questions.pack(fill="x", pady=(5, 10))

        # ---------- Khu vực nút điều khiển ----------
        control_frame = ctk.CTkFrame(self.main, fg_color="transparent")
        control_frame.pack(pady=20)

        self.start_btn = ctk.CTkButton(
            control_frame,
            text="START BOT",
            width=180,
            height=45,
            font=ctk.CTkFont(size=16, weight="bold"),
            command=self.start_bot
        )
        self.start_btn.grid(row=0, column=0, padx=15)

        self.stop_btn = ctk.CTkButton(
            control_frame,
            text="STOP BOT",
            width=180,
            height=45,
            fg_color="#d32f2f",
            hover_color="#b71c1c",
            font=ctk.CTkFont(size=16, weight="bold"),
            command=self.stop_bot,
            state="disabled"
        )
        self.stop_btn.grid(row=0, column=1, padx=15)

        self.status = ctk.CTkLabel(self.main, text="⚙️ Status: Idle", font=ctk.CTkFont(size=14))
        self.status.pack(pady=(0, 10))

        # ---------- Khu vực Log ----------
        log_frame = ctk.CTkFrame(self.main, fg_color="#2b2b2b", corner_radius=15)
        log_frame.pack(fill="both", expand=True, pady=(0, 10))

        log_header = ctk.CTkFrame(log_frame, fg_color="transparent")
        log_header.pack(fill="x", padx=15, pady=(15, 5))
        ctk.CTkLabel(log_header, text="📋 SYSTEM LOG", font=ctk.CTkFont(size=16, weight="bold")).pack(side="left")

        self.log = ctk.CTkTextbox(log_frame, height=200, font=("Consolas", 12), wrap="word")
        self.log.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        self.bot_thread = None
        self.stop_event = None

    def toggle_api(self):
        if self.api_show:
            self.api.configure(show="*")
            self.api_btn.configure(text="👁")
        else:
            self.api.configure(show="")
            self.api_btn.configure(text="🙈")
        self.api_show = not self.api_show

    def start_bot(self):
        # Đọc danh sách tài khoản
        accounts_text = self.accounts.get("1.0", "end-1c").strip()
        if not accounts_text:
            self.log.insert("end", "❌ Chưa nhập tài khoản nào!\n")
            return

        accounts = []
        for line in accounts_text.splitlines():
            line = line.strip()
            if not line:
                continue
            if "|" not in line:
                self.log.insert("end", f"❌ Dòng không đúng định dạng (thiếu '|'): {line}\n")
                return
            username, password = line.split("|", 1)
            accounts.append((username.strip(), password.strip()))

        # Đọc API keys
        api_keys = self.api.get().strip()
        if not api_keys:
            self.log.insert("end", "❌ Chưa nhập Gemini API keys\n")
            return

        # Đọc link bài tập
        url_text = self.url.get("1.0", "end-1c").strip()
        urls = [line.strip() for line in url_text.splitlines() if line.strip()]
        if not urls:
            self.log.insert("end", "❌ Chưa nhập link bài tập\n")
            return

        # Đọc số câu
        q_text = self.questions.get().strip()
        if not q_text:
            self.log.insert("end", "❌ Chưa nhập số câu\n")
            return

        parts = [p.strip() for p in q_text.split(",")]
        if len(parts) == 1:
            try:
                common = int(parts[0])
                max_q_list = [common] * len(urls)
            except:
                self.log.insert("end", "⚠️ Số câu không hợp lệ, dùng mặc định 5.\n")
                max_q_list = [5] * len(urls)
        else:
            if len(parts) != len(urls):
                self.log.insert("end", f"⚠️ Số lượng số câu ({len(parts)}) không khớp với số link ({len(urls)}). Dùng mặc định 5 cho tất cả.\n")
                max_q_list = [5] * len(urls)
            else:
                max_q_list = []
                valid = True
                for p in parts:
                    try:
                        max_q_list.append(int(p))
                    except:
                        self.log.insert("end", f"⚠️ Giá trị '{p}' không hợp lệ, dùng mặc định 5.\n")
                        valid = False
                        break
                if not valid:
                    max_q_list = [5] * len(urls)

        practice_items = list(zip(urls, max_q_list))

        # Log kế hoạch
        self.log.delete("1.0", "end")
        self.log.insert("end", f"📋 Số tài khoản: {len(accounts)}\n")
        self.log.insert("end", "📋 Kế hoạch xử lý bài tập:\n")
        for idx, (url, q) in enumerate(practice_items, 1):
            self.log.insert("end", f"  Bài {idx}: {url} - {q} câu\n")
        self.log.insert("end", "\n")

        # Redirect stdout để log hiển thị trên giao diện
        sys.stdout = RedirectText(self.log)

        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.status.configure(text="⚙️ Status: Running")

        # Tạo stop_event
        self.stop_event = threading.Event()

        # Tạo thread chạy bot
        self.bot_thread = threading.Thread(
            target=self.run_bot_thread,
            args=(accounts, practice_items, api_keys, self.stop_event),
            daemon=True
        )
        self.bot_thread.start()

    def run_bot_thread(self, accounts, practice_items, api_keys, stop_event):
        try:
            # Gọi run_bot với log_queue=None để sử dụng print (redirected)
            run_bot(accounts, practice_items, api_keys, log_queue=None, headless=False, stop_event=stop_event)
        except Exception as e:
            print("ERROR:", e)
        self.after(0, self.finish)

    def finish(self):
        sys.stdout = sys.__stdout__
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.status.configure(text="⚙️ Status: Done")
        self.log.insert("end", "\n✅ Bot đã hoàn thành tất cả tài khoản\n")

    def stop_bot(self):
        if self.stop_event:
            self.stop_event.set()
            self.log.insert("end", "\n⏸️ Đang yêu cầu dừng bot...\n")
            self.status.configure(text="⚙️ Status: Stopping")
        else:
            self.log.insert("end", "\n⚠️ Bot chưa chạy.\n")

if __name__ == "__main__":
    if getattr(sys, "frozen", False):
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = os.path.join(
            sys._MEIPASS,
            "playwright",
            "browsers"
        )
    app = ArsBotUI()
    app.mainloop()