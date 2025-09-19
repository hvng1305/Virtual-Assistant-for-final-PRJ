# app.py
import re  # Thư viện xử lý biểu thức chính quy
import datetime  # Thư viện xử lý ngày giờ
from urllib.parse import urlparse, quote_plus  # Thư viện phân tích và mã hóa URL
import os  # Thư viện tương tác với hệ điều hành
import webbrowser  # Thư viện mở trình duyệt web
import requests  # Thư viện gửi yêu cầu HTTP cho API thời tiết và tin tức

from selenium import webdriver  # Thư viện điều khiển trình duyệt
from selenium.webdriver.common.keys import Keys  # Thư viện mô phỏng phím
from selenium.webdriver.common.by import By  # Thư viện chọn phần tử HTML
from youtube_search import YoutubeSearch  # Thư viện tìm kiếm YouTube
import wikipedia  # Thư viện truy vấn Wikipedia
from unidecode import unidecode  # Thư viện bỏ dấu tiếng Việt

from flask import Flask, request, jsonify, render_template  # Thư viện Flask cho ứng dụng web
import pickle  # Thư viện lưu/tải mô hình máy học
from typing import Optional  # Thư viện hỗ trợ kiểu dữ liệu tùy chọn

app = Flask(__name__)  # Khởi tạo ứng dụng Flask

# Đường dẫn tới ChromeDriver để điều khiển Chrome
CHROMEDRIVER_PATH = r"C:\Program Files\Google\Chrome\Application\chromedriver.exe"

# Khóa API để gọi dịch vụ thời tiết và tin tức
OPENWEATHER_API_KEY = "70c3ebafb3b5e496625f9c71087fbe02"  # Khóa API thời tiết từ openweathermap.org
NEWS_API_KEY = "9f664582cf1f44d5ad37524207e8f876"  # Khóa API tin tức từ newsapi.org

# Tải mô hình ML để dự đoán ý định
with open("intent_model.pkl", "rb") as f:
    VECTORIZER, INTENT_MODEL = pickle.load(f)  # Tải vectorizer và mô hình
    print("Đã tải intent_model.pkl")  # Thông báo tải thành công

# Dự đoán ý định từ văn bản người dùng
def predict_intent(text: str) -> str:
    text = text.strip().lower()  # Chuẩn hóa văn bản: xóa khoảng trắng, chuyển chữ thường
    X = VECTORIZER.transform([text])  # Chuyển văn bản thành vector
    return INTENT_MODEL.predict(X)[0]  # Dự đoán ý định bằng mô hình

# Các hàm xử lý hành động
def open_application(text: str) -> str:
    text_lower = text.lower()  # Chuyển văn bản thành chữ thường
    if "google" in text_lower or "chrome" in text_lower:  # Kiểm tra yêu cầu mở Chrome
        chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"  # Đường dẫn Chrome
        try:
            os.startfile(chrome_path)  # Mở Chrome
            return "Mở Google Chrome"  # Trả về thông báo thành công
        except Exception as e:
            return f"Lỗi khi mở Chrome: {e}"  # Trả về lỗi nếu thất bại
    if "word" in text_lower:  # Kiểm tra yêu cầu mở Word
        word_path = r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE"  # Đường dẫn Word
        try:
            os.startfile(word_path)  # Mở Word
            return "Mở Microsoft Word"  # Trả về thông báo thành công
        except Exception as e:
            return f"Lỗi khi mở Word: {e}"  # Trả về lỗi nếu thất bại
    if "excel" in text_lower:  # Kiểm tra yêu cầu mở Excel
        excel_path = r"C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE"  # Đường dẫn Excel
        try:
            os.startfile(excel_path)  # Mở Excel
            return "Mở Microsoft Excel"  # Trả về thông báo thành công
        except Exception as e:
            return f"Lỗi khi mở Excel: {e}"  # Trả về lỗi nếu thất bại
    return "Ứng dụng chưa được cài đặt hoặc không biết đường dẫn."  # Thông báo nếu không hỗ trợ ứng dụng

