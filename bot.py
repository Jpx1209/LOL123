import time
import re
import json
import os
import sys
from playwright.sync_api import sync_playwright
from ai_engine import solve_question, solve_true_false

def log_msg(msg, log_queue=None):
    if log_queue:
        log_queue.put(msg)
    else:
        print(msg)

def log_question_to_file(filename, data):
    """Ghi log câu hỏi vào file JSON"""
    existing_data = []
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            try:
                existing_data = json.load(f)
            except:
                existing_data = []
    existing_data.append(data)
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(existing_data, f, ensure_ascii=False, indent=4)

def get_data_by_scraping(page, log_queue):
    """Cào dữ liệu câu hỏi và các phương án từ trang."""
    try:
        q_id_text = page.locator(".num").inner_text() if page.locator(".num").is_visible() else "unknown"
        q_id = re.sub(r'\D', '', q_id_text)

        question = page.evaluate("""() => {
            const qEl = document.querySelector('.question-name') || 
                        document.querySelector('.question-content-container');
            return qEl ? qEl.innerText.trim() : ""; 
        }""")

        options = {"A": "N/A", "B": "N/A", "C": "N/A", "D": "N/A"}

        # Cách 1: từ .row.options .col-md-12
        option_elements = page.locator(".row.options .col-md-12").all()
        labels = ["A", "B", "C", "D"]
        for i, el in enumerate(option_elements):
            if i < len(labels):
                raw_text = el.inner_text().strip()
                clean_text = re.sub(r'^[A-D][.)]\s*', '', raw_text)
                options[labels[i]] = clean_text

        # Cách 2: dùng regex tìm nhãn A., B., ...
        if all(v == "N/A" for v in options.values()):
            for char in labels:
                try:
                    opt = page.locator(f".options >> text=/^{char}[.)]/").first
                    if opt.is_visible():
                        options[char] = re.sub(r'^[A-D][.)]\s*', '', opt.inner_text()).strip()
                except: 
                    continue

        # Cách 3: tìm trong các thẻ label có for="option..." 
        if all(v == "N/A" for v in options.values()):
            for char in labels:
                label = page.locator(f"label:has-text('{char})'), label:has-text('{char}.')").first
                if label.is_visible():
                    full_text = label.inner_text().strip()
                    clean = re.sub(rf'^{char}[.)]\s*', '', full_text)
                    options[char] = clean

        log_msg(f"📊 Dữ liệu quét: Q: {question[:50]}... | Opts: {options}", log_queue)
        return q_id, question, options
    except Exception as e:
        log_msg(f"⚠️ [Lỗi quét] {e}", log_queue)
        return "unknown", "N/A", {"A": "N/A", "B": "N/A", "C": "N/A", "D": "N/A"}

