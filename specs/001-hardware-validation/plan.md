# Kế hoạch triển khai Hardware Validation Tool

**Trạng thái:** Bản nháp cho nhóm review. Phần dưới đây ghi công việc cần thực hiện
theo từng interface. Nhóm sẽ hoàn thiện kế hoạch triển khai tổng thể sau khi review
[đặc tả](spec.md).

## Chốt và nghiệm thu từng bài đo

| Bước | Công việc của nhóm | Đầu ra |
|---|---|---|
| 1. Chọn tham số | Trong quá trình phát triển từng interface, xác định các tham số timing và điện áp áp dụng cho board, device và chế độ đang dùng. | Danh mục bài đo cho tổ hợp đó. |
| 2. Thống nhất với EE Test Plan | Đối chiếu từng dòng EE Test Plan với bài trong tool. Hai bên dùng cùng thông số, định nghĩa phép đo, đơn vị, giới hạn và điều kiện áp dụng. | Mapping cho từng bài, được chốt trước khi chạy trên board. |
| 3. Đo tay trên scope | Đóng băng capture và chạy phân tích bằng tool. Kỹ sư đo tay trên chính scope ở cùng capture, kênh, sự kiện và ngưỡng đo. Nếu kiểm tra giá trị tệ nhất, đối chiếu cả sự kiện mà tool chọn. | Giá trị tool, giá trị đo tay và bằng chứng xác định vị trí đo. |
| 4. Review sai lệch | So sánh hai số đo sau khi quy đổi đơn vị. Dùng dung sai nghiệm thu nhóm thống nhất cho bài đó. Đối chiếu cả kết luận theo giới hạn của device. Nếu sai lệch vượt dung sai, kiểm tra nguyên nhân và đo lại. | Kết quả nghiệm thu phép đo của tool, liên kết đến bài và capture đã kiểm tra. |

Danh mục được bổ sung theo tiến độ của từng interface. Mỗi lượt chạy dùng danh mục
đã chốt cho lượt đó. Hồ sơ ghi giới hạn từ specification để đánh giá **board**
và dung sai so với phép đo tay để nghiệm thu **tool**.
