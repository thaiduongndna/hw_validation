# Hiến chương dự án Hardware Validation Tool

## Nguyên tắc cốt lõi

### I. Tính đúng đắn của kết quả

Mỗi kết luận phải dựa trên dữ liệu đo hợp lệ và specification áp dụng cho device
cùng điều kiện vận hành. PASS yêu cầu đáp ứng mọi giới hạn áp dụng.
FAIL yêu cầu bằng chứng hợp lệ về vi phạm giới hạn. Khi chưa đủ căn cứ,
phải ghi INCONCLUSIVE cùng lý do. Cả lần chạy chỉ đạt PASS khi mọi bài đo
áp dụng đã hoàn thành và đạt PASS.

### II. Khả năng truy xuất

Mỗi kết quả phải truy được về lần chạy, device, dữ liệu đo, đơn vị, cấu hình,
phương pháp phân tích và tiêu chí thực tế đã sử dụng.
Bằng chứng lưu lại phải đủ để kiểm tra lại kết luận khi specification nguồn thay đổi.

### III. Tính nhất quán giữa các chế độ

Mọi chế độ vận hành phải dùng chung quy tắc phân tích và đánh giá.
Với cùng dữ liệu, cấu hình phân tích và specification, kết quả phải nhất quán.

### IV. Kiểm soát đề xuất của AI

Kỹ sư phải xác nhận dữ liệu và thao tác do AI đề xuất trước khi áp dụng.
Phép tính và kết luận phải do logic xác định, kiểm thử được thực hiện.
Luồng đo đã được cấu hình và xác nhận phải hoạt động khi AI không khả dụng.

### V. Chất lượng và review

Thay đổi phải có bằng chứng kiểm chứng phù hợp và được người review kiểm tra
trước khi tích hợp vào nhánh chính. Thay đổi logic đo hoặc đánh giá phải có
kiểm thử cho kết quả đúng, vi phạm giới hạn và dữ liệu không đủ để kết luận.
Phải ghi rõ phạm vi đã kiểm chứng bằng mô phỏng và trên thiết bị thật.

### VI. Ràng buộc sản phẩm

Ứng dụng phải chạy trên Windows, được phát triển bằng Python và có giao diện
tiếng Anh. Hướng dẫn, thông báo trạng thái và lỗi trên giao diện phải dùng tiếng Anh.

## Phân định tài liệu

Specification phải mô tả hành vi người dùng cần, phạm vi tính năng và tiêu chí
nghiệm thu. Implementation plan phải xác định kiến trúc, thư viện, cách triển khai
và phân công công việc. Các tài liệu này phải tuân thủ constitution.

## Áp dụng trong phát triển

Khi lập kế hoạch và review, phải đối chiếu thay đổi với các nguyên tắc áp dụng
và chỉ ra bằng chứng đáp ứng. Mâu thuẫn phải được giải quyết bằng việc điều chỉnh
thiết kế hoặc sửa đổi constitution trước khi tích hợp.

## Quản trị dự án

Sửa đổi constitution phải ghi rõ lý do, ảnh hưởng và được người duy trì dự án
phê duyệt. Phải cập nhật phiên bản và ngày sửa đổi khi áp dụng.
Tăng MAJOR khi bỏ hoặc thay đổi quy định theo cách không tương thích,
MINOR khi bổ sung hoặc mở rộng quy định, PATCH khi chỉnh cách diễn đạt.

**Phiên bản**: 2.0.0 | **Ngày thông qua**: 2026-11-05 | **Lần sửa đổi gần nhất**: 2026-11-06
