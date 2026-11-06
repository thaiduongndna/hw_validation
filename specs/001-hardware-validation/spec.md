# Feature Specification: Hardware Validation Tool

**Feature Branch**: `main` (nhánh hiện tại, không có hook tạo nhánh)

**Created**: 2026-11-06

**Status**: Draft

**Input**: User description: "Ứng dụng validation phần cứng trên Windows, GUI tiếng Anh.
Tự cấu hình scope, lấy waveform và đo theo specification của device. Hỗ trợ Auto qua
netlist và thư viện script, Manual tự nhập command kích hoạt board. Hiển thị waveform,
bảng kết quả, xuất Excel và ảnh, hỗ trợ EE Test Plan và AI có xác nhận của kỹ sư."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Đo bằng Manual với cấu hình scope tự động (Priority: P1)

Kỹ sư gắn probe, chọn device, interface, specification và mapping kênh. Tool kết nối,
tự cấu hình scope và chuẩn bị trigger. Khi GUI báo sẵn sàng, kỹ sư tự nhập command
kích hoạt board qua console. Tool tự hoàn tất capture, lấy waveform, phân tích
và đánh giá kết quả.

**Why this priority**: Cung cấp luồng đo hoàn chỉnh ngay khi kỹ sư đã có command
cho board và specification, đồng thời xác lập hành vi đo chung cho Auto.

**Independent Test**: Dùng board và scope mục tiêu cùng một specification đã xác nhận,
thực hiện một bài đo bằng command nhập tay và kiểm tra kết quả với dữ liệu tham chiếu.
Luồng này sử dụng được mà không cần netlist hoặc script có sẵn.

**Acceptance Scenarios**:

1. **Given** kết nối hợp lệ và đủ đầu vào, **When** kỹ sư bắt đầu bài đo,
   **Then** tool tự cấu hình scope theo interface và specification, chuẩn bị trigger
   và chỉ báo sẵn sàng sau khi scope đã sẵn sàng nhận sự kiện.
2. **Given** scope đã sẵn sàng, **When** kỹ sư gửi command đến board,
   **Then** console hiển thị command và phản hồi, tool chờ capture hoàn tất rồi
   tự thu waveform, phân tích và hiển thị kết quả.
3. **Given** bài đo đang chờ trigger, **When** hết thời gian chờ hoặc mất kết nối,
   **Then** tool ghi trạng thái và nguyên nhân, bài đo thiếu dữ liệu có kết luận
   INCONCLUSIVE và không dùng dữ liệu từ lần capture trước.
4. **Given** tool chưa có đủ đầu vào để cấu hình phép đo, **When** kỹ sư yêu cầu chạy,
   **Then** GUI chỉ rõ dữ liệu cần bổ sung trước khi thực thi.

### User Story 2 - Chuẩn bị specification theo device (Priority: P1)

Kỹ sư nhập specification từ JSON hoặc tự điền để xác định đúng điều kiện đo,
giới hạn và ngưỡng cần dùng cho device đang kiểm tra.

**Why this priority**: Specification quyết định cấu hình phép đo và căn cứ kết luận.

**Independent Test**: Nhập một bộ tiêu chí mẫu, sửa điều kiện hoạt động và xem
giới hạn, đơn vị, nguồn tham chiếu mà một bài đo sẽ sử dụng.

**Acceptance Scenarios**:

1. **Given** specification có device và điều kiện vận hành rõ ràng,
   **When** kỹ sư chọn specification, **Then** tool hiển thị tiêu chí tương ứng,
   các giới hạn một phía hoặc hai phía và đơn vị.
2. **Given** kỹ sư nhập tay một phép đo, **When** chọn interface và thông số,
   **Then** form hiển thị trường bắt buộc, gồm VIH, VIL hoặc ngưỡng khác khi áp dụng,
   và chỉ rõ trường còn thiếu.
3. **Given** hai nguồn có tiêu chí mâu thuẫn, **When** chúng được nhập cho cùng
   điều kiện, **Then** tool yêu cầu kỹ sư chọn và xác nhận tiêu chí sử dụng.
4. **Given** giới hạn thấp nhất là 100 ns, **When** lần lượt đánh giá các số đo hợp lệ
   120 ns và 80 ns, **Then** kết quả tương ứng là PASS và FAIL.
   Nếu thiếu giới hạn áp dụng, kết quả là INCONCLUSIVE kèm lý do.