# Làm sạch URL
def sanitize_url(u: str) -> Optional[str]:
    u = u.strip().strip('.,);]\'"')  # Xóa khoảng trắng và ký tự thừa
    if " " in u:  # Kiểm tra URL có chứa khoảng trắng
        return None  # Trả về None nếu không hợp lệ
    pr = urlparse(u)  # Phân tích URL
    if not pr.scheme:  # Nếu thiếu giao thức (http/https)
        u = "https://" + u  # Thêm https
    return u  # Trả về URL đã làm sạch

# Tìm URL trong văn bản
def find_url_in_text(s: str) -> Optional[str]:
    m = re.search(r"(https?://[^\s]+)", s)  # Tìm URL bắt đầu bằng http/https
    if m:
        return sanitize_url(m.group(1))  # Làm sạch và trả về URL
    pattern = r"\b([a-z0-9\-]+\.(?:com|net|org|vn|edu|gov)(?:\.[a-z]{2})?)\b"  # Biểu thức tìm tên miền
    m2 = re.search(pattern, s, re.IGNORECASE)  # Tìm tên miền không phân biệt hoa thường
    if m2:
        return "https://" + m2.group(1).lower()  # Thêm https và trả về
    return None  # Trả về None nếu không tìm thấy

# Mở website
def open_website(text: str) -> Optional[str]:
    reg_ex = re.search(r"mở\s+(.+)", text.lower())  # Tìm cụm từ sau "mở"
    if not reg_ex:
        return None  # Trả về None nếu không tìm thấy
    target = reg_ex.group(1).strip()  # Lấy tên website hoặc truy vấn
    if "youtube" in target:  # Kiểm tra yêu cầu mở YouTube
        q = target.replace("youtube", "").strip()  # Loại bỏ từ "youtube"
        if q:
            return play_song("mở bài hát " + q)  # Tìm và phát bài hát nếu có truy vấn
        webbrowser.open("https://www.youtube.com")  # Mở trang chủ YouTube
        return "Đã mở trang chủ YouTube."  # Thông báo thành công
    if " " in target:  # Nếu có khoảng trắng, tìm kiếm trên Google
        query = quote_plus(target)  # Mã hóa truy vấn
        url = f"https://www.google.com/search?q={query}"  # Tạo URL tìm kiếm
        webbrowser.open(url)  # Mở Google
        return "Mở kết quả tìm kiếm trên Google."  # Thông báo thành công
    if not target.startswith(("http://", "https://")):  # Nếu không có giao thức
        if "." not in target:  # Nếu không có dấu chấm
            url = "https://www." + target  # Thêm www và https
        else:
            url = "https://" + target  # Thêm https
    else:
        url = target  # Sử dụng URL gốc
    url = sanitize_url(url)  # Làm sạch URL
    if not url:
        return "URL không hợp lệ. Hãy thử lại với tên website rõ ràng hơn."  # Thông báo lỗi
    webbrowser.open(url)  # Mở website
    return "Trang web bạn yêu cầu đã được mở."  # Thông báo thành công

# Mở Google và tìm kiếm
def open_google_and_search(text: str) -> str:
    text_lower = text.lower()  # Chuyển thành chữ thường
    if "kiếm" in text_lower:  # Kiểm tra từ khóa tìm kiếm
        search_for = text_lower.split("kiếm", 1)[1].strip()  # Lấy cụm từ sau "kiếm"
    else:
        search_for = ""  # Không có từ khóa tìm kiếm
    if search_for:
        webbrowser.open("https://www.google.com/search?q=" + quote_plus(search_for))  # Mở Google với truy vấn
        return f"Đã tìm kiếm trên Google với từ khóa: {search_for}"  # Thông báo thành công
    webbrowser.open("https://www.google.com")  # Mở trang chủ Google
    return "Mở Google."  # Thông báo thành công

