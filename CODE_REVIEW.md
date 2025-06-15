# Tự Đánh Giá Mã Nguồn (Code Review Self-Check) - Vexere AI Chatbot POC

Tài liệu này nhằm mục đích tự đánh giá mã nguồn của dự án Proof of Concept (POC) Chatbot AI Vexere, tập trung vào các quy ước về code style, chiến lược kiểm thử, và các điểm còn hạn chế cũng như hướng mở rộng tiềm năng, đồng thời so sánh với Kiến trúc Mục tiêu đã được đề ra trong `DESIGN_DOCUMENT.md`.

## 1. Quy ước Code Style

- **Ngôn ngữ chính:** Python

  - **Hướng dẫn chung:** Tuân thủ theo **PEP 8 -- Style Guide for Python Code**.
  - **Định dạng tự động:** Dự án sử dụng định dạng mã tự động từ IDE (tương đương Black/Ruff Formatter), đảm bảo tính nhất quán.
  - **Tên biến/hàm:** `snake_case`.
  - **Tên lớp:** `PascalCase`.
  - **Hằng số:** `ALL_CAPS_SNAKE_CASE`.
  - **Docstrings:** Theo PEP 257, đã áp dụng cho các thành phần chính.
  - **Imports:** Nhóm theo thứ tự: chuẩn, bên thứ ba, cục bộ. Tránh `from module import *`.
  - **Type Hinting:** Theo PEP 484, đã áp dụng rộng rãi.

- **Ngôn ngữ Frontend (HTML, CSS, JavaScript):**
  - **Cấu trúc:** Mã sạch sẽ, CSS trong file riêng. JavaScript thuần, xử lý DOM và gọi API.
  - **Định dạng:** Có thể đã được IDE tự động định dạng.

## 2. Kiểm thử & CI (Testing & Continuous Integration)

### 2.1. Chiến lược Kiểm thử Hiện tại (POC)

- **Kiểm thử Đơn vị/Tích hợp (Backend):**

  - **Framework:** `unittest`.
  - **Vị trí:** `backend/tests/test_ai_agent.py`.
  - **Phạm vi:** Kiểm thử logic của `AIAgentsManager` và `VertexAIAgent` với API Gemini live (yêu cầu ADC).
    - **So sánh với Kiến trúc Mục tiêu:** POC hiện tại thiếu các unit test biệt lập mock LLM, và chưa có contract test giữa các service (vì POC là một khối monolith tương đối).

- **Kiểm thử Thủ công End-to-End:**

  - **Quy trình:** Chạy backend FastAPI, mở `frontend/index.html`.
  - **Phạm vi:** Kiểm tra toàn bộ luồng từ UI -> API -> LLM -> Tool -> Mock API -> UI.

- **Script Kiểm thử Độc lập:**
  - `gemini_api_caller.py` (test API Gemini), `render_mermaid.py` (tạo diagram).

### 2.2. Đề xuất Quy trình CI/CD (Cho Kiến trúc Mục tiêu)

(Như đã mô tả chi tiết trong `DESIGN_DOCUMENT.md` - Mục 5.2, bao gồm quản lý mã nguồn, CI với linting/formatting/tests, CD với các chiến lược an toàn, IaC, và Monitoring & Observability toàn diện.)

## 3. Điểm còn hạn chế & Hướng mở rộng (So sánh POC với Kiến trúc Mục tiêu)

### 3.1. Các Hạn chế Hiện tại của POC

- **Quản lý Trạng thái & Lịch sử Chat:**

  - **POC:** Lưu trữ trong bộ nhớ của server backend (`main.py`).
  - **Hạn chế:** Mất dữ liệu khi server khởi động lại, không thể mở rộng theo chiều ngang.
  - **Kiến trúc Mục tiêu (`DESIGN_DOCUMENT.md`):** Đề xuất `Conversation Management Service` sử dụng Redis cho trạng thái phiên và PostgreSQL/NoSQL cho lịch sử hội thoại bền vững.

- **RAG cho FAQ:**

  - **POC:** Cơ chế retrieval dựa trên keyword matching đơn giản từ file JSON (`faq_data.json`). Đây là một **mô phỏng RAG** cơ bản.
  - **Hạn chế:** Thiếu khả năng tìm kiếm ngữ nghĩa, dễ bỏ sót hoặc trả về kết quả không chính xác.
  - **Kiến trúc Mục tiêu:** Đề xuất `RAG Service` hoàn chỉnh với Vector Database, quy trình embedding, và tìm kiếm tương đồng ngữ nghĩa.

