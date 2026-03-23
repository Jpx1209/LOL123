import threading
import queue
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
from bot import run_bot

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
socketio = SocketIO(app, cors_allowed_origins="*")

active_bots = {}  # {session_id: {'thread': Thread, 'stop_event': Event, 'log_queue': Queue, 'log_thread': Thread}}

@socketio.on('connect')
def handle_connect():
    session_id = request.sid
    print(f"Client connected: {session_id}")
    active_bots[session_id] = {
        'thread': None,
        'stop_event': threading.Event(),
        'log_queue': queue.Queue(),
        'log_thread': None
    }

@socketio.on('disconnect')
def handle_disconnect():
    session_id = request.sid
    print(f"Client disconnected: {session_id}")
    if session_id in active_bots:
        bot_data = active_bots[session_id]
        if bot_data['thread'] and bot_data['thread'].is_alive():
            bot_data['stop_event'].set()
            bot_data['thread'].join(timeout=5)
        if bot_data['log_thread'] and bot_data['log_thread'].is_alive():
            bot_data['log_thread'].join(timeout=2)
        del active_bots[session_id]

def bot_worker(session_id, accounts, practice_items, api_keys):
    """Chạy bot và gửi log qua socket"""
    bot_data = active_bots.get(session_id)
    if not bot_data:
        return
    log_queue = bot_data['log_queue']
    stop_event = bot_data['stop_event']

    # Thread riêng để đọc queue và emit log
    def emit_log():
        while not stop_event.is_set() or not log_queue.empty():
            try:
                msg = log_queue.get(timeout=0.5)
                socketio.emit('log', {'message': msg}, room=session_id)
            except queue.Empty:
                continue
        # Dọn queue còn sót
        while not log_queue.empty():
            try:
                msg = log_queue.get_nowait()
                socketio.emit('log', {'message': msg}, room=session_id)
            except queue.Empty:
                break

    log_thread = threading.Thread(target=emit_log, daemon=True)
    log_thread.start()
    bot_data['log_thread'] = log_thread

    # Chạy bot
    try:
        run_bot(accounts, practice_items, api_keys, log_queue, headless=True, stop_event=stop_event)
    except Exception as e:
        socketio.emit('log', {'message': f"❌ Lỗi bot: {e}"}, room=session_id)
    finally:
        stop_event.set()  # Đảm bảo emit_log thoát
        log_thread.join(timeout=5)
        socketio.emit('bot_finished', room=session_id)
        if session_id in active_bots:
            active_bots[session_id]['thread'] = None

@socketio.on('start_bot')
def handle_start_bot(data):
    session_id = request.sid
    bot_data = active_bots.get(session_id)
    if not bot_data:
        emit('error', {'message': 'Session không hợp lệ'})
        return

    if bot_data['thread'] and bot_data['thread'].is_alive():
        emit('error', {'message': 'Bot đang chạy, không thể khởi động lại'})
        return

    # Lấy dữ liệu từ client
    accounts_text = data.get('accounts', '').strip()
    api_keys = data.get('api_keys', '').strip()
    urls_text = data.get('urls', '').strip()
    questions_input = data.get('questions', '').strip()

    # Kiểm tra dữ liệu
    if not accounts_text:
        emit('error', {'message': 'Chưa nhập tài khoản'})
        return
    if not api_keys:
        emit('error', {'message': 'Chưa nhập API keys'})
        return
    if not urls_text:
        emit('error', {'message': 'Chưa nhập link bài tập'})
        return
    if not questions_input:
        emit('error', {'message': 'Chưa nhập số câu'})
        return

    # Parse danh sách tài khoản
    accounts = []
    for line in accounts_text.splitlines():
        line = line.strip()
        if not line:
            continue
        if '|' not in line:
            emit('error', {'message': f'Dòng không đúng định dạng (thiếu "|"): {line}'})
            return
        user, pwd = line.split('|', 1)
        accounts.append((user.strip(), pwd.strip()))

    # Parse link bài tập
    urls = [u.strip() for u in urls_text.splitlines() if u.strip()]
    if not urls:
        emit('error', {'message': 'Không có link bài tập'})
        return

    # Parse số câu
    q_parts = [p.strip() for p in questions_input.split(',')]
    if len(q_parts) == 1:
        try:
            common = int(q_parts[0])
            max_q_list = [common] * len(urls)
        except ValueError:
            emit('error', {'message': 'Số câu không hợp lệ'})
            return
    else:
        if len(q_parts) != len(urls):
            emit('error', {'message': f'Số lượng số câu ({len(q_parts)}) không khớp với số link ({len(urls)})'})
            return
        max_q_list = []
        for p in q_parts:
            try:
                max_q_list.append(int(p))
            except ValueError:
                emit('error', {'message': f'Giá trị "{p}" không hợp lệ'})
                return

    practice_items = list(zip(urls, max_q_list))

    # Xóa queue cũ và reset stop_event
    while not bot_data['log_queue'].empty():
        bot_data['log_queue'].get()
    bot_data['stop_event'].clear()

    # Tạo thread chạy bot_worker
    bot_thread = threading.Thread(
        target=bot_worker,
        args=(session_id, accounts, practice_items, api_keys),
        daemon=True
    )
    bot_thread.start()
    bot_data['thread'] = bot_thread

    emit('bot_started', {'message': 'Bot đã khởi động'})

@socketio.on('stop_bot')
def handle_stop_bot():
    session_id = request.sid
    bot_data = active_bots.get(session_id)
    if not bot_data:
        emit('error', {'message': 'Session không hợp lệ'})
        return
    if bot_data['thread'] and bot_data['thread'].is_alive():
        bot_data['stop_event'].set()
        emit('bot_stopped', {'message': 'Đang yêu cầu dừng bot...'})
    else:
        emit('error', {'message': 'Bot không chạy'})

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)