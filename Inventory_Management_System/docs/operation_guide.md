# 운영 및 작동 설명서

이 문서는 교수님 질문에 대비해 코드 기준으로 동작 흐름을 정리한 상세 설명서입니다. 최종 실행은 `app.py`를 기준으로 하며, `project.py`는 기존 참고용 코드일 뿐 실행 엔트리포인트가 아닙니다.

## 1. 시스템 구성

### 실행 경로

1. `app.py`가 Flask 서버를 띄웁니다.
2. 요청마다 `initialize_database()`가 호출되면 `inventory.ensure_database()`가 실행됩니다.
3. `inventory.ensure_database()`는 `database.init_db()`를 호출합니다.
4. `database.init_db()`가 SQLite 파일과 테이블을 준비합니다.
5. 이후 라우트는 로그인 세션과 역할에 따라 기능을 제공합니다.

### 모듈 책임

- `app.py`: 웹 라우트, 세션, 로그인, 권한 검사, 화면 렌더링
- `database.py`: SQLite 연결, 테이블 생성, 기본 사용자 생성, CRUD, 알림 동기화
- `inventory.py`: 상품 등록, 재고 증감, 조회 집계, 부족 알림 판단
- `scanner.py`: QR/바코드 디코딩
- `templates/`: HTML 화면
- `static/`: CSS

## 2. 데이터베이스 구조

### User

- `username`: 로그인 ID
- `password_hash`: 비밀번호 해시
- `role`: `admin` 또는 `staff`

이 테이블은 로그인 인증과 권한 분리에 사용됩니다. `app.py`의 `/login` 라우트에서 `database.get_user()`로 조회합니다.

### Product

- `product_id`: 상품 코드
- `name`: 상품명
- `min_quantity`: 최소 재고 기준

상품 기본 정보의 기준 테이블입니다. 상품 등록 시 `inventory.register_product()`가 `database.upsert_product()`를 호출하여 반영합니다.

### Inventory

- `product_id`: 상품 코드
- `quantity`: 현재 재고 수량

현재 물리 재고를 의미합니다. 입고와 출고가 발생할 때 `database.set_inventory_quantity()`로 갱신합니다.

### StockLog

- `log_id`: 이력 번호
- `product_id`: 대상 상품
- `change_type`: `IN` 또는 `OUT`
- `quantity`: 변화량
- `username`: 처리 사용자
- `created_at`: 처리 시각

입출고 이력을 남기는 감사 로그입니다. `inventory.adjust_stock()`가 성공하면 `database.add_stock_log()`로 기록합니다.

### Alert

- `alert_id`: 알림 번호
- `product_id`: 부족 상품
- `message`: 부족 알림 메시지
- `created_at`: 생성 시각

재고가 기준 이하일 때 표시되는 알림 테이블입니다. `database.sync_low_stock_alerts()`가 현재 상태를 다시 계산해 갱신합니다.

## 3. 기능별 동작

### 로그인

- 라우트: `/login`
- 함수: `login()`
- 관련 함수: `database.get_user()`, `check_password_hash()`

사용자가 아이디와 비밀번호를 입력하면 `User` 테이블에서 계정을 조회하고 해시 비밀번호를 검증합니다. 로그인 성공 시 세션에 `username`과 `role`을 저장합니다.

권한 제어는 `role_required("admin")`로 처리합니다. 따라서 `/products`는 관리자만 접근할 수 있습니다.

### 상품 등록

- 라우트: `/products`
- 함수: `products()`
- 관련 함수: `inventory.register_product()`, `database.upsert_product()`, `database.sync_low_stock_alerts()`

사용자가 `product_id`, `name`, `min_quantity`를 입력하면 `register_product()`가 값을 검증합니다. 이후 `Product` 테이블을 갱신하고, `Inventory`에 해당 상품 행이 없으면 수량 0으로 생성합니다. 마지막으로 부족 알림을 다시 계산합니다.

### 입고 처리

- 라우트: `/inventory`, `/api/scan`
- 함수: `inventory()`와 `api_scan()`
- 관련 함수: `inventory.adjust_stock()`, `database.get_product()`, `database.get_inventory_item()`, `database.set_inventory_quantity()`, `database.add_stock_log()`, `database.sync_low_stock_alerts()`