# Phát bài hát
def play_song(text: str) -> str:
    s = text.lower()  # Chuyển thành chữ thường
    s = s.replace("mở bài hát", "").replace("play song", "").replace("play", "")  # Loại bỏ từ khóa
    mysong = s.strip()  # Lấy tên bài hát
    if not mysong:
        return "Hãy nói rõ tên bài hát cần mở."  # Yêu cầu tên bài hát
    try:
        results = YoutubeSearch(mysong, max_results=1).to_dict()  # Tìm bài hát trên YouTube
        if results:
            url = "https://www.youtube.com" + results[0]["url_suffix"]  # Tạo URL bài hát
            webbrowser.open(url)  # Mở bài hát
            return f"Đang mở bài hát: {results[0]['title']}"  # Thông báo bài hát
        else:
            return "Không tìm thấy bài hát bạn yêu cầu."  # Thông báo không tìm thấy
    except Exception as e:
        return f"Lỗi khi tìm bài hát: {e}"  # Thông báo lỗi

# Tra cứu Wikipedia
def ask_wikipedia(text: str) -> str:
    wikipedia.set_lang("vi")  # Đặt ngôn ngữ Wikipedia là tiếng Việt
    q = text.lower()  # Chuyển thành chữ thường
    q = q.replace("wikipedia", "").replace("là gì", "").replace("ai là", "").replace("thông tin về", "").replace("giới thiệu về", "").replace("cho tôi biết về", "").replace("tra cứu", "").replace("wiki", "").replace("hãy cho tôi thông tin về", "").strip()  # Loại bỏ từ khóa
    if not q:
        return "Hãy nói rõ muốn tra cứu gì trên Wikipedia."  # Yêu cầu truy vấn rõ ràng
    try:
        summary = wikipedia.summary(q, sentences=2)  # Lấy tóm tắt 2 câu
        return summary  # Trả về tóm tắt
    except Exception as e:
        return f"Không tìm thấy thông tin về '{q}' trên Wikipedia."  # Thông báo không tìm thấy

# Hỏi thời tiết
def ask_weather(text: str) -> str:
    t = text.lower()  # Chuyển thành chữ thường
    reg_ex = re.search(r"(?:thời tiết|nhiệt độ)(?: hôm nay)?(?: tại| ở)?\s*(.+)?", t)  # Tìm tên thành phố
    if reg_ex and reg_ex.group(1):
        city = reg_ex.group(1).strip()  # Lấy tên thành phố
    else:
        city = "Hà Nội"  # Thành phố mặc định
    city_ascii = unidecode(city)  # Bỏ dấu tiếng Việt
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city_ascii}&appid={OPENWEATHER_API_KEY}&units=metric&lang=vi"  # Tạo URL API
    try:
        response = requests.get(url)  # Gửi yêu cầu API
        data = response.json()  # Lấy dữ liệu JSON
        if data.get("cod") != 200:
            return f"Không tìm thấy thông tin thời tiết cho '{city}'."  # Thông báo không tìm thấy
        weather_desc = data["weather"][0]["description"]  # Mô tả thời tiết
        temp = data["main"]["temp"]  # Nhiệt độ
        feels_like = data["main"]["feels_like"]  # Cảm giác nhiệt độ
        return f"Thời tiết tại {city}: {weather_desc}, nhiệt độ {temp}°C, cảm giác như {feels_like}°C."  # Trả về thông tin
    except Exception as e:
        return f"Lỗi khi lấy thông tin thời tiết: {e}"  # Thông báo lỗi

