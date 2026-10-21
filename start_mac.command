#!/bin/bash
cd "$(dirname "$0")" || exit 1
if ! command -v python3 >/dev/null 2>&1; then
 echo "Bạn cần cài Python 3 để chạy Vocabulary Race."
 read -r _
 exit 1
fi
python3 -m pip install -r requirements.txt || exit 1
echo "=================================================="
echo "VOCABULARY RACE — NGÂN HÀNG — 20 CÂU"
echo "Mở trang giáo viên: http://localhost:8000/teacher"
echo "Để điện thoại tham gia, mở trang giáo viên bằng IP LAN máy Mac."
echo "=================================================="
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