입고는 `action = in`으로 처리됩니다. `adjust_stock()`는 상품 존재 여부와 수량 유효성을 확인한 뒤 현재 재고에 수량을 더합니다. 재고 갱신 후 `StockLog`에 `IN` 로그를 남기고, 부족 알림을 다시 계산합니다.

### 출고 처리

- 라우트: `/inventory`, `/api/scan`
- 함수: `inventory()`와 `api_scan()`
- 관련 함수: `inventory.adjust_stock()`, `database.get_product()`, `database.get_inventory_item()`, `database.set_inventory_quantity()`, `database.add_stock_log()`, `database.sync_low_stock_alerts()`

출고는 `action = out`으로 처리됩니다. 현재 재고보다 많은 수량은 출고할 수 없게 검증합니다. 성공하면 `Inventory` 수량을 줄이고 `StockLog`에 `OUT` 로그를 저장합니다. 이후 부족 알림을 다시 동기화합니다.

### 재고 조회

- 라우트: `/inventory`, `/api/inventory`, `/`
- 관련 함수: `inventory.get_inventory_rows()`, `database.list_inventory()`, `inventory.get_dashboard_counts()`

재고 조회는 `Product`와 `Inventory`를 조인해서 현재 수량과 최소 기준을 함께 보여줍니다. 메인 대시보드에서는 상품 수, 부족 상품 수, 로그 수, 알림 수를 요약해서 보여줍니다.

### 부족 알림

- 관련 함수: `database.list_low_stock_products()`, `database.sync_low_stock_alerts()`, `database.list_alerts()`

재고 수량이 최소 재고 이하가 되면 부족 상태로 판단합니다. `sync_low_stock_alerts()`는 현재 부족한 상품을 다시 조회한 뒤 `Alert`를 전체 재생성합니다. 입고 후 기준 이상이 되면 더 이상 부족 상품에 포함되지 않기 때문에 알림도 사라집니다.

### QR/바코드 인식

- 파일: `scanner.py`
- 함수: `scan_product_id_from_bytes()`, `scan_product_id_from_image()`, `scan_product_id_from_file()`

사용자가 이미지 파일을 업로드하면 `scan_product_id_from_bytes()`가 바이트를 이미지로 바꿔 QR/바코드를 추출합니다. 추출된 문자열은 `product_id`로 사용되며, `/inventory`의 입출고 처리에 그대로 연결됩니다.

## 4. 실행 방법

### 가상환경 활성화

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

cmd:

```bat
.venv\Scripts\activate.bat
```

### 패키지 설치

필수:

```bash
pip install Flask
```

선택:

```bash
pip install opencv-python pyzbar numpy
```

### 서버 실행

```bash
python app.py
```

### 접속 URL

- `http://127.0.0.1:5000`
- 같은 Wi-Fi 모바일 접속: `http://PC_IP:5000`

### 기본 계정

- `admin / admin123`
- `staff / staff123`

## 5. 검증 절차

1. `admin`으로 로그인한다.
2. 상품을 등록한다.
3. 입고를 수행해 `Inventory.quantity`가 증가하는지 확인한다.
4. 출고를 수행해 `Inventory.quantity`가 감소하는지 확인한다.
5. 재고 조회에서 상품명, 수량, 최소 재고 기준이 표시되는지 확인한다.
6. 재고가 기준 이하인 상품이 있으면 `Alert`가 생성되는지 확인한다.
7. 입출고 이력에서 `StockLog`가 남는지 확인한다.
8. `staff`로 로그인해 상품 등록이 제한되는지 확인한다.
9. 모바일 브라우저에서 같은 화면에 접속되는지 확인한다.

## 6. 교수님 설명용 1분 요약

이 프로젝트는 `app.py`가 Flask 서버를 실행하는 구조이고, SQLite는 `database.py`가 관리합니다. 로그인은 `/login`에서 처리되며, 세션의 `role` 값으로 `admin`과 `staff` 권한을 구분합니다. 상품 등록은 `inventory.register_product()`가 `Product`와 `Inventory` 테이블을 갱신하고, 입고와 출고는 `inventory.adjust_stock()`가 `Inventory` 수량과 `StockLog` 이력을 함께 처리합니다. 현재 재고가 `Product.min_quantity` 이하가 되면 `Alert` 테이블에 부족 알림이 생성되며, QR/바코드 인식은 `scanner.py`에서 담당합니다. `project.py`는 참고용이며 최종 실행은 반드시 `app.py` 기준입니다.