### User Story 3 - Kiểm tra waveform và bằng chứng đo (Priority: P1)

Kỹ sư xem waveform trực tiếp trên GUI và dùng bảng kết quả để kiểm tra từng phép đo.

**Why this priority**: Giúp kỹ sư xác minh kết luận và tìm vị trí vi phạm trên tín hiệu.

**Independent Test**: Dùng một lần chạy có waveform và các kết quả biết trước,
chọn từng kết quả và kiểm tra vùng dữ liệu, kênh, mốc đo hiển thị.

**Acceptance Scenarios**:

1. **Given** lần chạy có dữ liệu hợp lệ, **When** xem kết quả,
   **Then** GUI hiển thị waveform cùng thông số, giá trị đo, đơn vị, giới hạn và kết luận.
2. **Given** kết quả được tính từ một sự kiện, **When** chọn hàng tương ứng,
   **Then** đồ thị zoom đến sự kiện đó và đánh dấu các kênh, ngưỡng hoặc mốc thời gian
   được dùng cho phép đo.
3. **Given** một thông số tổng hợp từ nhiều sự kiện, **When** chọn kết quả,
   **Then** GUI định vị sự kiện quyết định kết luận và cho xem bằng chứng của các
   giá trị cực trị được báo cáo.
4. **Given** phép đo thiếu sự kiện hoặc waveform, **When** chọn hàng kết quả,
   **Then** GUI nêu nguyên nhân thiếu bằng chứng và không hiển thị vùng đo giả định.

### User Story 4 - Auto từ netlist và chuỗi lệnh (Priority: P1)

Kỹ sư nhập netlist Cadence Design Entry HDL, chọn device trên diagram và xác nhận
mapping với tín hiệu, kênh scope và chuỗi lệnh. Tool tự điều phối các bài đo.

**Why this priority**: Đáp ứng nhu cầu chạy tự động theo kết nối thực tế của board.

**Independent Test**: Dùng netlist mẫu, script đã xác nhận và specification,
chọn một device và thực hiện lượt đo tự động.

**Acceptance Scenarios**:

1. **Given** netlist hợp lệ, **When** nhập netlist,
   **Then** tool dựng diagram device–net và cho chọn device để xem kết nối liên quan.
2. **Given** device đã chọn, **When** ghép thư viện script và mapping kênh,
   **Then** tool đề xuất các liên kết xác định được, đánh dấu phần còn thiếu
   và cho kỹ sư sửa trước khi xác nhận.
3. **Given** đầu vào đã xác nhận, **When** chạy Auto,
   **Then** tool tự cấu hình scope, chuẩn bị trigger, gửi command board,
   chờ capture, phân tích và ghi kết quả theo chuỗi đã chọn.
4. **Given** script bên thứ ba đúng định dạng hỗ trợ, **When** import,
   **Then** kỹ sư xem được interface, tham số, các bước và điều kiện hoàn tất
   trước khi xác nhận sử dụng. Script thiếu thông tin bắt buộc được báo lỗi rõ ràng.
5. **Given** lượt chạy đang hoạt động, **When** kỹ sư yêu cầu dừng,
   **Then** tool ngừng gửi các bước kế tiếp, lưu kết quả đã hoàn tất và chỉ rõ
   trạng thái bước hiện tại, kể cả khi chưa xác nhận được command trên board đã dừng.

### User Story 5 - Excel report và EE Test Plan (Priority: P1)

Kỹ sư xuất kết quả có ảnh bằng chứng. Nếu có EE Test Plan Excel, kỹ sư dùng tài liệu
đó để nhập tiêu chí và nhận lại bản kết quả theo đúng bài đo.

**Why this priority**: Là đầu ra phục vụ review và lưu hồ sơ validation.

**Independent Test**: Dùng bộ kết quả biết trước và một EE Test Plan mẫu,
xuất báo cáo rồi kiểm tra từng hàng, ảnh và nội dung gốc.

**Acceptance Scenarios**:

1. **Given** có kết quả đo, **When** xuất báo cáo,
   **Then** Excel chứa giá trị, đơn vị, giới hạn, kết luận và tham chiếu đến ảnh
   cùng lần chạy. Bài thiếu ảnh phải có lý do.
2. **Given** EE Test Plan có các bài đo và tiêu chí, **When** nhập tài liệu,
   **Then** kỹ sư xem và xác nhận mapping giữa dòng tài liệu với bài đo.
