@echo off
chcp 65001 > nul
setlocal

:: ============================================================
::  run.cmd — Chạy Legal Merger (package legal_merger/)
::  Cách dùng: run.cmd <van_ban_goc> <van_ban_sua_doi> [output]
::
::  Ví dụ:
::    run.cmd docs\input\15-ttkdtm.pdf docs\input\30-suadoi-15.pdf
::    run.cmd goc.pdf suadoi.pdf ket_qua.txt
::    run.cmd goc.pdf suadoi.pdf ket_qua.docx --format docx
:: ============================================================

if "%~1"=="" goto :usage
if "%~2"=="" goto :usage

set BASE=%~1
set AMEND=%~2

:: Output mặc định nếu không truyền tham số thứ 3
if "%~3"=="" (
    set OUTPUT=van_ban_hop_nhat.txt
) else (
    set OUTPUT=%~3
)

:: Chuyển vào thư mục chứa run.cmd để đảm bảo đường dẫn tương đối hoạt động
cd /d "%~dp0"

:: Chạy package — truyền thêm các tham số tuỳ chọn từ %4 trở đi
python -m legal_merger "%BASE%" -a "%AMEND%" -o "%OUTPUT%" %4 %5 %6 %7 %8 %9

goto :end

:usage
echo.
echo  Cach dung: run.cmd ^<van_ban_goc^> ^<van_ban_sua_doi^> [output] [tuy_chon]
echo.
echo  Vi du:
echo    run.cmd docs\input\15-ttkdtm.pdf docs\input\30-suadoi-15.pdf
echo    run.cmd goc.pdf suadoi.pdf ket_qua.txt
echo    run.cmd goc.pdf suadoi.pdf ket_qua.docx --format docx --cmp-format xlsx
echo    run.cmd goc.pdf suadoi.pdf ket_qua.txt --no-comparison
echo.
echo  Tuy chon:
echo    --format docx          Xuat van ban hop nhat dang Word
echo    --no-deleted           An cac dieu da bi bai bo
echo    --no-comparison        Khong tao bang so sanh
echo    --cmp-format docx xlsx Dinh dang bang so sanh (mac dinh: ca hai)
echo    --no-clean-pages       Tat xoa so trang/header/footer
echo.

:end
endlocal