- **Xử lý Lỗi:**

  - **POC:** Xử lý lỗi ở mức cơ bản (chủ yếu là `print` statements).
  - **Hạn chế:** Chưa có cơ chế retry, thông báo lỗi chưa thân thiện/chi tiết.
  - **Kiến trúc Mục tiêu:** Đề xuất Global Error Handlers, logging có cấu trúc, cơ chế retry, circuit breakers.

- **Bảo mật:**

  - **POC:** Chưa triển khai các biện pháp bảo mật nâng cao. Quản lý secrets (API keys) đang dựa vào `config.py`.
  - **Hạn chế:** Thiếu xác thực người dùng, phân quyền API, các biện pháp chống prompt injection.
  - **Kiến trúc Mục tiêu:** Đề xuất xác thực/ủy quyền (OAuth2/OIDC), quản lý secrets chuyên dụng (Vault, KMS), mã hóa dữ liệu, WAF.

- **Modularität và `main.py`:**

  - **POC:** `main.py` đảm nhận nhiều vai trò (API endpoint, điều phối luồng chat, quản lý state, host mock API).
  - **Hạn chế:** Có thể trở nên khó quản lý khi mở rộng.
  - **Kiến trúc Mục tiêu:** Phân tách thành các services/modules nhỏ hơn như `Orchestration Layer`, `Conversation Management Service`, và API Gateway sẽ định tuyến đến các mock/internal API riêng biệt.

- **Khả năng Mở rộng Công cụ (Tool Scalability):**

  - **POC:** Việc đăng ký và quản lý tool thực hiện thủ công trong `vertex_agent.py` (schema) và `main.py` (mapping).
  - **Hạn chế:** Khó quản lý nếu số lượng tool tăng nhiều.
  - **Kiến trúc Mục tiêu:** Đề xuất cơ chế đăng ký và quản lý tool linh hoạt hơn, có thể là một `Tool Execution Service` riêng.

- **Testing Coverage:**

  - **POC:** `test_ai_agent.py` kiểm thử tích hợp với LLM live.
  - **Hạn chế:** Thiếu unit test biệt lập cho từng tool, thiếu mock LLM cho các test nhanh hơn/ổn định hơn.
  - **Kiến trúc Mục tiêu:** Kim tự tháp kiểm thử đầy đủ (Unit, Integration, Contract, E2E).

- **Xử lý Đa phương thức (Image/Audio):**
  - **POC:** Backend đã cập nhật để nhận và chuyển tiếp dữ liệu đa phương thức (base64) tới Gemini. Frontend có UI cơ bản để tải lên.
  - **Hạn chế:** Logic lưu trữ phần đa phương thức trong `current_history` của `main.py` còn đơn giản (chủ yếu là text). UI frontend cho việc hiển thị media trong chat log và xử lý lỗi tải lên chưa hoàn thiện.
  - **Kiến trúc Mục tiêu:** Hỗ trợ đầy đủ việc gửi và nhận dữ liệu đa phương thức, có cơ chế lưu trữ hiệu quả (ví dụ: GCS URI thay vì base64 trong lịch sử dài hạn) và UI/UX tốt hơn.

### 3.2. Hướng Mở rộng và Cải tiến (Phù hợp với Kiến trúc Mục tiêu)

(Phần này về cơ bản là các bước để đưa POC tiến gần hơn đến Kiến trúc Mục tiêu đã mô tả trong `DESIGN_DOCUMENT.md` - Mục 6.4. Các điểm chính bao gồm:)

- Triển khai `Conversation Management Service` với Redis/Database.
- Xây dựng `RAG Service` hoàn chỉnh với Vector DB.
- Nâng cấp hệ thống xử lý lỗi và logging.
- Tích hợp các giải pháp bảo mật và quản lý secrets.
- Refactor `main.py` và xây dựng các service/module chuyên biệt.
- Mở rộng phạm vi và loại hình kiểm thử tự động.
- Hoàn thiện UI/UX và logic xử lý đa phương thức.
- Tích hợp Đa kênh: Mở rộng hỗ trợ cho các kênh giao tiếp khác như Mobile App, Zalo, Facebook Messenger, và Voice Gateway. Điều này sẽ đòi hỏi việc xây dựng các adapter hoặc tích hợp với API của từng nền tảng.
- Tích hợp Vexere API thật.
- Thêm các tính năng như cá nhân hóa, phân tích, dashboard, i18n/l10n.

---

Tài liệu này là một bản tự đánh giá ban đầu và nên được cập nhật thường xuyên khi dự án phát triển.