3. **Given** mapping đã xác nhận, **When** xuất kết quả,
   **Then** tool tạo bản kết quả của EE Test Plan, điền đúng vùng đã chọn,
   bảo toàn tiêu chí và nội dung ngoài vùng kết quả.
4. **Given** specification nguồn được sửa sau lần chạy, **When** người review
   kiểm tra báo cáo cũ, **Then** vẫn xác định được tiêu chí thực tế đã dùng
   và tái lập được phép so sánh.

### User Story 6 - AI hỗ trợ kỹ sư (Priority: P2)

Kỹ sư dùng AI để đọc tài liệu, đề xuất specification, mapping, cấu hình và chuỗi lệnh,
sau đó xác nhận phần sẽ dùng.

**Why this priority**: Giảm nhập liệu và hỗ trợ chuẩn bị bài đo.
P2 xác định thứ tự phát triển, tính năng vẫn thuộc phiên bản này.

**Independent Test**: Cung cấp tài liệu có tiêu chí biết trước, kiểm tra đề xuất,
nguồn tham chiếu và hành vi trước, sau khi kỹ sư xác nhận.

**Acceptance Scenarios**:

1. **Given** tài liệu có tiêu chí, **When** yêu cầu AI trích xuất,
   **Then** tool hiển thị giá trị, đơn vị, điều kiện và vị trí nguồn để kỹ sư kiểm tra.
2. **Given** đề xuất chưa được xác nhận, **When** chuẩn bị lượt chạy,
   **Then** tool không dùng đề xuất đó làm tiêu chí hoặc thao tác được thực thi.
3. **Given** đề xuất đã được chỉnh sửa và xác nhận, **When** chạy phép đo,
   **Then** kết luận do quy tắc đánh giá thực hiện trên dữ liệu đo và tiêu chí đã chốt.
4. **Given** AI không khả dụng, **When** chạy với cấu hình và specification
   đã xác nhận, **Then** luồng đo vẫn hoạt động và GUI báo rõ trạng thái AI.

### Edge Cases

- Scope không đáp ứng yêu cầu về kênh hoặc acquisition phải được báo rõ trước khi chạy
  nếu kiểm tra được. Dữ liệu thu được không đủ chất lượng phải có lý do khi đánh giá.
- Thiếu kênh, clipping, thiếu sự kiện, capture chưa hoàn tất hoặc dữ liệu từ lần chạy cũ
  không được dùng để tạo số đo hợp lệ cho phép đo bị ảnh hưởng.
- Đơn vị không tương thích, thiếu giới hạn hoặc chưa rõ điều kiện áp dụng dẫn đến
  INCONCLUSIVE. Một giới hạn hợp lệ ở một phía vẫn đủ để đánh giá tiêu chí một phía.
- Board mất kết nối hoặc command lỗi phải được ghi lại, không tự động coi đó là
  bằng chứng vi phạm giới hạn điện áp hoặc timing.
- Định dạng netlist, tài liệu hoặc script chưa hỗ trợ phải được báo cùng lý do,
  tránh tạo mapping mặc định không có căn cứ.
- Kỹ sư không được gửi command console cạnh tranh với chuỗi Auto đang điều khiển board.
- Sau khi dừng hoặc lỗi, bài chưa chạy và bài bị gián đoạn phải phân biệt được
  với bài đã hoàn thành.
- Tệp Excel bị khóa hoặc bị sửa sau khi nhập phải được thông báo và cho chọn xuất
  bản mới, tránh ghi đè kết quả hoặc tiêu chí ngoài ý muốn.
- Lỗi lấy ảnh không được thay đổi số đo đã tính. Báo cáo phải thể hiện phần bằng chứng
  còn thiếu và không báo hoàn tất xuất báo cáo khi tệp chưa được ghi thành công.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Tool phải hỗ trợ kỹ sư validation và người review kết quả, tuân thủ
  constitution 2.0.0 về nền tảng, ngôn ngữ, tính đúng đắn và khả năng truy xuất.
- **FR-002**: Phạm vi phải bao gồm GPIO, UART, SPI, QSPI, I2C, I3C, JTAG, MDIO,
  RGMII, NCSI, LTPI và VGA. Với mỗi interface, phải có danh mục phép đo điện áp,
  timing, chế độ và tốc độ hỗ trợ, cùng điều kiện và bằng chứng kiểm chứng.