def click_true_false(page, results, log_queue):
    """Xử lý click đúng/sai."""
    page.screenshot(path="debug_truefalse.png")
    log_msg("📸 Đã chụp debug_truefalse.png để kiểm tra giao diện", log_queue)
    clicked = 0

    labels = page.locator("label:has-text('Đúng'), label:has-text('Sai')").all()
    log_msg(f"🔍 Tìm thấy {len(labels)} label Đúng/Sai", log_queue)

    if len(labels) == 8:
        label_texts = [label.text_content().strip() for label in labels]
        log_msg(f"📝 Text các label: {label_texts}", log_queue)

        for idx, (key, value) in enumerate(results.items()):
            start = idx * 2
            if start + 1 >= len(labels):
                break
            label1 = labels[start]
            label2 = labels[start+1]
            text1 = label1.text_content().strip()
            text2 = label2.text_content().strip()

            if text1 == "Đúng" and text2 == "Sai":
                target = label1 if value == "Đúng" else label2
            elif text1 == "Sai" and text2 == "Đúng":
                target = label2 if value == "Đúng" else label1
            else:
                if text1 == value:
                    target = label1
                elif text2 == value:
                    target = label2
                else:
                    log_msg(f"   ⚠️ Không tìm thấy label {value} cho {key}", log_queue)
                    continue
            try:
                target.click(force=True)
                clicked += 1
                log_msg(f"   ✅ Đã chọn {key} {value} (cách 1 - label cặp)", log_queue)
            except:
                log_msg(f"   ❌ Không click được label cho {key}", log_queue)
        return clicked

    elif len(labels) == 4:
        for idx, (key, value) in enumerate(results.items()):
            if idx >= len(labels):
                break
            label = labels[idx]
            label_text = label.text_content().strip()
            if label_text == value:
                try:
                    label.click(force=True)
                    clicked += 1
                    log_msg(f"   ✅ Đã chọn {key} {value} (cách 1 - label đơn)", log_queue)
                except:
                    pass
            else:
                log_msg(f"   ⚠️ Label {key} có text '{label_text}' không khớp {value}", log_queue)
        return clicked

    log_msg("⚠️ Không tìm thấy đủ label, chuyển sang tìm button", log_queue)
    buttons = page.locator("button:has-text('Đúng'), button:has-text('Sai')").all()
    log_msg(f"🔍 Tìm thấy {len(buttons)} button Đúng/Sai", log_queue)

    if len(buttons) == 8:
        for idx, (key, value) in enumerate(results.items()):
            start = idx * 2
            if start + 1 >= len(buttons):
                break
            btn1 = buttons[start]
            btn2 = buttons[start+1]
            text1 = btn1.text_content().strip()
            text2 = btn2.text_content().strip()
            if text1 == "Đúng" and text2 == "Sai":
                target = btn1 if value == "Đúng" else btn2
            elif text1 == "Sai" and text2 == "Đúng":
                target = btn2 if value == "Đúng" else btn1
            else:
                if text1 == value:
                    target = btn1
                elif text2 == value:
                    target = btn2
                else:
                    continue
            try:
                target.click(force=True)
                clicked += 1
                log_msg(f"   ✅ Đã chọn {key} {value} (cách 2 - button cặp)", log_queue)
            except:
                pass
        return clicked

    elif len(buttons) == 4:
        for idx, (key, value) in enumerate(results.items()):
            if idx >= len(buttons):
                break
            btn = buttons[idx]
            btn_text = btn.text_content().strip()
            if btn_text == value:
                try:
                    btn.click(force=True)
                    clicked += 1
                    log_msg(f"   ✅ Đã chọn {key} {value} (cách 2 - button đơn)", log_queue)
                except:
                    pass
        return clicked

    log_msg("⚠️ Không tìm thấy đủ button, chuyển sang cách dùng XPath", log_queue)
    for key, value in results.items():
        label_text = f"{key})"
        xpath = f"//*[contains(text(), '{label_text}')]/following::button[contains(text(), '{value}')][1]"
        try:
            btn = page.locator(xpath).first
            if btn.is_visible(timeout=500):
                btn.click(force=True)
                clicked += 1
                log_msg(f"   ✅ Đã chọn {key} {value} (cách 3 - XPath button)", log_queue)
                continue
        except:
            pass

        xpath = f"//*[contains(text(), '{label_text}')]/following::label[contains(text(), '{value}')][1]"
        try:
            lbl = page.locator(xpath).first
            if lbl.is_visible(timeout=500):
                lbl.click(force=True)
                clicked += 1
                log_msg(f"   ✅ Đã chọn {key} {value} (cách 3 - XPath label)", log_queue)
                continue
        except:
            pass
        log_msg(f"   ❌ Không tìm thấy nút cho {key} {value} (cách 3)", log_queue)
    return clicked

