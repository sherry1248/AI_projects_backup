# IoT 기반 재고 관리 시스템

이 프로젝트는 Flask + SQLite 기반의 재고 관리 웹 애플리케이션입니다. 최종 실행 파일은 `app.py`이며, `project.py`는 기존 참고용 코드로만 남겨두었고 최종 실행에는 사용하지 않습니다.

사용자는 웹 브라우저로 로그인한 뒤 상품 등록, 입고, 출고, 재고 조회, 부족 알림, 입출고 이력을 확인할 수 있습니다. QR/바코드 이미지를 업로드하면 `scanner.py`가 상품 ID를 추출하고, 그 값을 입출고 처리 화면에 연결합니다.

## 1. 전체 실행 흐름

1. `app.py`가 Flask 서버를 실행합니다.
2. 요청이 들어오면 `app.py`의 `before_request`에서 `inventory.ensure_database()`를 호출해 DB를 준비합니다.
3. 로그인은 `/login` 라우트에서 처리하고, 성공 시 세션에 `username`과 `role`을 저장합니다.
4. 상품 등록, 재고 증감, 조회, 알림 확인은 `inventory.py`의 함수가 담당합니다.
5. 실제 SQLite 생성, 테이블 생성, CRUD는 `database.py`가 담당합니다.
6. QR/바코드 이미지 인식은 `scanner.py`가 담당합니다.
7. 화면 구성은 `templates/`와 `static/`이 담당합니다.

### 파일 역할 요약

| 파일           | 역할                                           |
| -------------- | ---------------------------------------------- |
| `app.py`       | Flask 서버 실행, 라우트 처리, 로그인/권한 제어 |
| `database.py`  | SQLite DB 생성, 테이블 정의, CRUD, 알림 동기화 |
| `inventory.py` | 상품 등록, 입고/출고, 조회, 대시보드 집계      |
| `scanner.py`   | QR/바코드 이미지 인식                          |
| `project.py`   | 참고용 기존 코드, 최종 실행에는 사용하지 않음  |
| `templates/`   | 웹 화면 템플릿                                 |
| `static/`      | CSS 등 정적 파일                               |

## 2. DB 구조 설명

DB는 `database.py`에서 `inventory.db`로 생성됩니다. 핵심 테이블은 다음과 같습니다.

### User

- 역할: 사용자 로그인 정보 저장
- 주요 컬럼:
  - `username`: 로그인 ID, PK
  - `password_hash`: 비밀번호 해시
  - `role`: `admin` 또는 `staff`

### Product

- 역할: 상품 기본 정보 저장
- 주요 컬럼:
  - `product_id`: 상품 코드, PK
  - `name`: 상품명
  - `min_quantity`: 최소 재고 기준

### Inventory

- 역할: 현재 재고 수량 저장
- 주요 컬럼:
  - `product_id`: 상품 코드, PK이자 FK
  - `quantity`: 현재 수량

### StockLog

- 역할: 입고/출고 이력 저장
- 주요 컬럼:
  - `log_id`: 이력 번호, PK
  - `product_id`: 어떤 상품인지
  - `change_type`: `IN` 또는 `OUT`
  - `quantity`: 변경 수량
  - `username`: 누가 처리했는지
  - `created_at`: 처리 시각

### Alert

- 역할: 재고 부족 알림 저장
- 주요 컬럼:
  - `alert_id`: 알림 번호, PK
  - `product_id`: 부족 상태인 상품
  - `message`: 부족 알림 메시지
  - `created_at`: 생성 시각

### 테이블 연결 관계

- `Product`가 기준 상품 정보를 담고 있습니다.
- `Inventory`는 각 상품의 현재 수량을 1:1로 저장합니다.
- `StockLog`는 재고가 변할 때마다 누적 기록을 남깁니다.
- `Alert`는 현재 재고가 최소 재고보다 낮을 때 생성됩니다.
- `User`는 로그인 계정과 권한을 관리합니다.

## 3. 기능별 작동 방식

### 로그인

