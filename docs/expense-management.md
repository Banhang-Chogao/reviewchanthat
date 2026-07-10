# Expense Management

Cong cu rieng tu ghi chep va phan tich chi phi hang ngay, local-first, ma hoa AES-GCM.

## Tinh nang

- Them/xoa/nhan ban dong giao dich
- Inline edit voi autosave
- Undo thao tac gan nhat
- Sort/filter/search du lieu
- Filter theo thang, loai chi phi, phuong thuc thanh toan
- Dinh dang VND tu dong
- Export/Import ma hoa AES-GCM (PBKDF2)
- Export CSV
- 10 bieu do Chart.js
- Local insight engine (khong goi API ngoai)
- Access gate bao ve (SHA-256)
- Session lock

## Cau truc bang

| Cot | Field | Ghi chu |
|-----|-------|---------|
| A | Sequence | Nhap tay |
| B | Income | Nhap tay, VND |
| C | Expense Amount | Nhap tay, VND |
| D | Expense Label | Nhap tay |
| E | Expense Type | Nhap tay |
| F | Transaction Type | Nhap tay |
| G | Route | Nhap tay |
| H | Bank Route | Nhap tay |
| I | Remark | Nhap tay |
| J | Date | **Cong thuc**: tu tinh tu D/M/Y |
| K | D | Nhap tay |
| L | M | Nhap tay |
| M | Y | Nhap tay |

Cot J (Date) la read-only, tu dong tinh tu D/M/Y.
