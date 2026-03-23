from google import genai
import os
import re
import warnings
from dotenv import load_dotenv
from api_key_manager import APIKeyManager

warnings.filterwarnings("ignore", category=FutureWarning)
load_dotenv()

_key_manager = None
_model_name = None

def init_engine(api_keys_str: str):

    global _key_manager, _model_name
    _key_manager = APIKeyManager(api_keys_str)
    client = _key_manager.get_current_client()
    _model_name = _choose_working_model(client)
    print(f"✅ [AI] Sử dụng model: {_model_name} (với key {_key_manager.current_index+1})")

def _get_key_manager():

    global _key_manager
    if _key_manager is None:

        keys_str = os.getenv("GEMINI_API_KEYS", "")
        _key_manager = APIKeyManager(keys_str)
        client = _key_manager.get_current_client()
        global _model_name
        _model_name = _choose_working_model(client)
        print(f"✅ [AI] Tự động khởi tạo với key từ env. Model: {_model_name}")
    return _key_manager

def _get_model_name():

    global _model_name
    if _model_name is None:

        _get_key_manager()
    return _model_name

def _choose_working_model(client):

    try:
        models = client.models.list()
        for model in models:
            if 'generateContent' in str(model.supported_actions):
                if 'flash' in model.name:
                    return model.name
        return "models/gemini-1.5-flash"
    except Exception as e:
        print(f"⚠️ [Hệ thống] Không liệt kê được model, dùng mặc định: {e}")
        return "models/gemini-1.5-flash"

def solve_question(question_text, options=None, is_fill_blank=False):

    # Lấy key_manager và model hiện tại
    key_manager = _get_key_manager()
    model_name = _get_model_name()

    if not question_text or question_text.strip() == "" or "N/A" in question_text:
        if not re.search(r'[a-zA-Z]{2,}', str(question_text)):
            print("❓ [AI] Cảnh báo: Dữ liệu câu hỏi quá ngắn hoặc trống.")
            return None


    clean_q = re.sub(r'#\d+', '', question_text)
    clean_q = re.sub(r'Đáp án:.*?(SKIP|\d+)', '', clean_q, flags=re.IGNORECASE).strip()

    if is_fill_blank:
        prompt = f"""
        Nhiệm vụ: Điền từ/cụm từ còn thiếu vào chỗ trống trong câu hỏi sau : 
        Câu hỏi: {clean_q}
        Yêu cầu:
        - Chỉ trả về từ/cụm từ cần điền, không thêm bất kỳ ký tự nào khác.
        - Nếu không chắc chắn, trả về chuỗi rỗng.
        - KHÔNG giải thích, KHÔNG lập luận.
        - Ví dụ: Nếu kết quả là 68, chỉ viết: 68
        - TUYỆT ĐỐI KHÔNG trả về "SKIP" hoặc bất kỳ từ nào khác.
        """
        print(f"🧠 [AI] Đang giải dạng ĐIỀN Ô...")
    else:

        opts = options or {}
        prompt = f"""
        Nhiệm vụ: Giải câu hỏi trắc nghiệm sau.
        Câu hỏi: {clean_q}
        Các phương án:
        A. {opts.get('A', 'N/A')}
        B. {opts.get('B', 'N/A')}
        C. {opts.get('C', 'N/A')}
        D. {opts.get('D', 'N/A')}
        Quy trình thực hiện:
        1. Phân tích nội dung câu hỏi và xác định kiến thức liên quan.
        2. Kiểm tra từng phương án A, B, C, D xem phương án nào khớp với kiến thức chuẩn.
        3. Tuyệt đối không chọn các phương án có nội dung là "N/A".
        Kết quả cuối cùng:
        Chỉ trả về duy nhất 1 ký tự là chữ cái của đáp án đúng (A, B, C, hoặc D). Không giải thích thêm.
        """
        print(f"🧠 [AI] Đang giải dạng KHOANH (A,B,C,D)...")

    max_retries = len(key_manager.working_keys) * 2  # số lần thử tối đa
    for attempt in range(max_retries):
        try:

            client = key_manager.get_current_client()
            response = client.models.generate_content(
                model=model_name,
                contents=prompt
            )
            

            if response is None or not hasattr(response, 'text') or response.text is None:
                print("⚠️ [AI] Response không có nội dung (None)")
                # Xem như lỗi, xoay key và thử lại
                if key_manager.rotate_on_error(Exception("Empty response")):
                    print(f"🔄 [AI] Đã chuyển sang key {key_manager.current_index+1} do response rỗng")
                    continue
                else:
                    return None
            
            res_text = response.text.strip()

            if is_fill_blank:
                ans = res_text.replace('"', '').replace('.', '').strip()
                # Lọc kết quả không hợp lệ 
                if ans.upper() == "SKIP" or len(ans) > 100:
                    print(f"⚠️ [AI] Kết quả không hợp lệ: '{ans}'")
                    return None
                print(f"🤖 [AI Kết quả] Từ cần điền: '{ans}'")
                return ans
            else:
                match = re.search(r"\b[A-D]\b", res_text.upper())
                if match:
                    ans = match.group(0)
                    print(f"🤖 [AI Kết quả] Đáp án chọn: {ans}")
                    return ans
                else:
                    print(f"⚠️ [AI] Không tìm thấy đáp án trong: {res_text}")
                    return None
        except Exception as e:
            print(f"❌ [AI Lỗi] {e}")
            # Xử lý xoay key
            if key_manager.rotate_on_error(e):

                print(f"🔄 [AI] Đã chuyển sang key {key_manager.current_index+1}")
                continue
            else:
                if "429" in str(e):
                    return "RETRY"
                return None
    return None