- 처리 라우트: `/login` in `app.py`
- 사용 함수:
  - `database.get_user(username)`
  - `werkzeug.security.check_password_hash()`
- 동작 방식:
  - 사용자가 아이디와 비밀번호를 입력하면 `get_user()`로 `User` 테이블을 조회합니다.
  - 비밀번호는 평문 비교가 아니라 해시 검증으로 처리합니다.
  - 로그인 성공 시 `session["username"]`과 `session["role"]`을 저장합니다.
  - `role_required("admin")`가 적용된 `/products` 라우트는 관리자만 접근할 수 있습니다.

### 상품 등록

- 처리 라우트: `/products` in `app.py`
- 사용 함수:
  - `inventory.register_product()`
  - `database.upsert_product()`
  - `database.sync_low_stock_alerts()`
- 동작 방식:
  - 사용자가 `product_id`, `name`, `min_quantity`를 입력합니다.
  - `register_product()`가 입력값을 검증한 뒤 `upsert_product()`를 호출합니다.
  - `Product` 테이블에는 상품 정보가 저장 또는 갱신됩니다.
  - 해당 상품이 없으면 `Inventory` 테이블에 수량 0 행이 생성됩니다.
  - 이후 `sync_low_stock_alerts()`로 부족 알림을 다시 계산합니다.

### 입고 처리

- 처리 라우트: `/inventory` 또는 `/api/scan` in `app.py`
- 사용 함수:
  - `inventory.adjust_stock()`
  - `database.get_product()`
  - `database.get_inventory_item()`
  - `database.set_inventory_quantity()`
  - `database.add_stock_log()`
  - `database.sync_low_stock_alerts()`
- 동작 방식:
  - 사용자가 상품 코드와 수량을 입력합니다.
  - QR/바코드 이미지가 있으면 `scanner.scan_product_id_from_bytes()`로 `product_id`를 추출합니다.
  - `adjust_stock()`가 상품 존재 여부와 수량 유효성을 확인합니다.
  - 입고면 현재 수량에 더한 뒤 `Inventory.quantity`를 갱신합니다.
  - `StockLog`에 `change_type = IN`으로 이력을 남깁니다.
  - 재고 갱신 후 `Alert`를 다시 동기화합니다.

### 출고 처리

- 처리 라우트: `/inventory` 또는 `/api/scan` in `app.py`
- 사용 함수:
  - `inventory.adjust_stock()`
  - `database.get_product()`
  - `database.get_inventory_item()`
  - `database.set_inventory_quantity()`
  - `database.add_stock_log()`
  - `database.sync_low_stock_alerts()`
- 동작 방식:
  - 사용자가 상품 코드와 출고 수량을 입력합니다.
  - `adjust_stock()`가 현재 재고보다 많은 출고를 방지합니다.
  - 가능하면 `Inventory.quantity`를 감소시킵니다.
  - `StockLog`에 `change_type = OUT`으로 기록합니다.
  - 갱신 후 `sync_low_stock_alerts()`로 부족 상태를 다시 계산합니다.

### 재고 조회

- 처리 라우트: `/inventory`, `/api/inventory`, `/`, `/logs`, `/alerts`
- 사용 함수:
  - `inventory.get_inventory_rows()`
  - `database.list_inventory()`
  - `inventory.get_dashboard_counts()`
- 동작 방식:
  - `list_inventory()`가 `Product`와 `Inventory`를 조인해서 현재 재고 목록을 읽습니다.
  - 웹 화면에는 상품명, 현재 수량, 최소 재고 기준을 함께 보여줍니다.
  - 대시보드에서는 상품 수, 부족 상품 수, 이력 수, 알림 수를 요약합니다.

### 부족 알림

- 사용 함수:
  - `database.list_low_stock_products()`
  - `database.sync_low_stock_alerts()`
  - `database.list_alerts()`
