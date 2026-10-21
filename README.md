# VOCABULARY RACE · Chủ đề Ngân hàng (20 câu)

Trò chơi trắc nghiệm tiếng Hàn có 20 câu (14 Hàn → Việt, 6 Việt → Hàn), bám sát bộ từ vựng đã thống nhất. Từng từ vựng được hỏi đúng một lần; bốn lựa chọn/câu. Nội dung đã được chuẩn hóa nghĩa theo ngữ cảnh ngân hàng.

## Cách dùng

### Mở bản chơi thử không cần cài đặt

Mở `Vocabulary_Race_Ngan_Hang_20_DEMO.html` bằng Chrome/Safari/Edge. Bạn có thể làm 20 câu như sinh viên, sai chờ 3 giây, nhưng bản HTML này **chỉ chạy một người trên một thiết bị và không đồng bộ với giáo viên**.

Mở `Giao_Dien_Giao_Vien_Ngan_Hang_DEMO.html` để xem thử bảng xếp hạng đa sắc và việc đổi thứ hạng. Đây cũng chỉ là mô phỏng.

### Chạy ứng dụng nhiều người chơi trên máy tính

Cần Python 3.10+ và kết nối Internet khi cài thư viện.

```bash
python -m pip install -r requirements.txt
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

- **Giáo viên:** `http://localhost:8000/teacher`. Nhấn `Tạo phòng đua mới` và giữ kín liên kết chứa khóa quản lý.
- **Sinh viên:** liên kết và QR được tạo ngay trong phòng giáo viên, có dạng `http://localhost:8000/race/MÃ-PHÒNG` (thay localhost bằng IP LAN khi sinh viên dùng điện thoại cùng Wi-Fi).
- Giáo viên chủ động nhấn **Bắt đầu** sau khi mọi người đã đăng nhập; có thể tạm dừng, kết thúc và xuất bảng kết quả CSV.
- Nhấn **Thi lại** để chơi lại cùng nhóm sinh viên, câu hỏi và đáp án được đảo ngẫu nhiên lần mới.

### Triển khai website công khai trên Render

1. Tải **toàn bộ nội dung của thư mục này**, không phải riêng tệp ZIP, lên một kho GitHub.
2. Vào Render → New → Blueprint, kết nối kho GitHub. File `render.yaml` quy định cách chạy ứng dụng.
3. Chờ trạng thái triển khai thành công. Render mới cấp tên miền thực tế; ví dụ `https://ten-ung-dung.onrender.com/teacher` chỉ là minh họa, **không phải link đã được xuất bản**.
4. Dùng trang giáo viên để tạo phòng, chia sẻ QR/link sinh viên.

**Quan trọng:** Phiên bản phòng học này lưu dữ liệu trong RAM của một tiến trình. Nếu máy chủ ngủ, khởi động lại hoặc cập nhật ứng dụng thì dữ liệu phòng có thể mất; hãy tải CSV sau giờ học. Không triển khai nhiều worker/instance nếu chưa nâng cấp sang cơ sở dữ liệu chung. Thiết kế cho tối đa 60 sinh viên/phòng và 100 phòng trên một tiến trình. Dữ liệu đáp án được máy chủ kiểm tra (trình duyệt học viên không nhận đáp án). Không nên sử dụng làm nền tảng thi cử chính thức có yêu cầu chống gian lận tuyệt đối.

## Luật chơi

- Đúng: +1 bước và chuyển câu.
- Sai: dừng tại câu hiện tại, máy chủ khóa 3 giây rồi được thử lại. Không áp dụng thêm thời gian phạt.
- 20 câu hỏi được đảo ngẫu nhiên cho từng sinh viên; bốn đáp án cũng được đảo.
- Mỗi sinh viên giữ một màu đường đua theo thứ tự tham gia; bảng giáo viên tự thay đổi thứ hạng theo số câu đúng. Nếu bằng số câu, người đạt mốc đó trước đứng trên. Người về đích sớm nhất đứng hạng nhất.
- Đồng hồ dừng khi giáo viên tạm dừng. Link giáo viên có khóa bí mật, chỉ chia sẻ link sinh viên.

## Tệp chính

`questions.py`: 20 câu và đáp án; `main.py`: API, phòng, chấm điểm và khóa 3 giây phía máy chủ; `static/`: giao diện web; `render.yaml`: cấu hình Render; `tests/`: kiểm thử.
