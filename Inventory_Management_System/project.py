# import tkinter as tk
# from tkinter import ttk, messagebox
# import cv2


# inventory = {
#     "P001": {"name": "콜라", "qty": 15},
#     "P002": {"name": "사이다", "qty": 3},
#     "P003": {"name": "과자", "qty": 20},
# }

# MIN_STOCK = 5


# def scan_barcode():
#     cap = cv2.VideoCapture(0)

#     if not cap.isOpened():
#         messagebox.showerror("카메라 오류", "카메라를 열 수 없습니다.")
#         return None

#     detector = cv2.QRCodeDetector()
#     result_code = None

#     while True:
#         ret, frame = cap.read()

#         if not ret:
#             break

#         data, bbox, _ = detector.detectAndDecode(frame)

#         if data:
#             result_code = data

#             if bbox is not None:
#                 bbox = bbox.astype(int)
#                 for i in range(len(bbox[0])):
#                     pt1 = tuple(bbox[0][i])
#                     pt2 = tuple(bbox[0][(i + 1) % len(bbox[0])])
#                     cv2.line(frame, pt1, pt2, (0, 255, 0), 2)

#             cv2.putText(frame, result_code, (30, 40),
#                         cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

#             cv2.imshow("QR Scanner", frame)
#             cv2.waitKey(500)

#             cap.release()
#             cv2.destroyAllWindows()
#             return result_code

#         cv2.imshow("QR Scanner - q 키를 누르면 종료", frame)

#         if cv2.waitKey(1) & 0xFF == ord("q"):
#             break

#     cap.release()
#     cv2.destroyAllWindows()
#     return result_code


# def scan_for_in():
#     code = scan_barcode()

#     if code:
#         in_code_entry.delete(0, tk.END)
#         in_code_entry.insert(0, code)

#         if code in inventory:
#             in_name_entry.delete(0, tk.END)
#             in_name_entry.insert(0, inventory[code]["name"])

#         messagebox.showinfo("스캔 완료", f"인식된 코드: {code}")


# def scan_for_out():
#     code = scan_barcode()

#     if code:
#         out_code_entry.delete(0, tk.END)
#         out_code_entry.insert(0, code)

#         messagebox.showinfo("스캔 완료", f"인식된 코드: {code}")


# def refresh_table():
#     for row in stock_table.get_children():
#         stock_table.delete(row)

#     for code, data in inventory.items():
#         status = "부족" if data["qty"] <= MIN_STOCK else "정상"
#         stock_table.insert("", "end", values=(code, data["name"], data["qty"], status))


# def stock_in():
#     code = in_code_entry.get().strip()
#     name = in_name_entry.get().strip()
#     qty = in_qty_entry.get().strip()

#     if not code or not name or not qty:
#         messagebox.showwarning("입력 오류", "상품코드, 상품명, 입고수량을 모두 입력하세요.")
#         return

#     if not qty.isdigit():
#         messagebox.showwarning("입력 오류", "수량은 숫자로 입력하세요.")
#         return

#     qty = int(qty)

#     if code in inventory:
#         inventory[code]["qty"] += qty
#         inventory[code]["name"] = name
#     else:
#         inventory[code] = {"name": name, "qty": qty}

#     refresh_table()
#     messagebox.showinfo("입고 완료", f"{name} {qty}개 입고 완료")

#     in_code_entry.delete(0, tk.END)
#     in_name_entry.delete(0, tk.END)
#     in_qty_entry.delete(0, tk.END)


# def stock_out():
#     code = out_code_entry.get().strip()
#     qty = out_qty_entry.get().strip()

#     if not code or not qty:
#         messagebox.showwarning("입력 오류", "상품코드와 출고수량을 입력하세요.")
#         return

#     if not qty.isdigit():
#         messagebox.showwarning("입력 오류", "수량은 숫자로 입력하세요.")
#         return

#     qty = int(qty)

#     if code not in inventory:
#         messagebox.showerror("출고 오류", "등록되지 않은 상품입니다.")
#         return

