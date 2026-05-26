
===============================
# BRAINSTORM - PHÂN TÍCH YÊU CẦU
===============================


## Step 1: codebase (LOcal machine)
    - VS CODE +  Claude Code
        => Cập nhật git và push Github

## Step 2: Vào Github
    - Download code (*.zip)

## Step 3: Upload codebase (*.zip) lên Claude.ai
    - Nghiên cứu codebase(file *.zip)
    - Brainstorm (lên ý tưởng - Phân tích yêu cầu)          

=> Claude.ai viết kế hoạch bổ sung code cho chức năng nào đó.

### (Người): => Gửi cho tôi bản kế hoạch vào file PLAN-<tên chức năng>.md
    - Ví dụ: PLAN-bo_sung_chuc_nang_report.md   (Claude Code thực hiện)

    - Doanload về local machine

## Step 4:
### VS Côde + Claude Code

    - Nghiên cứu codebase và kế hoạch bổ sung chức năng trong @PLAN-bo_sung_chuc_nang_report.md nếu nội dung trong kế hoạch chưa tối ưu và chưa đúng với codebase thì chỉnh sửa lại cho đúng và cập nhật vào file @PLAN-bo_sung_chuc_nang_report.md

## Step 5:
### Claude.ai
    - Upload lên Claude.ai
        + codebase (*.zip)
        + PLAN-bo_sung_chuc_nang_report.md

    - Đây là bản kế hoạch do Claude Code rà soát, cập nhật. Nghiên cứu codebase và bản kế hoạch này để đề xuất phương án tối ưu nhất.

    - Gửi kết quả review và đề xuất của bạn cho tôi vào file REVIEW-v1-PLAN-bo_sung_chuc_nang_report.md

    Đây là bản kế hoạch đã được cập nhật theo review v1 của bạn
                                                            REVIEW-v2-PLAN-bo_sung_chuc_nang_report.md

## Step 6
### VS Code + Claude Code
    - Download REVIEW-v1-PLAN-bo_sung_chuc_nang_report.md
    
    - Nghiên cứu kế hoạch trong file @PLAN-bo_sung_chuc_nang_report.md và kết quả review trong @REVIEW-v1-PLAN-bo_sung_chuc_nang_report.md nếu nội dung review nào là tối ưu và đúng với codebase thì cập nhật nôi dung đó vào kế hoạch trong file @PLAN-bo_sung_chuc_nang_report.md.

    < Lặp Step 5 - Step 6 cho đến khi có bản PLAN tối ưu nhất có thể thực thi - Do Claude.ai xác nhận >
====================================================================================
### Local Machie
==============
HR-management/
   src
   data
   UPGRADE
       bo_sung_chuc_nang_report
           - PLAN-bo_sung_chuc_nang_report.md   (nội dung đã được cập nhật sau v3)         
           - REVIEW-v1-PLAN-bo_sung_chuc_nang_report.md
           - REVIEW-v2-PLAN-bo_sung_chuc_nang_report.md
           - REVIEW-v3-PLAN-bo_sung_chuc_nang_report.md
====================================================================================           

## Step 7:
### VS Code + Claude Code
    - Tạo nhánh <tên nhánh> (ví dụ: bo_sung_report) trên git và github đồng thời đặt bo_sung_report làm nhánh mặc định
    => Github:  branch  - main
                        - bo_sung_report (mặc định - default)

## Step 8:
### VS Code + Claude Code
    Sau khi test chức năng mới thành công (UAT)
    - Cập nhật git và push github

    - Căn cứ codebase và kế hoạch nâng cấp trong @PLAN-bo_sung_chuc_nang_report.md hãy viết tài liệu hướng dẫn cài đặt và triển khai lưu vào file <đường dẫn/>README-<Tên chức năng>.md (ví dụ: report/README-report.md)

    - Căn cứ codebase và kế hoạch nâng cấp trong @PLAN-bo_sung_chuc_nang_report.md hãy viết tài liệu thiết kế chi tiết để tôi sử dụng trong đào tạo và chuyển giao công nghệ lưu vào file  <đường dẫn/>DESIGN.md (ví dụ: report/DESIGN.md)