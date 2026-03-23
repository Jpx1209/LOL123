import os
import time
from google import genai

class APIKeyManager:
    def __init__(self, keys_str=None):
        if keys_str is None:
            keys_str = os.getenv("GEMINI_API_KEYS", "")
        self.keys = [k.strip() for k in keys_str.split(",") if k.strip()]
        self.current_index = 0
        self.working_keys = []
        self._validate_keys()

    def _validate_keys(self):
        print("🔍 [API Key Manager] Đang kiểm tra các API key...")
        working = []
        for i, key in enumerate(self.keys):
            try:
                client = genai.Client(api_key=key)
                client.models.list()
                print(f"   ✅ Key {i+1} hoạt động.")
                working.append(key)
            except Exception as e:
                print(f"   ❌ Key {i+1} không hoạt động: {e}")
        if not working:
            raise Exception("Không có API key nào hoạt động!")
        self.working_keys = working
        self.current_index = 0

    def get_current_client(self):
        if not self.working_keys:
            self._validate_keys()
        key = self.working_keys[self.current_index]
        return genai.Client(api_key=key)

    def chuyen_key(self):
        if len(self.working_keys) == 1:
            print("⚠️ [API Key Manager] Chỉ có một key hoạt động, không thể chuyển.")
            return False
        self.current_index = (self.current_index + 1) % len(self.working_keys)
        print(f"🔄 [API Key Manager] Chuyển sang key {self.current_index + 1}")
        return True

    def rotate_on_error(self, error):
        if hasattr(error, 'code') and error.code == 429:
            print("⚠️ [API Key Manager] Phát hiện rate limit (429), chuyển key...")
            return self.chuyen_key()  
        elif "API key not valid" in str(error) or "invalid" in str(error).lower():
            print("⚠️ [API Key Manager] Key không hợp lệ, chuyển key...")
            self.working_keys.pop(self.current_index)
            if not self.working_keys:
                raise Exception("Không còn key hoạt động!")
            self.current_index = min(self.current_index, len(self.working_keys)-1)
            return True
        return False