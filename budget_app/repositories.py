import os
import json
import tempfile
import logging
from typing import Generator, List, Dict ,Any
from budget_app.models import Transaction, Budget

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

class DataRepository:
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        try:
            os.makedirs(data_dir, exist_ok=True)
        except Exception as e:
            logging.error(f"데이터 디렉토리({data_dir}) 생성 실패: {e}")
            raise
        
        self.tx_path = os.path.join(data_dir, "transactions.jsonl")
        self.cat_path = os.path.join(data_dir, "categories.jsonl")
        self.bg_path = os.path.join(data_dir, "budgets.jsonl")
        
        self._init_files()

    def _init_files(self):
        # 파일 생성 및 초기화 과정에서 발생할 수 있는 예외 처리
        try:
            if not os.path.exists(self.cat_path):
                self.save_categories(["food", "transport", "rent", "etc"])
            if not os.path.exists(self.tx_path):
                with open(self.tx_path, 'w', encoding='utf-8') as f: pass
            if not os.path.exists(self.bg_path):
                with open(self.bg_path, 'w', encoding='utf-8') as f: pass
        except IOError as e:
            logging.error(f"초기 파일 데이터 생성 중 입출력 오류 발생: {e}")

    # --- Categories ---
    def load_categories(self) -> List[str]:
        if not os.path.exists(self.cat_path): 
            return []
        try:
            with open(self.cat_path, 'r', encoding='utf-8') as f:
                categories = []
                for line_idx, line in enumerate(f, start=1):
                    clean_line = line.strip()
                    if clean_line:
                        categories.append(clean_line)
                return categories
        except IOError as e:
            logging.error(f"카테고리 파일({self.cat_path})을 읽는 중 오류가 발생했습니다: {e}")
            return []

    def save_categories(self, categories: List[str]):
        # 데이터 유효성 검사 (공백 유입 차단)
        for idx, cat in enumerate(categories):
            if not cat or str(cat).strip() == "":
                logging.error(f"카테고리 저장 실패: {idx}번째 인덱스에 유효하지 않은 공백 값이 있습니다.")
                return

        temp_name = None
        try:
            with tempfile.NamedTemporaryFile('w', dir=self.data_dir, delete=False, encoding='utf-8') as tf:
                for cat in categories:
                    tf.write(f"{cat.strip()}\n")
                temp_name = tf.name
            os.replace(temp_name, self.cat_path)
        except Exception as e:
            logging.error(f"카테고리 파일 원자적 저장 중 예외 발생: {e}")
            if temp_name and os.path.exists(temp_name):
                os.remove(temp_name)

    # --- Budgets ---
    def load_budgets(self) -> Dict[str, int]:
        budgets = {}
        if not os.path.exists(self.bg_path): 
            return budgets
        try:
            with open(self.bg_path, 'r', encoding='utf-8') as f:
                for line_idx, line in enumerate(f, start=1):
                    if line.strip():
                        try:
                            data = json.loads(line)
                            # 필수 키 유효성 및 데이터 형식 검증 (공백/타입 미달 방지)
                            if 'month' not in data or 'amount' not in data:
                                raise KeyError("필수 필드('month', 'amount')가 누락되었습니다.")
                            if not str(data['month']).strip():
                                raise ValueError("'month' 값이 비어있습니다.")
                            
                            budgets[data['month'].strip()] = int(data['amount'])
                        except (json.JSONDecodeError, TypeError, KeyError, ValueError) as je:
                            # 형식이 맞지 않으면 무시하거나 깨진 공백으로 처리하지 않고, 원인을 명확히 경고
                            logging.error(f"예산 데이터 파싱 에러 [{self.bg_path} - {line_idx}번째 줄]: {je}")
        except IOError as e:
            logging.error(f"예산 파일을 읽는 중 시스템 오류 발생: {e}")
        return budgets

    def save_budget(self, month: str, amount: int):
        # 입력 파라미터 사전 검증
        if not month or month.strip() == "":
            logging.error("예산 저장 실패: 'month' 정보가 비어있거나 공백입니다.")
            return
        try:
            amount = int(amount)
        except (ValueError, TypeError):
            logging.error(f"예산 저장 실패: 'amount'({amount})는 올바른 정수 형식이 아닙니다.")
            return

        budgets = self.load_budgets()
        budgets[month.strip()] = amount
        
        temp_name = None
        try:
            with tempfile.NamedTemporaryFile('w', dir=self.data_dir, delete=False, encoding='utf-8') as tf:
                for m, a in budgets.items():
                    # 한글 깨짐 방지 및 가독성을 위해 ensure_ascii=False 적용
                    tf.write(json.dumps({"month": m, "amount": a}, ensure_ascii=False) + "\n")
                temp_name = tf.name
            os.replace(temp_name, self.bg_path)
        except Exception as e:
            logging.error(f"예산 데이터 파일 저장 중 오류 발생: {e}")
            if temp_name and os.path.exists(temp_name):
                os.remove(temp_name)

    # --- Transactions (Streaming Generator) ---
    def stream_transactions(self) -> Generator[Any, None, None]:
        if not os.path.exists(self.tx_path): 
            return
        try:
            with open(self.tx_path, 'r', encoding='utf-8') as f:
                for line_idx, line in enumerate(f, start=1):
                    if line.strip():
                        try:
                            data = json.loads(line)
                            # 빈 데이터 딕셔너리가 유입되었거나 파일 포맷이 망가진 경우 체크
                            if not data:
                                raise ValueError("JSON 데이터가 비어있습니다.")
                            yield Transaction.from_dict(data)
                        except json.JSONDecodeError as je:
                            logging.error(f"거래 내역 파일 구문 오류 [{self.tx_path} - {line_idx}번째 줄]: 깨진 JSON 문자열입니다. ({je})")
                        except Exception as e:
                            logging.error(f"거래 내역 데이터 변환 실패 [{self.tx_path} - {line_idx}번째 줄]: {e}")
        except IOError as e:
            logging.error(f"거래 내역 파일을 읽는 중 I/O 오류 발생: {e}")

    def add_transaction(self, tx: Any):
        try:
            # 객체 자체의 유효성 검증
            if tx is None:
                raise ValueError("추가하려는 Transaction 객체가 None입니다.")
            
            jsonl_line = tx.to_jsonl()
            if not jsonl_line or jsonl_line.strip() == "":
                raise ValueError("Transaction 객체가 비어있는 문자열을 반환했습니다.")

            with open(self.tx_path, 'a', encoding='utf-8') as f:
                f.write(jsonl_line.strip() + "\n")
        except IOError as e:
            logging.error(f"거래 내역 파일에 데이터를 추가(Append)하지 못했습니다: {e}")
        except Exception as e:
            logging.error(f"거래 내역 추가 중 예외 발생: {e}")

    def rewrite_transactions(self, transactions: List[Any]):
        if transactions is None:
            logging.error("거래 내역 재작성 실패: 전달된 리스트가 None입니다.")
            return

        temp_name = None
        try:
            with tempfile.NamedTemporaryFile('w', dir=self.data_dir, delete=False, encoding='utf-8') as tf:
                for idx, tx in enumerate(transactions):
                    if tx is None:
                        raise ValueError(f"{idx}번째 요소가 올바른 Transaction 객체가 아닙니다 (None).")
                    tf.write(tx.to_jsonl().strip() + "\n")
                temp_name = tf.name
            os.replace(temp_name, self.tx_path)
        except Exception as e:
            logging.error(f"거래 내역 파일 전체 재작성 중 오류 발생 (작업 취소됨): {e}")
            if temp_name and os.path.exists(temp_name):
                os.remove(temp_name)