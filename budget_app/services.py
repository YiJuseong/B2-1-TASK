import csv
import os
import uuid
import sys
from datetime import datetime
from typing import List, Optional
from budget_app.models import Transaction
from budget_app.repositories import DataRepository
from dataclasses import dataclass, asdict, field


class BudgetService:
    def __init__(self, repo: DataRepository):
        self.repo = repo

    def _validate_date(self, date_str: str) -> bool:
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            return True
        except ValueError:
            return False

    def interactive_add(self):
        print("\n=== 새 거래 추가 ===")
    
        try:
            # 1. 날짜 입력
            while True:
                date = input("날짜 입력 (YYYY-MM-DD) [엔터시 오늘]: ").strip()
                if not date:
                    date = datetime.today().strftime("%Y-%m-%d")
                    break
                if self._validate_date(date): 
                    break
                print("[오류] 올바른 날짜 형식이 아닙니다.")

        # 2. 타입 입력
            while True:
                tx_type = input("타입 입력 (income/expense): ").strip().lower()
                if tx_type in ['income', 'expense']: 
                    break
                print("[오류] income 또는 expense만 입력 가능합니다.")

        # 3. 카테고리 입력
            categories = self.repo.load_categories()
            while True:
                print(f"사용 가능한 카테고리: {', '.join(categories)}")
                category = input("카테고리명: ").strip()
                if category in categories: 
                    break
                print(f"[오류] 존재하지 않는 카테고리입니다.")
            
                yn = input("해당 카테고리를 새로 등록할까요? (y/n): ").strip().lower()
                if yn == 'y':
                    categories.append(category)
                    self.repo.save_categories(categories)
                    break

        # 4. 금액 입력
            while True:
                try:
                    amount = int(input("금액 (양수 정수): ").strip())
                    if amount > 0: 
                        break
                    print("[오류] 금액은 0보다 커야 합니다.")
                except ValueError:
                    print("[오류] 숫자만 입력 가능합니다.")

        # 5. 메모 및 태그
            memo = input("메모 (선택, 생성시 엔터): ").strip()
            tags_raw = input("태그 (쉼표 분리, 선택): ").strip()
            tags = [t.strip() for t in tags_raw.split(",") if t.strip()] if tags_raw else []

        # 6. 객체 생성 및 저장
            tx_id = str(uuid.uuid4())[:8]
            new_tx = Transaction(id=tx_id, type=tx_type, date=date, amount=amount, category=category, memo=memo, tags=tags)
            self.repo.add_transaction(new_tx)
            print(f"🎉 성공적으로 저장되었습니다! 생성된 거래 ID: {tx_id}")

    # 🚨 [Ctrl + C] 방어벽
        except KeyboardInterrupt:
            print("\n\n👋 [입력 취소] 사용자가 입력을 중단했습니다. 메인 화면으로 돌아갑니다.")
            sys.exit(1) # 의도치 않은 중단이므로 종료 코드 1 또는 안전하게 0으로 설정 가능합니다.

    # 🚨 [Ctrl + D] 방어벽
        except EOFError:
            print("\n\n👋 [입력 종료] EOF 신호가 감지되어 프로그램을 안전하게 종료합니다.")
            sys.exit(0) # 사용자가 입력을 끝내겠다는 명확한 신호(EOF)이므로 정상 종료인 0을 반환합니다.

    def list_transactions(self, limit: int):
        all_tx = list(self.repo.stream_transactions())
        all_tx.sort(key=lambda x: x.date, reverse=True)
        
        print(f"\n--- 최신 거래 목록 (최대 {limit}건) ---")
        for tx in all_tx[:limit]:
            print(f"[{tx.id}] {tx.date} | {tx.type.upper()} | {tx.category} | {tx.amount:,}원 | {tx.memo} {tx.tags}")

    def search_transactions(self, start_date: Optional[str], end_date: Optional[str], 
                            category: Optional[str], tx_type: Optional[str], 
                            query: Optional[str], tag: Optional[str]):
        
        # 스트리밍 조건 필터링
        filtered = self.repo.stream_transactions()
        
        if start_date: filtered = (tx for tx in filtered if tx.date >= start_date)
        if end_date: filtered = (tx for tx in filtered if tx.date <= end_date)
        if category: filtered = (tx for tx in filtered if tx.category == category)
        if tx_type: filtered = (tx for tx in filtered if tx.type == tx_type)
        if query: filtered = (tx for tx in filtered if query in (tx.memo or ""))
        if tag: filtered = (tx for tx in filtered if tag in tx.tags)

        results = list(filtered)
        results.sort(key=lambda x: x.date, reverse=True)

        print(f"\n--- 검색 결과 (총 {len(results)}건) ---")
        for tx in results:
            print(f"[{tx.id}] {tx.date} | {tx.type.upper()} | {tx.category} | {tx.amount:,}원 | {tx.memo} {tx.tags}")

    def show_summary(self, month: str, top_n: int):
        all_tx = list(self.repo.stream_transactions())
        month_tx = [tx for tx in all_tx if tx.date.startswith(month)]

        if not month_tx:
            print(f"\n[안내] {month}월에 해당하는 데이터가 존재하지 않습니다.")
            return

        total_income = sum(tx.amount for tx in month_tx if tx.type == 'income')
        total_expense = sum(tx.amount for tx in month_tx if tx.type == 'expense')
        balance = total_income - total_expense

        # 카테고리별 지출 통계
        cat_expense = {}
        for tx in month_tx:
            if tx.type == 'expense':
                cat_expense[tx.category] = cat_expense.get(tx.category, 0) + tx.amount
        
        sorted_cat = sorted(cat_expense.items(), key=lambda x: x[1], reverse=True)

        print(f"\n=== {month} 월별 요약 ===")
        print(f"총 수입: {total_income:,}원")
        print(f"총 지출: {total_expense:,}원")
        print(f"잔   액: {balance:,}원")
        print(f"\n* 카테고리별 지출 TOP {top_n}:")
        for cat, amt in sorted_cat[:top_n]:
            print(f"  - {cat}: {amt:,}원")

        # 예산 연동 확인
        budgets = self.repo.load_budgets()
        if month in budgets:
            b_amount = budgets[month]
            rate = (total_expense / b_amount) * 100 if b_amount > 0 else 0
            print(f"\n* 예산 사용률: {rate:.1f}% (설정 예산: {b_amount:,}원)")
            if total_expense > b_amount:
                print("⚠️ [경고] 설정된 예산을 초과했습니다!")

    def set_budget(self, month: str, amount: int):
        self.repo.save_budget(month, amount)
        print(f"👍 [{month}] 예산이 {amount:,}원으로 정상 설정되었습니다.")

    def manage_category(self, action: str, name: Optional[str]):
        categories = self.repo.load_categories()
        if action == 'list':
            print("\n--- 등록된 카테고리 목록 ---")
            for c in categories: print(f"- {c}")
        elif action == 'add':
            if not name: return print("[오류] 추가할 카테고리명을 지정하세요.")
            if name in categories: return print("[오류] 이미 존재하는 카테고리입니다.")
            categories.append(name)
            self.repo.save_categories(categories)
            print(f"✅ 카테고리 '{name}' 추가 완료.")
        elif action == 'remove':
            if not name: return print("[오류] 삭제할 카테고리명을 지정하세요.")
            if name not in categories: return print("[오류] 존재하지 않는 카테고리입니다.")
            
            # 카테고리 사용 여부 검사
            in_use = any(tx.category == name for tx in self.repo.stream_transactions())
            if in_use:
                print(f"[거부] '{name}' 카테고리를 사용하는 거래 내역이 존재하여 삭제할 수 없습니다.")
                return
            
            categories.remove(name)
            self.repo.save_categories(categories)
            print(f"❌ 카테고리 '{name}' 삭제 완료.")

    def delete_transaction(self, tx_id: str):
        all_tx = list(self.repo.stream_transactions())
        filtered = [tx for tx in all_tx if tx.id != tx_id]
        
        if len(all_tx) == len(filtered):
            print(f"[오류] ID가 '{tx_id}'인 거래를 찾을 수 없습니다.")
            return

        self.repo.rewrite_transactions(filtered)
        print(f"🗑️ 거래 [ID: {tx_id}]가 정상적으로 삭제되었습니다.")

    def interactive_update(self, tx_id: str):
        all_tx = list(self.repo.stream_transactions())
        target_tx = next((tx for tx in all_tx if tx.id == tx_id), None)

        if not target_tx:
            print(f"[오류] ID가 '{tx_id}'인 거래를 찾을 수 없습니다.")
            return

        print(f"\n=== 거래 수정 (ID: {tx_id}) ===")
        print("수정하지 않고 넘어가려면 그냥 [엔터]를 입력하세요.")

        # 날짜 수정
        date_in = input(f"날짜 [{target_tx.date}]: ").strip()
        if date_in:
            while not self._validate_date(date_in):
                print("[오류] 잘못된 날짜 형식입니다.")
                date_in = input(f"날짜 [{target_tx.date}]: ").strip()
                if not date_in: break
            if date_in: target_tx.date = date_in

        # 타입 수정
        type_in = input(f"타입 [{target_tx.type}]: ").strip().lower()
        if type_in in ['income', 'expense']: target_tx.type = type_in

        # 카테고리 수정
        categories = self.repo.load_categories()
        cat_in = input(f"카테고리 [{target_tx.category}]: ").strip()
        if cat_in and cat_in in categories: target_tx.category = cat_in

        # 금액 수정
        amt_in = input(f"금액 [{target_tx.amount}]: ").strip()
        if amt_in:
            try: target_tx.amount = int(amt_in)
            except ValueError: print("[오류] 숫자가 아니므로 기존 금액을 유지합니다.")

        # 메모 수정
        memo_in = input(f"메모 [{target_tx.memo}]: ").strip()
        if memo_in: target_tx.memo = memo_in

        self.repo.rewrite_transactions(all_tx)
        print("✏️ 거래 정보가 성공적으로 수정되었습니다!")

    def export_csv(self, out_path: str, month: Optional[str] = None, start_date: Optional[str] = None, end_date: Optional[str] = None):
        try:
            tx_stream = self.repo.stream_transactions()
            if month:
                tx_stream = (tx for tx in tx_stream if tx.date.startswith(month))
            if start_date:
                tx_stream = (tx for tx in tx_stream if tx.date >= start_date)
            if end_date:
                tx_stream = (tx for tx in tx_stream if tx.date <= end_date)

            count = 0
            # 출력할 디렉토리가 없으면 자동으로 생성
            os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)

            with open(out_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                # 헤더 작성
                writer.writerow(['id', 'type', 'date', 'amount', 'category', 'memo', 'tags'])
                for tx in tx_stream:
                    writer.writerow([tx.id, tx.type, tx.date, tx.amount, tx.category, tx.memo, ",".join(tx.tags)])
                    count += 1
            print(f"💾 내보내기 완료: 총 {count}건의 데이터가 '{out_path}' 파일로 저장되었습니다.")
        
        except IOError as e:
            print(f"❌ [파일 오류] 내보내기 중 파일 쓰기 실패: {e}")
        except Exception as e:
            print(f"❌ [예기치 못한 오류] 내보내기 실패: {e}")

    def import_csv(self, from_path: str):
        if not os.path.exists(from_path):
            print(f"❌ [오류] 파일이 존재하지 않습니다: {from_path}")
            return

        # 롤백을 위해 기존 카테고리 상태를 복사해 둡니다.
        original_categories = self.repo.load_categories()
        temp_categories = list(original_categories)  # 임시 작업용 카테고리 리스트
        
        # 파싱에 성공한 Transaction 객체들을 임시로 담아둘 리스트
        temp_transactions = []
        
        required_headers = {'type', 'date', 'amount', 'category'}

        try:
            # Excel 호환성을 위해 utf-8-sig 사용
            with open(from_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                
                # 1. CSV 헤더 구조 검증
                if not reader.fieldnames:
                    print("❌ [포맷 오류] CSV 파일이 비어있거나 올바른 형식이 아닙니다.")
                    return
                
                missing_headers = required_headers - set(reader.fieldnames)
                if missing_headers:
                    print(f"❌ [포맷 오류] 필수 헤더가 누락되었습니다. (누락: {', '.join(missing_headers)})")
                    return

                # 2. 행 데이터 루프 및 검증 (오류 발생 시 즉시 중단 및 롤백)
                for line_num, row in enumerate(reader, start=2):
                    # 필수 데이터 빈 값 체크
                    for field_name in required_headers:
                        if not row.get(field_name) or not str(row[field_name]).strip():
                            raise ValueError(f"{line_num}번째 줄: 필수 데이터('{field_name}')가 비어있습니다.")

                    # 타입 유효성 검증
                    row_type = row['type'].strip()
                    if row_type not in ['income', 'expense']:
                        raise ValueError(f"{line_num}번째 줄: 유효하지 않은 타입입니다. ('{row_type}' -> income/expense만 가능)")

                    # 금액 숫자 변환 검증
                    try:
                        amount_val = int(row['amount'])
                    except ValueError:
                        raise ValueError(f"{line_num}번째 줄: 금액 형식이 올바르지 않습니다. ('{row['amount']}')")

                    # 임시 카테고리 업데이트 처리
                    category_val = row['category'].strip()
                    if category_val not in temp_categories:
                        temp_categories.append(category_val)
                    
                    # 태그 파싱
                    tags_str = row.get('tags', '')
                    tags_list = [t.strip() for t in tags_str.split(",") if t.strip()] if tags_str else []

                    # Transaction.from_dict() 데이터 정제
                    cleaned_data = {
                        'id': row.get('id').strip() if row.get('id') else str(uuid.uuid4())[:8],
                        'type': row_type,
                        'date': row['date'].strip(),
                        'amount': amount_val,
                        'category': category_val,
                        'memo': row.get('memo', '').strip(),
                        'tags': tags_list
                    }

                    # 객체를 생성하여 임시 리스트에만 추가 (아직 repo에 저장 안 함)
                    tx = Transaction.from_dict(cleaned_data)
                    temp_transactions.append(tx)

            # 3. 모든 데이터가 완벽할 때만 최종 반영 (All or Nothing)
            for tx in temp_transactions:
                self.repo.add_transaction(tx)
                
            self.repo.save_categories(temp_categories)
            
            print(f"📥 가져오기 완료: 총 {len(temp_transactions)}건의 거래가 안전하게 반영되었습니다.")

        except ValueError as val_err:
            # 데이터 검증 에러 발생 시 커밋하지 않고 중단 (자동 롤백 효과)
            print(f"❌ [가져오기 실패] 데이터 검증 오류로 인해 작업을 취소합니다 (롤백).")
            print(f"   👉 사유: {val_err}")
            
        except UnicodeDecodeError:
            print("❌ [인코딩 오류] 파일 인코딩 형식이 'utf-8'이 아닙니다. 작업을 취소합니다.")
            
        except Exception as e:
            print(f"❌ [예기치 못한 오류] 작업 중 알 수 없는 에러가 발생하여 취소합니다: {e}")
    