- **FR-003**: Mỗi lượt chạy phải xác định được device, interface, điều kiện vận hành
  và tập bài đo áp dụng. GUI phải cho biết bài nào được hỗ trợ, chưa hỗ trợ hoặc
  không áp dụng. Loại bài khỏi phạm vi phải có lý do được kỹ sư xác nhận.
- **FR-004**: Tool phải kết nối scope qua Ethernet bằng địa chỉ kỹ sư nhập,
  hiển thị nhận dạng và trạng thái kết nối. Thiết bị mục tiêu ban đầu là
  Tektronix MSO64B và MSO66B.
- **FR-005**: Tool phải cho kỹ sư xác nhận mapping tín hiệu–kênh, tự cấu hình scope
  theo interface, frequency và specification, đồng thời lưu cấu hình thực tế.
  Nếu thiếu đầu vào bắt buộc, phải chỉ rõ trước khi chạy.
- **FR-006**: Tool phải chuẩn bị trigger trước hoạt động cần đo, chờ capture hoàn tất
  rồi lấy waveform. Các kênh trong phép đo liên kênh phải cùng acquisition
  hoặc có bằng chứng đồng bộ tương đương.
- **FR-007**: Manual phải có console board qua UART hoặc TCP, hiển thị command,
  phản hồi và trạng thái kết nối. GUI phải báo scope sẵn sàng trước khi kỹ sư
  gửi command kích hoạt bài đo.
- **FR-008**: Trong Manual, kỹ sư tự gõ và gửi command board. Cấu hình scope,
  capture sau trigger, thu dữ liệu, phân tích và ghi kết quả phải tự động.
  Điều khiển scope được thực hiện qua GUI.
- **FR-009**: Auto phải đọc netlist Cadence Design Entry HDL, dựng diagram kết nối
  device–net, cho chọn device và xác nhận mapping tới tín hiệu, kênh và script.
- **FR-010**: Thư viện script phải phân loại theo interface, hỗ trợ tham số như bus,
  device và timeout, và mô tả các bước command board kết hợp với bước đo.
  Ví dụ command board là `i2cdetect -y 1`.
- **FR-011**: Tool phải import script bên thứ ba theo định dạng chuỗi lệnh được hỗ trợ,
  hiển thị các bước, tham số và thông tin còn thiếu để kỹ sư xác nhận trước khi dùng.
- **FR-012**: Auto phải tự gửi command từ script sau khi scope sẵn sàng, theo dõi
  hoàn tất hoặc timeout từng bước, hiển thị tiến độ và hỗ trợ dừng.
  Cùng dữ liệu, cấu hình phân tích và spec phải cho cùng kết quả ở Auto và Manual.
- **FR-013**: Specification phải nhập được từ JSON, nhập tay, EE Test Plan Excel
  và AI trích xuất tài liệu. Các nguồn phải được kiểm tra và trình bày thống nhất.
- **FR-014**: Mỗi tiêu chí phải xác định thông số, đơn vị, giới hạn áp dụng,
  điều kiện đo và nguồn tham chiếu. Mâu thuẫn phải được kỹ sư giải quyết trước khi dùng.
- **FR-015**: Form nhập tay phải cung cấp trường cần thiết theo phép đo,
  gồm VIH, VIL và các tiêu chí điện áp, timing khi áp dụng, đồng thời chỉ ra
  trường bắt buộc còn thiếu.
- **FR-016**: Phân tích phải dùng ngưỡng và định nghĩa của phép đo trong specification.
  Vai trò của ngưỡng nhận biết logic, ngưỡng xác định thời điểm cạnh và giới hạn
  đánh giá phải được phân biệt. Một đặc tính chưa thể xác định từ waveform
  phải được báo cần phương pháp đo bổ sung.
- **FR-017**: PASS phải yêu cầu đủ dữ liệu hợp lệ và mọi giới hạn áp dụng được đáp ứng.
  FAIL phải có số đo hợp lệ vi phạm ít nhất một giới hạn. Chưa đủ căn cứ phải ghi
  INCONCLUSIVE kèm nguyên nhân. So sánh phải quy đổi đơn vị trước khi đánh giá.
