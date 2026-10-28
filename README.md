# TekScope → Excel — demo 0.1

Ứng dụng Windows đọc **measurement thật đang có trên Tektronix MSO64B/MSO66B**, so sánh criteria trong Excel, điền số đo và PASS/FAIL vào chính workbook. Địa chỉ scope do người dùng nhập. Không có database và không có dữ liệu mô phỏng trong luồng GUI/CLI.

## Chạy GUI

Mở `Start_Demo.cmd` trong thư mục này. Cần Python 3.10 trở lên có Tkinter (bộ cài Python Windows thông thường có sẵn); demo dùng thư viện chuẩn, không cần cài pip package hoặc VISA cho kết nối LAN.

1. Trên scope: kết nối LAN, bật Socket Server, chọn protocol **None**, ghi lại port (thường là **4000**). Máy tính phải truy cập được IP/port đó.
2. Tự probe, cấu hình channel, timebase, trigger và các measurement mong muốn trên scope. Đặt threshold, gating và nguồn tín hiệu đúng định nghĩa spec.
3. Trong GUI tiếng Anh, nhập **IP/hostname + port**, bấm **Connect / refresh**. Tool đọc `*IDN?` và danh sách `MEAS1`, `MEAS2`... cùng loại phép đo/channel/đơn vị.
4. Bấm **Open Excel…** để mở file spec hoặc **Load sample** để dùng mẫu. Chọn một dòng spec, chọn measurement trên scope và bấm **Assign to selected row**. Lặp lại cho các dòng cần đo. Không tự ghép dựa vào tên hoặc thứ tự.
5. Bấm **Read & evaluate**. Mặc định tool dừng acquisition và đọc dữ liệu hiện đang có. Chọn **New single capture** để chờ một acquisition mới theo trigger đã cấu hình (timeout 15 giây). Sau đọc, scope ở trạng thái Stop.
6. Mặc định bật **Auto-save results to Excel**: các cột kết quả được cập nhật, PASS xanh / FAIL đỏ; bản workbook trước được giữ trong `backups/`. Có thể tắt tự lưu để xem trước rồi dùng **Save Excel…** để lưu file mới.

Nếu workbook đang mở và Excel khóa file: đóng workbook rồi lưu lại, hoặc dùng tên file mới. GUI phân biệt đã đo và đã lưu, không báo đã lưu khi ghi lỗi. Nếu criteria trong file bị sửa sau khi nạp, cần mở lại và đo lại.

## File specification

File mẫu: `outputs/demo/spec_demo.xlsx`, sheet `Validation`. Các giới hạn chỉ để minh họa phần mềm, **không phải datasheet của linh kiện thật**. Sửa chúng trước khi kết luận trên board.

File mẫu đã có sẵn trong repo. Script `tools/build_demo_workbook.mjs` chỉ dùng để tạo lại mẫu trong môi trường Codex có `@oai/artifact-tool`; không cần chạy script hoặc cài thư viện này để sử dụng demo.

Demo tìm hàng tiêu đề trong 50 dòng đầu, theo các tên cột:

| Cột đầu vào | Cột tool điền |
|---|---|
| Test ID, Interface, Signal, Parameter, Spec Min, Spec Max, Unit | Measured Min, Measured Max, Result, Note, Run ID |

Test ID phải là text duy nhất; cột spec là số hoặc để trống. Để trống một phía nghĩa là không có giới hạn phía đó; số 0 là giới hạn hợp lệ. Demo hỗ trợ .xlsx với cấu trúc cột này, chưa có trình mapping layout tùy ý hoặc criteria bằng công thức Excel.

Tool so sánh measured minimum với Spec Min, measured maximum với Spec Max, bao gồm giá trị đúng bằng giới hạn. Đổi các đơn vị tương thích V/mV/uV, s/ms/us/ns/ps, Hz/kHz/MHz/GHz và baud/kbaud/Mbaud. Không đổi bit/s thành baud nếu không có định nghĩa phù hợp. Chỉ làm tròn khi hiển thị. INCONCLUSIVE nghĩa là chưa có dữ liệu hợp lệ, thiếu mẫu hoặc đơn vị không tương thích; đó không phải FAIL điện.

Chỉ các dòng đã gán mới được điền. Tool giữ nguyên vùng spec và các phần XLSX không liên quan. `Note` ghi nguồn measurement, channel, phạm vi CURRENTACQ và số mẫu. Mỗi run lưu transcript SCPI và snapshot criteria/mapping trong `runs/<run_id>/scope_run.json` để kiểm tra lại; không phải database.

## CLI cho người dùng / agent

Chạy từ thư mục dự án. Thay `<SCOPE_IP>` bằng IP thật:

```text
python -m hwval_demo connect --host <SCOPE_IP> --port 4000
python -m hwval_demo run --host <SCOPE_IP> --workbook outputs/demo/spec_demo.xlsx --map GPIO-01=MEAS1 --map SPI-01=MEAS2 --save
python -m hwval_demo run --host <SCOPE_IP> --workbook outputs/demo/spec_demo.xlsx --map GPIO-01=MEAS1 --single --acquisition-timeout 15 --output result_new.xlsx
```

CLI trả JSON. Không có `--save`/`--output` thì chỉ đọc/đánh giá và lưu log, không sửa workbook. Exit codes: 0 = các dòng được đo đều PASS; 1 = có FAIL; 2 = lỗi thực thi/kết nối/lưu; 3 = có dòng chưa đủ dữ liệu. `connect` trả danh sách phép đo, không chạy acquisition.

## Giới hạn bản demo và kiểm thử

Đây là demo tập trung vào **LAN SCPI → native measurement → Excel**. Chưa có USB/VISA, board console, API server, tải raw waveform hoặc engine decode GPIO/SPI/I²C/UART; những phần đó vẫn nằm trong kế hoạch đầy đủ. Demo dùng phép đo có sẵn trên scope và chưa tự kiểm chứng threshold/gating đúng datasheet. Khi firmware hoặc option không hỗ trợ query, tool báo lỗi thay vì tạo số đo giả.

Hiện chưa thử với scope vật lý vì người dùng sẽ nhập địa chỉ sau. Kiểm thử tự động dùng SCPI server trên loopback để xác nhận framing TCP, thứ tự Stop/Single, timeout, CURRENTACQ, invalid values và toàn bộ đường đọc → so sánh → lưu. Đây là kiểm thử giao thức, không thay thế xác nhận với MSO6B thực tế.

```text
python -m unittest discover -s tests -v
```

Tài liệu lệnh dùng để xây driver: [Tektronix measurement commands](https://tm-devices.readthedocs.io/stable/reference/tm_devices/commands/gen_7n037o_lpdmso/measurement/), [4/5/6 Series programmer manual — socket server](https://download.tek.com/manual/4-5-6-Series-MSO-Programmer_077130522.pdf).