# Hỏi tin tức
def ask_news(text: str) -> str:
    t = text.lower()  # Chuyển thành chữ thường
    title = "Tin tức mới nhất"  # Tiêu đề mặc định
    query = "Việt Nam"  # Từ khóa tìm kiếm mặc định
    if "hôm nay" in t:
        title = "Tin tức hôm nay"  # Thay tiêu đề nếu có "hôm nay"
    elif "thế giới" in t:
        title = "Tin tức thế giới"  # Thay tiêu đề nếu có "thế giới"
        query = "thế giới"  # Thay từ khóa tìm kiếm
    url = "https://newsapi.org/v2/everything"  # URL API tin tức
    params = {
        "apiKey": NEWS_API_KEY,  # Khóa API
        "q": query,  # Từ khóa tìm kiếm
        "language": "vi",  # Ngôn ngữ tiếng Việt
        "sortBy": "publishedAt",  # Sắp xếp theo thời gian
        "pageSize": 3  # Lấy 3 bài báo
    }
    try:
        response = requests.get(url, params=params)  # Gửi yêu cầu API
        data = response.json()  # Lấy dữ liệu JSON
        if data.get("status") != "ok" or not data.get("articles"):
            return f"{title}:\nHiện chưa có bài báo nào."  # Thông báo không có bài báo
        articles = data["articles"]  # Lấy danh sách bài báo
        news_str = f"{title}:\n"  # Chuẩn bị chuỗi kết quả
        for i, article in enumerate(articles, 1):  # Duyệt qua từng bài báo
            title_news = article.get("title", "Không có tiêu đề")  # Lấy tiêu đề
            desc = article.get("description", "")  # Lấy mô tả
            source = article.get("source", {}).get("name", "")  # Lấy nguồn
            url = article.get("url", "")  # Lấy URL
            news_str += f"\n{i}. {title_news}\n"  # Thêm tiêu đề bài báo
            if desc:
                news_str += f"   Tóm tắt: {desc}\n"  # Thêm mô tả
            if source:
                news_str += f"   Nguồn: {source}\n"  # Thêm nguồn
            if url:
                news_str += f"   Link: {url}\n"  # Thêm URL
        return news_str.strip()  # Trả về chuỗi tin tức
    except Exception as e:
        return f"Lỗi khi lấy tin tức: {e}"  # Thông báo lỗi

# Định tuyến Flask
@app.route("/")  # Trang chủ
def index():
    return render_template("index.html")  # Trả về giao diện HTML

@app.post("/chat")  # API xử lý yêu cầu chat
def chat():
    data = request.get_json(force=True) or {}  # Lấy dữ liệu JSON từ yêu cầu
    user_text = (data.get("text") or "").strip()  # Lấy văn bản người dùng
    if not user_text:
        return jsonify({"reply": "Bạn nói gì mình chưa nghe rõ. Thử nói lại nhé!"})  # Yêu cầu nhập lại nếu rỗng
    intent = predict_intent(user_text)  # Dự đoán ý định
    reply = route_intent(intent, user_text)  # Xử lý ý định
    return jsonify({"reply": reply})  # Trả về phản hồi JSON

# Định tuyến ý định
def route_intent(intent: str, text: str) -> str:
    t = text.strip().lower()  # Chuẩn hóa văn bản
    if intent == "greeting":  # Xử lý lời chào
        return "Xin chào! Mình là trợ lý ảo. Mình có thể giúp gì?"
    if intent == "ask_time":  # Hỏi giờ
        return f"Bây giờ là {datetime.now().strftime('%H:%M:%S')}."
    if intent == "ask_date":  # Hỏi ngày
        return f"Hôm nay là {datetime.now().strftime('%A, %d/%m/%Y')}."
    if intent == "open_google":  # Mở Google
        return open_google_and_search(t)
    if intent == "open_website":  # Mở website
        return open_website(t) or "Không thể mở website. Hãy thử lại."
    if intent == "open_app":  # Mở ứng dụng
        return open_application(t)
    if intent == "play_song":  # Phát bài hát
        return play_song(t)
    if intent == "ask_wiki":  # Tra cứu Wikipedia
        return ask_wikipedia(t)
    if intent == "ask_weather":  # Hỏi thời tiết
        return ask_weather(t)
    if intent == "ask_news":  # Hỏi tin tức
        return ask_news(t)
    return f"Mình đã nhận: “{text}”. Ý định dự đoán: {intent}. Hiện hỗ trợ chào hỏi, hỏi giờ/ngày, mở Google/website/ứng dụng, chơi nhạc, tra cứu Wikipedia, thời tiết, tin tức."  # Phản hồi mặc định

# Chạy ứng dụng Flask
if __name__ == "__main__":
    print("Khởi động Flask app tại http://127.0.0.1:5000")  # Thông báo khởi động
    app.run(debug=True, host="127.0.0.1", port=5000)  # Chạy server Flask