- **FR-018**: Với giới hạn dạng ≥ hoặc ≤, giá trị đúng bằng giới hạn phải đạt.
  Nếu tiêu chí quy định toán tử khác, phải dùng toán tử đã xác nhận.
  Làm tròn để hiển thị phải giữ tách biệt với giá trị dùng để so sánh.
- **FR-019**: Tool phải phân biệt kết luận với trạng thái chưa chạy, đang chạy,
  hoàn thành, lỗi hoặc bị dừng. Tổng thể chỉ PASS khi mọi bài áp dụng hoàn thành
  và PASS. Vi phạm đã có bằng chứng phải được giữ lại kể cả khi lượt chạy dở dang.
- **FR-020**: GUI phải hiển thị waveform và bảng thông số, số đo, đơn vị, giới hạn,
  kết luận và lý do chưa thể kết luận.
- **FR-021**: Chọn một kết quả phải zoom đến bằng chứng của phép đo, đánh dấu mốc
  hoặc ngưỡng áp dụng. Kết quả tổng hợp phải chỉ ra sự kiện quyết định và bằng chứng
  của các cực trị báo cáo.
- **FR-022**: Tool phải lưu đủ bằng chứng để truy từ mỗi kết quả về lần chạy,
  device, tín hiệu, kênh, waveform, cấu hình, phương pháp và specification đã dùng.
- **FR-023**: Mỗi bài đo có dữ liệu phải có ảnh bằng chứng từ tool hoặc scope,
  gắn với đúng acquisition. Trường hợp thiếu ảnh hoặc dữ liệu phải có lý do.
- **FR-024**: Tool phải xuất Excel report chứa các bài đã chạy và chưa hoàn tất,
  số đo, giới hạn, kết luận, lý do và tham chiếu ảnh, dữ liệu liên quan.
- **FR-025**: Với EE Test Plan, tool phải đọc tiêu chí và cho xác nhận mapping bài đo
  tới dòng kết quả, tạo bản kết quả, bảo toàn tiêu chí và nội dung ngoài vùng được chọn.
- **FR-026**: AI phải hỗ trợ đọc spec và đề xuất mapping, cấu hình, chuỗi lệnh.
  Dữ liệu trích xuất phải có nguồn tham chiếu để kỹ sư kiểm tra trước khi xác nhận.
- **FR-027**: Chỉ đề xuất AI đã xác nhận được dùng cho lượt chạy. Phép tính và kết luận
  phải kiểm chứng được độc lập với câu trả lời AI. Mất AI không được chặn luồng đo
  với đầu vào đã xác nhận.
- **FR-028**: Khi lỗi hoặc dừng, tool phải giữ kết quả đã hoàn thành, chỉ rõ bước
  bị ảnh hưởng và không trộn dữ liệu giữa các lần chạy. Thao tác dùng chung thiết bị
  phải được điều phối tránh xung đột.

### Key Entities *(include if feature involves data)*

- **Device và kết nối** — Định danh linh kiện, điều kiện vận hành, interface,
  chân, net và các thiết bị liên quan.
- **Specification** — Bộ tiêu chí theo device và điều kiện, giới hạn, đơn vị,
  ngưỡng, định nghĩa phép đo, nguồn và phiên bản đã xác nhận.
- **Bài đo** — Thông số cần đo, tính áp dụng, mapping tín hiệu–kênh,
  yêu cầu capture và tiêu chí đánh giá.
- **Chuỗi lệnh** — Interface, nguồn thư viện hoặc import, tham số,
  bước kích hoạt board, bước đo và điều kiện hoàn tất.
- **Lần chạy** — Mode, device, tập bài đo, cấu hình, thời điểm, trạng thái,
  command đã gửi và các kết quả liên quan.
- **Bằng chứng và kết quả** — Waveform đồng bộ, ảnh, vùng hoặc sự kiện đo,
  giá trị và đơn vị, giới hạn đã dùng, kết luận và lý do.
- **Mapping EE Test Plan** — Tài liệu nguồn, bài đo, dòng tiêu chí và vùng kết quả
  đã được kỹ sư xác nhận.
- **Đề xuất AI** — Nội dung đề xuất, nguồn tham chiếu, chỉnh sửa của kỹ sư
  và trạng thái xác nhận.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Một kỹ sư hoàn thành ít nhất một lượt đo từ chuẩn bị đến báo cáo
  bằng Manual và một lượt bằng Auto trên từng model scope mục tiêu,
  với kết quả khớp bộ dữ liệu tham chiếu trong dung sai đã công bố cho phép đo.