#     if inventory[code]["qty"] < qty:
#         messagebox.showerror(
#             "재고 부족",
#             f"현재 재고: {inventory[code]['qty']}개\n출고 요청: {qty}개"
#         )
#         return

#     inventory[code]["qty"] -= qty
#     refresh_table()

#     messagebox.showinfo("출고 완료", f"{inventory[code]['name']} {qty}개 출고 완료")

#     out_code_entry.delete(0, tk.END)
#     out_qty_entry.delete(0, tk.END)


# def search_stock():
#     keyword = search_entry.get().strip()

#     for row in stock_table.get_children():
#         stock_table.delete(row)

#     for code, data in inventory.items():
#         if keyword in code or keyword in data["name"]:
#             status = "부족" if data["qty"] <= MIN_STOCK else "정상"
#             stock_table.insert("", "end", values=(code, data["name"], data["qty"], status))


# root = tk.Tk()
# root.title("재고 관리 시스템")
# root.geometry("700x500")

# title_label = tk.Label(root, text="재고 관리 시스템", font=("맑은 고딕", 18, "bold"))
# title_label.pack(pady=10)

# notebook = ttk.Notebook(root)
# notebook.pack(expand=True, fill="both", padx=10, pady=10)

# # 입고 화면
# in_frame = ttk.Frame(notebook)
# notebook.add(in_frame, text="입고")

# tk.Label(in_frame, text="상품코드").grid(row=0, column=0, padx=10, pady=10)
# in_code_entry = tk.Entry(in_frame)
# in_code_entry.grid(row=0, column=1, padx=10, pady=10)

# tk.Button(in_frame, text="바코드/QR 스캔", command=scan_for_in).grid(row=0, column=2, padx=10)

# tk.Label(in_frame, text="상품명").grid(row=1, column=0, padx=10, pady=10)
# in_name_entry = tk.Entry(in_frame)
# in_name_entry.grid(row=1, column=1, padx=10, pady=10)

# tk.Label(in_frame, text="입고수량").grid(row=2, column=0, padx=10, pady=10)
# in_qty_entry = tk.Entry(in_frame)
# in_qty_entry.grid(row=2, column=1, padx=10, pady=10)

# tk.Button(in_frame, text="입고 처리", command=stock_in, width=20).grid(
#     row=3, column=0, columnspan=3, pady=20
# )

# # 출고 화면
# out_frame = ttk.Frame(notebook)
# notebook.add(out_frame, text="출고")

# tk.Label(out_frame, text="상품코드").grid(row=0, column=0, padx=10, pady=10)
# out_code_entry = tk.Entry(out_frame)
# out_code_entry.grid(row=0, column=1, padx=10, pady=10)

# tk.Button(out_frame, text="바코드/QR 스캔", command=scan_for_out).grid(row=0, column=2, padx=10)

# tk.Label(out_frame, text="출고수량").grid(row=1, column=0, padx=10, pady=10)
# out_qty_entry = tk.Entry(out_frame)
# out_qty_entry.grid(row=1, column=1, padx=10, pady=10)

# tk.Button(out_frame, text="출고 처리", command=stock_out, width=20).grid(
#     row=2, column=0, columnspan=3, pady=20
# )

# # 현재 재고 상태
# stock_frame = ttk.Frame(notebook)
# notebook.add(stock_frame, text="현재 재고 상태")

# search_entry = tk.Entry(stock_frame)
# search_entry.pack(pady=10)

# tk.Button(stock_frame, text="검색", command=search_stock).pack()

# columns = ("상품코드", "상품명", "재고수량", "상태")
# stock_table = ttk.Treeview(stock_frame, columns=columns, show="headings")

# for col in columns:
#     stock_table.heading(col, text=col)
#     stock_table.column(col, width=130, anchor="center")

# stock_table.pack(expand=True, fill="both", padx=10, pady=10)

# tk.Button(stock_frame, text="전체 조회", command=refresh_table).pack(pady=5)

# refresh_table()

# root.mainloop()