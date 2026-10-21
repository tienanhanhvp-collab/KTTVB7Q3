"""Ngân hàng: 20 câu; 14 Hàn → Việt và 6 Việt → Hàn.
Chỉ máy chủ giữ trường answer; phía trình duyệt không nhận đáp án.
"""
QUESTIONS = [
    {"id":1,"direction":"ko-vi","prompt":"통장","answer":"Sổ ngân hàng, sổ ghi giao dịch tài khoản","options":["Số tài khoản ngân hàng","Sổ ngân hàng, sổ ghi giao dịch tài khoản","Thẻ rút tiền tại máy ATM","Giấy tờ xác minh danh tính"]},
    {"id":2,"direction":"ko-vi","prompt":"계좌 번호","answer":"Số tài khoản ngân hàng","options":["Số tài khoản ngân hàng","Mật khẩu tài khoản ngân hàng","Mã định danh ngân hàng","Số thẻ ngân hàng"]},
    {"id":3,"direction":"ko-vi","prompt":"현금카드","answer":"Thẻ rút tiền, thẻ ATM","options":["Thẻ tín dụng","Thẻ trả trước","Thẻ rút tiền, thẻ ATM","Thẻ thành viên ngân hàng"]},
    {"id":4,"direction":"ko-vi","prompt":"출금","answer":"Rút tiền khỏi tài khoản","options":["Chuyển khoản ngân hàng","Nhận tiền từ người khác","Nộp tiền vào tài khoản","Rút tiền khỏi tài khoản"]},
    {"id":5,"direction":"ko-vi","prompt":"입금","answer":"Nộp tiền vào tài khoản","options":["Nộp tiền vào tài khoản","Rút tiền khỏi tài khoản","Kiểm tra số dư tài khoản","Đổi ngoại tệ tại ngân hàng"]},
    {"id":6,"direction":"ko-vi","prompt":"계좌 이체","answer":"Chuyển tiền giữa các tài khoản ngân hàng","options":["Gửi tiền mặt tại quầy giao dịch","Chuyển tiền giữa các tài khoản ngân hàng","Thanh toán các khoản phí định kỳ","Rút tiền mặt từ tài khoản"]},
    {"id":7,"direction":"ko-vi","prompt":"송금하다","answer":"Gửi tiền, chuyển tiền cho người nhận","options":["Rút tiền mặt tại ngân hàng","Đổi tiền thành mệnh giá nhỏ","Gửi tiền, chuyển tiền cho người nhận","Trả phí sử dụng dịch vụ ngân hàng"]},
    {"id":8,"direction":"ko-vi","prompt":"동전","answer":"Tiền xu","options":["Tiền giấy","Tiền thừa trả lại","Ngoại tệ","Tiền xu"]},
    {"id":9,"direction":"ko-vi","prompt":"지폐","answer":"Tiền giấy","options":["Tiền giấy","Tiền xu","Tiền gửi ngân hàng","Tiền thừa trả lại"]},
    {"id":10,"direction":"ko-vi","prompt":"잔돈","answer":"Tiền lẻ, tiền thừa trả lại","options":["Tiền tiết kiệm","Tiền lẻ, tiền thừa trả lại","Tiền gửi ngân hàng","Tiền nước ngoài"]},
    {"id":11,"direction":"ko-vi","prompt":"자동 납부","answer":"Tự động thanh toán các khoản phí, hóa đơn","options":["Tự động nhận tiền lãi ngân hàng","Tự động đổi ngoại tệ","Tự động thanh toán các khoản phí, hóa đơn","Tự động gửi tiền tiết kiệm"]},
    {"id":12,"direction":"ko-vi","prompt":"자동이체를 하다","answer":"Thực hiện chuyển khoản tự động theo lịch đã đăng ký","options":["Tự động thay đổi mật khẩu tài khoản","Tự động kiểm tra số dư tài khoản","Tự động đổi tiền sang ngoại tệ","Thực hiện chuyển khoản tự động theo lịch đã đăng ký"]},
    {"id":13,"direction":"ko-vi","prompt":"환전하다","answer":"Đổi ngoại tệ","options":["Đổi ngoại tệ","Đổi tiền thành các mệnh giá nhỏ","Thanh toán phí chuyển khoản","Gửi tiền tiết kiệm"]},
    {"id":14,"direction":"ko-vi","prompt":"수수료를 내다","answer":"Trả phí giao dịch, phí dịch vụ","options":["Trả nợ vay ngân hàng","Trả phí giao dịch, phí dịch vụ","Chi tiền cho sinh hoạt hằng ngày","Chuyển tiền lương vào tài khoản"]},
    {"id":15,"direction":"vi-ko","prompt":"Mật khẩu, mã PIN","answer":"비밀번호","options":["신분증","계좌 번호","비밀번호","잔액 조회"]},
    {"id":16,"direction":"vi-ko","prompt":"Kiểm tra, tra cứu số dư tài khoản","answer":"잔액 조회","options":["계좌 이체","출금","입금","잔액 조회"]},
    {"id":17,"direction":"vi-ko","prompt":"Giấy tờ tùy thân","answer":"신분증","options":["신분증","현금카드","통장","비밀번호"]},
    {"id":18,"direction":"vi-ko","prompt":"Mở sổ ngân hàng","answer":"통장을 개설하다","options":["통장을 정리하다","통장을 개설하다","통장을 해지하다","통장을 확인하다"]},
    {"id":19,"direction":"vi-ko","prompt":"Ghi chép sổ thu chi","answer":"가계부를 쓰다","options":["지출을 줄이다","수수료를 내다","가계부를 쓰다","잔액을 조회하다"]},
    {"id":20,"direction":"vi-ko","prompt":"Chi tiêu, khoản chi","answer":"지출","options":["저축","수입","잔액","지출"]},
]
assert len(QUESTIONS)==20
assert len({x['id'] for x in QUESTIONS})==20
assert sum(x['direction']=='ko-vi' for x in QUESTIONS)==14
assert sum(x['direction']=='vi-ko' for x in QUESTIONS)==6
assert all(len(x['options'])==4 and len(set(x['options']))==4 and x['answer'] in x['options'] for x in QUESTIONS)