- **SC-002**: Cả 12 interface có danh mục khả năng đo và ít nhất một tình huống
  nghiệm thu xuyên suốt. Mọi phép đo được công bố hỗ trợ có bằng chứng kiểm chứng
  theo đúng chế độ, tốc độ và điều kiện đã công bố.
- **SC-003**: Trên toàn bộ bộ dữ liệu nghiệm thu, kết luận Auto và Manual trùng nhau
  khi đầu vào phân tích và tiêu chí giống nhau.
- **SC-004**: Mọi trường hợp nghiệm thu thiếu dữ liệu hoặc tiêu chí đều được giải thích,
  và không có PASS khi chưa đủ căn cứ. Các trường hợp vi phạm, đạt và đúng tại biên
  có kết luận đúng với tiêu chí.
- **SC-005**: Với mỗi kết quả có bằng chứng trong bộ nghiệm thu, một lần chọn hàng
  định vị đúng sự kiện hoặc vùng đo và hiển thị các mốc áp dụng.
- **SC-006**: Người review tái lập được phép so sánh của mọi kết quả trong bộ báo cáo
  nghiệm thu từ bằng chứng lưu lại, kể cả khi specification nguồn đã bị sửa.
- **SC-007**: Trên các mẫu netlist và EE Test Plan đã thống nhất, toàn bộ kết nối,
  tiêu chí và vùng kết quả thuộc phạm vi chọn được mapping đúng. Các mục chưa
  mapping được đều được hiển thị để xử lý.
- **SC-008**: Mọi tình huống đề xuất AI chưa xác nhận trong kiểm thử đều bị loại khỏi
  đầu vào thực thi. Luồng đã cấu hình chạy hoàn tất khi AI không khả dụng.
- **SC-009**: Các tình huống timeout, ngắt kết nối, dừng và lỗi xuất báo cáo trong
  kiểm thử đều giữ được kết quả đã hoàn thành và hiển thị trạng thái xử lý đúng.

## Assumptions

- Kỹ sư chịu trách nhiệm gắn probe vật lý và xác nhận mapping. Một lượt chạy điều khiển
  một board và một scope. Mở rộng nhiều thiết bị đồng thời cần đặc tả bổ sung.
- Windows, Python và GUI tiếng Anh là ràng buộc đã chốt trong constitution.
  PyVISA để lấy waveform và OpenAI API cho AI là lựa chọn kỹ thuật do người dùng
  yêu cầu, được ghi nhận để lập plan. Đặc tả này không chọn thêm thư viện hoặc model AI.
- Import script được hiểu là import chuỗi command board kèm các bước đo và tham số.
  Plugin Python thực thi tùy ý chưa thuộc phạm vi đã chốt.
- Cả Auto, Manual, import script và AI đều thuộc phiên bản này.
  Thứ tự ưu tiên user story dùng để sắp xếp triển khai.
- Diagram thể hiện quan hệ device–net phục vụ chọn đối tượng đo.
  Mặc định không yêu cầu tái tạo bố cục schematic gốc từ netlist.
- Waveform hiển thị sau capture và trong lúc xem lại kết quả.
  Streaming liên tục từ scope chưa phải yêu cầu của phiên bản này.
- Một command như i2cdetect là bước tạo hoạt động trên board.
  Khả năng tạo đủ sự kiện cho từng phép đo phải được xác minh trong bài đo tương ứng.
- Danh sách interface xác định phạm vi sản phẩm. Chi tiết chế độ, tốc độ, phép đo,
  ngưỡng, định nghĩa và dung sai nghiệm thu phải được lập theo specification của
  device cùng tài liệu giao tiếp áp dụng. Chỉ công bố khả năng đã có bằng chứng.
- Cần mẫu netlist Cadence Design Entry HDL, EE Test Plan, tài liệu device
  và script bên thứ ba để xác định định dạng hỗ trợ và dữ liệu nghiệm thu
  trước khi hoàn tất thiết kế các chức năng import.
- Mặc định xuất bản kết quả EE Test Plan riêng, kèm ảnh có thể truy cập từ báo cáo.
  Kết quả và bằng chứng lưu bằng tệp, không yêu cầu database.
- Đội dự án có 3 người phát triển và 1 người review. Phân công module và lịch thực hiện
  thuộc implementation plan.