def solve_true_false(question_text):

    key_manager = _get_key_manager()
    model_name = _get_model_name()

    clean_q = re.sub(r'#\d+', '', question_text)
    clean_q = re.sub(r'Đáp án:.*?(SKIP|\d+)', '', clean_q, flags=re.IGNORECASE).strip()

    prompt = f"""
    Cho câu hỏi sau (có thể kèm các phát biểu a, b, c, d):
    {clean_q}

    Hãy xác định các phát biểu a, b, c, d là đúng hay sai.
    Trả về kết quả theo định dạng:
    a: Đúng
    b: Sai
    c: Đúng
    d: Sai
    (Chỉ trả về các dòng này, không thêm giải thích hay ký tự khác)
    """
    max_retries = len(key_manager.working_keys) * 2
    for attempt in range(max_retries):
        try:
            client = key_manager.get_current_client()
            response = client.models.generate_content(
                model=model_name,
                contents=prompt
            )
            
            # Kiểm tra response
            if response is None or not hasattr(response, 'text') or response.text is None:
                print("⚠️ [AI] Response không có nội dung (None)")
                if key_manager.rotate_on_error(Exception("Empty response")):
                    print(f"🔄 [AI] Đã chuyển sang key {key_manager.current_index+1} do response rỗng")
                    continue
                else:
                    return None

            res_text = response.text.strip()
            lines = res_text.split('\n')
            results = {}
            for line in lines:
                line = line.strip()
                if ':' in line:
                    key, val = line.split(':', 1)
                    key = key.strip().lower()
                    val = val.strip().lower()
                    if key in ['a', 'b', 'c', 'd'] and val in ['đúng', 'sai']:
                        results[key] = 'Đúng' if val == 'đúng' else 'Sai'
            if len(results) == 4:
                print(f"🤖 [AI Kết quả] {results}")
                return results
            else:
                print(f"⚠️ [AI] Kết quả không đầy đủ: {res_text}")
                return None
        except Exception as e:
            print(f"❌ [AI Lỗi] {e}")
            if key_manager.rotate_on_error(e):
                print(f"🔄 [AI] Đã chuyển sang key {key_manager.current_index+1}")
                continue
            else:
                if "429" in str(e):
                    return "RETRY"
                return None
    return None