- 동작 방식:
  - `Inventory.quantity < Product.min_quantity`이면 부족 상태로 판단합니다.
  - `sync_low_stock_alerts()`가 현재 부족한 상품을 다시 계산합니다.
  - 부족한 상품은 `Alert` 테이블에 메시지로 저장됩니다.
  - 입고 후 수량이 기준 이상이 되면 `Alert`를 다시 동기화해서 해제 상태가 되도록 맞춥니다.

### QR/바코드 인식

- 처리 위치: `scanner.py`
- 사용 함수:
  - `scan_product_id_from_bytes()`
  - `scan_product_id_from_image()`
  - `scan_product_id_from_file()`
- 동작 방식:
  - 사용자가 이미지 파일을 업로드하면 바이트 데이터를 읽습니다.
  - `OpenCV`와 `pyzbar`가 설치되어 있으면 QR/바코드를 디코딩합니다.
  - 추출된 값은 `product_id`로 사용되고, 입고/출고 폼에 연결됩니다.

## 4. 실행 방법

### 1) 가상환경 활성화

Windows PowerShell 예시:

```powershell
.venv\Scripts\Activate.ps1
```

cmd 예시:

```bat
.venv\Scripts\activate.bat
```

### 2) 패키지 설치

필수 패키지:

```bash
pip install Flask
```

선택 패키지 QR/바코드 인식용:

```bash
pip install opencv-python pyzbar numpy
```

### 3) 서버 실행

```bash
python app.py
```

### 4) 접속 URL

- 로컬 PC: `http://127.0.0.1:5000`
- 같은 Wi-Fi 모바일 접속: `http://PC_IP:5000`, PC_IP는 개인 집 IP 적으면 된다.

서버는 `app.py`에서 `host="0.0.0.0"`, `port=5000`으로 실행되므로 같은 네트워크 장치에서 접근할 수 있습니다.

### 5) 기본 로그인 계정

| 계정  | 비밀번호 | 권한      |
| ----- | -------- | --------- |
| admin | admin123 | 관리자    |
| staff | staff123 | 일반 직원 |

## 5. 테스트 방법

1. `admin` 계정으로 로그인합니다.
2. 상품을 등록합니다.
3. 입고 처리를 수행하고 `Inventory` 수량 증가를 확인합니다.
4. 출고 처리를 수행하고 `Inventory` 수량 감소를 확인합니다.
5. 재고 조회 화면에서 상품명, 수량, 최소 재고 기준이 보이는지 확인합니다.
6. 최소 재고 이하 상품이 있으면 `Alert`가 생성되는지 확인합니다.
7. 입출고 이력 화면에서 `StockLog` 기록이 남는지 확인합니다.
8. `staff` 계정으로 다시 로그인한 뒤 상품 등록 메뉴가 제한되는지 확인합니다.
9. 모바일 브라우저에서 `http://PC_IP:5000` 접속이 되는지 확인합니다.

## 6. 발표용 1분 요약

이 프로젝트는 `app.py`를 통해 Flask 서버가 실행되고, SQLite 데이터는 `database.py`에서 관리합니다. 사용자가 로그인하면 `session`과 `role`을 기준으로 권한이 나뉘며, `admin`은 상품 등록까지 가능하고 `staff`는 입고, 출고, 조회 중심으로 사용합니다. 상품 등록은 `inventory.py`의 `register_product()`가 처리하고, 입고와 출고는 `adjust_stock()`가 `Inventory` 수량을 갱신한 뒤 `StockLog`에 이력을 남깁니다. 현재 재고가 `Product.min_quantity` 이하가 되면 `Alert` 테이블에 부족 알림이 생성되며, QR/바코드 인식은 `scanner.py`에서 담당합니다. `project.py`는 기존 참고용 코드이고, 실제 최종 실행은 반드시 `app.py` 기준으로 동작합니다.

## 7. 제출용 핵심 문장

- 최종 실행 파일은 `app.py`입니다.
- DB는 `database.py`에서 생성 및 관리합니다.
- 입고/출고 로직은 `inventory.py`에서 처리합니다.
- QR/바코드 인식은 `scanner.py`에서 처리합니다.
- `project.py`는 참고용이며 최종 실행 파일이 아닙니다.
