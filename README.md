# Hardware Validation Tool

Ứng dụng validation phần cứng trên Windows. Dự án đang ở giai đoạn rà soát
đặc tả với Spec Kit. Nhóm gồm 3 người phát triển và 1 người review.

## Tài liệu cần review

- [Constitution 2.0.0](.specify/memory/constitution.md)
- [Đặc tả tổng thể — Draft](specs/001-hardware-validation/spec.md)
- [Checklist chất lượng](specs/001-hardware-validation/checklists/requirements.md)
- [Plan nháp — chốt tham số và nghiệm thu bằng phép đo tay](specs/001-hardware-validation/plan.md)

Nhóm chốt từng bài đo theo tiến độ triển khai interface, thống nhất tham số giữa
EE Test Plan và tool, rồi đối chiếu với kết quả đo tay trên scope.
Cần mẫu netlist Cadence Design Entry HDL, EE Test Plan, specification device
và script import để hoàn thiện các đầu vào và điều kiện nghiệm thu.

## Review bằng Spec Kit

1. Clone repo hoặc cập nhật từ `main`, rồi mở dự án trong Codex.
2. Tạo nhánh riêng cho mỗi người, ví dụ `codex/clarify-duong`.
3. Chạy đoạn PowerShell sau từ thư mục gốc repo để chọn đặc tả hiện tại.

```powershell
$featureState = '{"feature_directory":"specs/001-hardware-validation"}'
[IO.File]::WriteAllText(
    (Join-Path (Get-Location).Path '.specify/feature.json'),
    $featureState,
    [Text.UTF8Encoding]::new($false)
)
& ./.specify/scripts/powershell/check-prerequisites.ps1 -Json -PathsOnly
```

Tệp chọn feature là trạng thái riêng của từng máy và được Git bỏ qua.
Các skill dùng cho Codex đã nằm trong `.agents/skills`.

4. Gửi `$speckit-clarify` trong chat Codex và trả lời các câu hỏi.
5. Review thay đổi trong spec và checklist, commit rồi mở pull request.
   Người review đối chiếu câu trả lời giữa các nhánh và thống nhất nội dung
   trước khi tích hợp, đặc biệt với các quyết định mâu thuẫn.
6. Khi cả nhóm đã chốt đặc tả và cập nhật checklist, tiếp tục `$speckit-plan`.

Các ưu tiên trong user story xác định thứ tự phát triển. Phạm vi và tiêu chí
nghiệm thu cuối cùng được chốt qua quá trình review đặc tả.