def process_account(page, username, password, practice_items, api_keys, log_queue, stop_event=None):
    """
    Xử lý một tài khoản: đăng nhập và làm tất cả bài tập.
    log_queue: Queue để gửi log về client (có thể None).
    stop_event: threading.Event để dừng sớm.
    """
    from ai_engine import init_engine
    init_engine(api_keys)

    log_msg(f"🚀 [Hệ thống] Đang khởi động đăng nhập cho tài khoản: {username}", log_queue)
    page.goto("https://app.onluyen.vn/login")

    try:
        page.fill("input[placeholder*='đăng nhập']", username)
        page.fill("input[placeholder='Mật khẩu']", password)
        page.click("button:has-text('Đăng nhập')")
        page.wait_for_url("**/home-student", timeout=20000)
        log_msg("✅ [Hệ thống] Login thành công!", log_queue)
    except Exception as e:
        log_msg(f"❌ [Hệ thống] Login thất bại cho {username}: {e}", log_queue)
        return

    for idx, (practice_url, max_questions) in enumerate(practice_items, start=1):
        if stop_event and stop_event.is_set():
            log_msg("⏹️ [Hệ thống] Nhận lệnh dừng, bỏ qua bài tập tiếp theo.", log_queue)
            return

        log_msg(f"\n📌 [Bài tập {idx}/{len(practice_items)}] Đang xử lý: {practice_url} (số câu: {max_questions})", log_queue)
        page.goto(practice_url)
        page.wait_for_load_state("domcontentloaded")
        time.sleep(2)

        # Xử lý nút BẮT ĐẦU / TIẾP TỤC
        try:
            if page.locator(".num, .question-name, .question-content-container").first.is_visible(timeout=3000):
                log_msg("ℹ️ Đã ở trang làm bài, bỏ qua bước bắt đầu.", log_queue)
            else:
                start_clicked = False
                start_btn = page.locator("div.btn-test.green.ng-star-inserted").first
                if start_btn.is_visible(timeout=2000):
                    start_btn.click(force=True)
                    start_clicked = True
                    log_msg("🔘 Đã click nút (class btn-test.green).", log_queue)

                if not start_clicked:
                    start_btn = page.locator("button:has-text('Bắt đầu'), a:has-text('Bắt đầu'), button:has-text('Tiếp tục'), a:has-text('Tiếp tục')").first
                    if start_btn.is_visible(timeout=2000):
                        start_btn.click(force=True)
                        start_clicked = True
                        log_msg(f"🔘 Đã click nút '{start_btn.text_content().strip()}' (text).", log_queue)

                if not start_clicked:
                    selectors = [
                        ".btn-start",
                        ".start-button",
                        "button.green",
                        ".btn-test",
                        "//button[contains(text(), 'Bắt đầu')]",
                        "//a[contains(text(), 'Bắt đầu')]",
                        "//button[contains(text(), 'Tiếp tục')]",
                        "//a[contains(text(), 'Tiếp tục')]"
                    ]
                    for sel in selectors:
                        if sel.startswith("//"):
                            btn = page.locator(f"xpath={sel}").first
                        else:
                            btn = page.locator(sel).first
                        if btn.is_visible(timeout=1000):
                            btn.click(force=True)
                            start_clicked = True
                            log_msg(f"🔘 Đã click nút (selector: {sel}).", log_queue)
                            break

                if start_clicked:
                    page.wait_for_selector(".num, .question-name, .question-content-container", timeout=15000)
                    log_msg("✅ Đã vào bài làm.", log_queue)
                else:
                    log_msg("⚠️ Không tìm thấy nút bắt đầu hoặc tiếp tục, tiếp tục...", log_queue)
        except Exception as e:
            log_msg(f"⚠️ Lỗi khi xử lý nút Bắt đầu/Tiếp tục: {e}", log_queue)

        for i in range(1, max_questions + 1):
            if stop_event and stop_event.is_set():
                log_msg("⏹️ [Hệ thống] Nhận lệnh dừng, thoát giữa chừng.", log_queue)
                return

            log_msg(f"\n🔍 [Câu {i}/{max_questions}] Đang quét nội dung...", log_queue)
            time.sleep(2)

            input_selector = "input[type='text'], .input-fill-blank, [contenteditable='true']"
            input_field = page.locator(input_selector).first
            is_fill_blank = input_field.is_visible(timeout=2000)

            if is_fill_blank:
                log_msg("📝 [Thông báo] Dạng bài: ĐIỀN Ô TRỐNG", log_queue)
                q_content = page.evaluate("() => document.querySelector('.question-content-container')?.innerText || document.body.innerText")
                id_match = re.search(r"#(\d+)", q_content)
                q_id = id_match.group(1) if id_match else f"fill_{i}"

                ans = solve_question(q_content, is_fill_blank=True)
                if ans == "RETRY":
                    time.sleep(5)
                    ans = solve_question(q_content, is_fill_blank=True)

                log_question_to_file("question-dien-o.json", {"id": q_id, "question": q_content, "answer": ans})

                if ans:
                    log_msg(f"⌨️ [Hệ thống] Đang điền: {ans}", log_queue)
                    input_field.click()
                    input_field.fill("")
                    input_field.type(ans, delay=60)
                else:
                    log_msg("⚠️ Không có đáp án, bỏ qua.", log_queue)
                    try:
                        page.click("button:has-text('BỎ QUA')", timeout=3000)
                    except:
                        pass
                    try:
                        next_btn = page.locator("button:has-text('CÂU TIẾP THEO'), button:has-text('TIẾP TỤC'), .btn-next")
                        if next_btn.is_visible():
                            next_btn.click(force=True)
                    except:
                        pass
                    continue
            else:
                radios = page.locator("input[type='radio']").all()
                radio_count = len(radios)

                dung_sai_container = page.locator(".true-false, .answer-group, .choice-group").first
                if dung_sai_container.is_visible():
                    dung_sai_count = dung_sai_container.locator("button:has-text('Đúng'), button:has-text('Sai'), label:has-text('Đúng'), label:has-text('Sai')").count()
                else:
                    dung_sai_count = page.locator("button:has-text('Đúng'), button:has-text('Sai'), label:has-text('Đúng'), label:has-text('Sai')").count()

                if radio_count >= 8 or dung_sai_count >= 8:
                    log_msg("✅ [Thông báo] Dạng bài: ĐÚNG SAI", log_queue)
                    q_content = page.evaluate("() => document.querySelector('.question-content-container')?.innerText || document.body.innerText")
                    id_match = re.search(r"#(\d+)", q_content)
                    q_id = id_match.group(1) if id_match else f"truefalse_{i}"

                    results = solve_true_false(q_content)
                    if results == "RETRY":
                        time.sleep(5)
                        results = solve_true_false(q_content)

                    log_question_to_file("question-dung-sai.json", {"id": q_id, "question": q_content, "answers": results})

                    if results:
                        clicked_count = click_true_false(page, results, log_queue)
                        if clicked_count < 4:
                            log_msg(f"⚠️ Chỉ click được {clicked_count}/4 ý, bỏ qua câu này.", log_queue)
                            try:
                                page.click("button:has-text('BỎ QUA')", timeout=3000)
                            except:
                                pass
                            try:
                                next_btn = page.locator("button:has-text('CÂU TIẾP THEO'), button:has-text('TIẾP TỤC'), .btn-next")
                                if next_btn.is_visible():
                                    next_btn.click(force=True)
                            except:
                                pass
                            continue
                        else:
                            log_msg(f"✅ Đã click đủ {clicked_count}/4 ý.", log_queue)
                    else:
                        log_msg("⚠️ AI không trả về kết quả, bỏ qua", log_queue)
                        try:
                            page.click("button:has-text('BỎ QUA')", timeout=3000)
                        except:
                            pass
                        try:
                            next_btn = page.locator("button:has-text('CÂU TIẾP THEO'), button:has-text('TIẾP TỤC'), .btn-next")
                            if next_btn.is_visible():
                                next_btn.click(force=True)
                        except:
                            pass
                        continue
                else:
                    a_label = page.locator("text=/^A[.)]/").first
                    b_label = page.locator("text=/^B[.)]/").first
                    c_label = page.locator("text=/^C[.)]/").first
                    d_label = page.locator("text=/^D[.)]/").first
                    if a_label.is_visible() and b_label.is_visible() and c_label.is_visible() and d_label.is_visible():
                        log_msg("🔘 [Thông báo] Dạng bài: KHOANH ĐÁP ÁN (phát hiện qua nhãn)", log_queue)
                    else:
                        log_msg("🔘 [Thông báo] Dạng bài: KHOANH (fallback)", log_queue)

                    q_id, question, options = get_data_by_scraping(page, log_queue)

                    log_question_to_file("questions.json", {"id": q_id, "question": question, "options": options})

                    ans = solve_question(question, options, is_fill_blank=False)
                    if ans == "RETRY":
                        time.sleep(5)
                        ans = solve_question(question, options, is_fill_blank=False)

                    if not ans:
                        log_msg(f"⏭️ AI không trả lời được. Bỏ qua...", log_queue)
                        try:
                            page.click("button:has-text('BỎ QUA')", timeout=3000)
                        except:
                            pass
                        try:
                            next_btn = page.locator("button:has-text('CÂU TIẾP THEO'), button:has-text('TIẾP TỤC'), .btn-next")
                            if next_btn.is_visible():
                                next_btn.click(force=True)
                        except:
                            pass
                        continue

                    # Click đáp án
                    try:
                        log_msg(f"🖱️ [Câu {i}] Đang click vào đáp án {ans}...", log_queue)
                        clicked = False
                        pattern = re.compile(rf"^{ans}[.)]\s*", re.IGNORECASE)

                        possible_selectors = [
                            ".answer-item",
                            ".choice-item",
                            ".option",
                            "label",
                            "div.options > div",
                            ".list-answer > div",
                            ".answer-wrapper"
                        ]
                        for sel in possible_selectors:
                            elements = page.locator(sel).all()
                            for el in elements:
                                text = el.text_content().strip()
                                if pattern.match(text):
                                    el.click(force=True)
                                    clicked = True
                                    log_msg(f"   ✅ Click vào phần tử chứa text: {text[:50]}", log_queue)
                                    break
                            if clicked:
                                break

                        if not clicked:
                            radio = page.locator(f"input[type='radio'][value='{ans}']").first
                            if radio.is_visible(timeout=1000):
                                radio.click(force=True)
                                clicked = True
                                log_msg(f"   ✅ Click radio value={ans}", log_queue)

                        if not clicked:
                            el = page.get_by_text(re.compile(rf"^{ans}[.)]"), exact=False).first
                            if el.is_visible(timeout=1000):
                                el.click(force=True)
                                clicked = True
                                log_msg(f"   ✅ Click get_by_text (regex)", log_queue)

                        if not clicked:
                            target = page.get_by_text(ans, exact=True).last
                            box = target.bounding_box(timeout=2000)
                            if box:
                                page.mouse.click(box['x'] + box['width']/2, box['y'] + box['height']/2)
                                clicked = True
                                log_msg("   ✅ Click dùng bounding_box (ký tự đơn)", log_queue)

                        if not clicked:
                            raise Exception("Không tìm thấy phần tử đáp án nào để click")

                        log_msg(f"🎯 [Câu {i}] Click chọn {ans} thành công!", log_queue)
                    except Exception as e:
                        log_msg(f"❌ [Câu {i}] Lỗi click: {e}", log_queue)
                        try:
                            page.click("button:has-text('BỎ QUA')", timeout=3000)
                        except:
                            pass
                        try:
                            next_btn = page.locator("button:has-text('CÂU TIẾP THEO'), button:has-text('TIẾP TỤC'), .btn-next")
                            if next_btn.is_visible():
                                next_btn.click(force=True)
                        except:
                            pass
                        continue

            # Xử lý nút TRẢ LỜI và TIẾP THEO
            try:
                time.sleep(1.5)
                log_msg(f"📩 [Câu {i}] Đang bấm 'TRẢ LỜI'...", log_queue)

                confirm_btn = None
                css_selectors = [
                    "button:has-text('TRẢ LỜI')",
                    "button:has-text('Trả lời')",
                    ".btn-answer",
                    "button.primary",
                    "button.btn-submit"
                ]
                for selector in css_selectors:
                    btn = page.locator(selector).first
                    if btn.is_visible(timeout=2000):
                        confirm_btn = btn
                        log_msg(f"   🔍 Tìm thấy nút TRẢ LỜI với CSS: {selector}", log_queue)
                        break

                if not confirm_btn:
                    xpath = "//button[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'trả lời')]"
                    confirm_btn = page.locator(f"xpath={xpath}").first
                    if confirm_btn.is_visible(timeout=2000):
                        log_msg(f"   🔍 Tìm thấy nút TRẢ LỜI với XPath", log_queue)
                    else:
                        confirm_btn = None

                if not confirm_btn:
                    raise Exception("Không tìm thấy nút TRẢ LỜI")

                confirm_btn.wait_for(state="visible", timeout=10000)
                confirm_btn.click(force=True)
                log_msg("   ✅ Đã click nút TRẢ LỜI", log_queue)

                time.sleep(2)

                next_btn = None
                next_css_selectors = [
                    "button:has-text('CÂU TIẾP THEO')",
                    "button:has-text('Tiếp tục')",
                    "button:has-text('TIẾP TỤC')",
                    ".btn-next",
                    "button.next"
                ]
                for selector in next_css_selectors:
                    btn = page.locator(selector).first
                    if btn.is_visible(timeout=2000):
                        next_btn = btn
                        log_msg(f"   🔍 Tìm thấy nút TIẾP THEO với CSS: {selector}", log_queue)
                        break

                if not next_btn:
                    xpath_next = "//button[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'tiếp')]"
                    next_btn = page.locator(f"xpath={xpath_next}").first
                    if next_btn.is_visible(timeout=2000):
                        log_msg(f"   🔍 Tìm thấy nút TIẾP THEO với XPath", log_queue)
                    else:
                        next_btn = None

                if next_btn:
                    next_btn.click(force=True)
                    log_msg("   ✅ Đã click nút TIẾP THEO", log_queue)
                else:
                    log_msg("   ⚠️ Không tìm thấy nút TIẾP THEO, có thể đã hết bài", log_queue)

                log_msg(f"✨ [Câu {i}] Hoàn thành câu.", log_queue)
            except Exception as e:
                log_msg(f"❌ [Lỗi] {e}", log_queue)
                page.screenshot(path=f"debug_cau{i}.png")
                try:
                    page.click("button:has-text('BỎ QUA')", timeout=3000)
                except:
                    pass
                try:
                    next_btn = page.locator("button:has-text('CÂU TIẾP THEO'), button:has-text('TIẾP TỤC'), .btn-next").first
                    if next_btn.is_visible():
                        next_btn.click(force=True)
                except:
                    pass

        log_msg(f"✅ [Bài tập {idx}] Đã xử lý xong {max_questions} câu.", log_queue)

def run_bot(accounts, practice_items, api_keys, log_queue=None, headless=False, stop_event=None):
    """
    accounts: list of (username, password)
    practice_items: list of (url, max_questions)
    api_keys: chuỗi api key
    log_queue: Queue để gửi log về client (có thể None)
    headless: True nếu chạy không giao diện
    stop_event: threading.Event để dừng bot sớm
    """
    from ai_engine import init_engine
    init_engine(api_keys)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)

        for idx, (username, password) in enumerate(accounts, start=1):
            if stop_event and stop_event.is_set():
                log_msg("⏹️ [Hệ thống] Nhận lệnh dừng, kết thúc sớm.", log_queue)
                break

            log_msg(f"\n{'='*50}\n👤 Xử lý tài khoản {idx}/{len(accounts)}: {username}\n{'='*50}", log_queue)
            context = browser.new_context()
            page = context.new_page()

            try:
                process_account(page, username, password, practice_items, api_keys, log_queue, stop_event)
            except Exception as e:
                log_msg(f"❌ Lỗi khi xử lý tài khoản {username}: {e}", log_queue)
            finally:
                context.close()

        browser.close()
        log_msg("🏁 Bot đã dừng.", log_queue)