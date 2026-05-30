import sys
import argparse
from budget_app.repositories import DataRepository
from budget_app.services import BudgetService

def main():
    parser = argparse.ArgumentParser(description="대화형 지향 가계부 CLI 애플리케이션")
    parser.add_index = True
    parser.add_argument('--data-dir', default='./data', help='데이터 저장 폴더 경로 (기본값: ./data)')

    subparsers = parser.add_subparsers(dest='command', help='실행할 명령 기능 선택')

    # 1. add
    subparsers.add_parser('add', help='거래 추가 (대화형 실행)')
    
    # 2. list
    p_list = subparsers.add_parser('list', help='최신순 거래 목록 조회')
    p_list.add_argument('--limit', type=int, default=10, help='조회 건수 한도 (기본: 10)')

    # 3. search
    p_src = subparsers.add_parser('search', help='조건별 거래 상세 검색')
    p_src.add_argument('--from', dest='from_date', help='시작 날짜 (YYYY-MM-DD)')
    p_src.add_argument('--to', dest='to_date', help='종료 날짜 (YYYY-MM-DD)')
    p_src.add_argument('--category', help='카테고리 필터')
    p_src.add_argument('--type', choices=['income', 'expense'], help='타입 필터')
    p_src.add_argument('--q', dest='query', help='메모 키워드 검색')
    p_src.add_argument('--tag', help='태그 검색')

    # 4. summary
    p_sum = subparsers.add_parser('summary', help='월별 지출/수입 통계 및 요약')
    p_sum.add_argument('--month', required=True, help='조회 대상 월 (YYYY-MM)')
    p_sum.add_argument('--top', type=int, default=3, help='카테고리 노출 순위 개수 (기본: 3)')

    # 5. budget
    p_bud = subparsers.add_parser('budget', help='예산 설정 및 관리')
    p_bud_sub = p_bud.add_subparsers(dest='subcommand')
    p_set = p_bud_sub.add_parser('set', help='예산 지정')
    p_set.add_argument('--month', required=True, help='지정 대상 월 (YYYY-MM)')
    p_set.add_argument('--amount', type=int, required=True, help='설정할 예산 금액')

    # 6. category
    p_cat = subparsers.add_parser('category', help='카테고리 관리 기능')
    p_cat.add_argument('action', choices=['add', 'list', 'remove'], help='수행 액션 선택')
    p_cat.add_argument('name', nargs='?', help='카테고리 명칭')

    # 7. update
    p_upd = subparsers.add_parser('update', help='거래 데이터 수정 (대화형)')
    p_upd.add_argument('--id', required=True, help='수정할 거래 고유 ID')

    # 8. delete
    p_del = subparsers.add_parser('delete', help='거래 내역 삭제')
    p_del.add_argument('--id', required=True, help='삭제할 거래 고유 ID')

    # 9, 10. import/export
    p_imp = subparsers.add_parser('import', help='외부 CSV 파일로부터 데이터 가져오기')
    p_imp.add_argument('--from', dest='from_path', required=True, help='가져올 CSV 파일 경로')

    p_exp = subparsers.add_parser('export', help='데이터를 외부 CSV 파일로 내보내기')
    p_exp.add_argument('--out', required=True, help='저장할 출력 CSV 파일 경로')
    p_exp.add_argument('--month', help='내보낼 대상 월 (YYYY-MM)')
    p_exp.add_argument('--from', dest='from_date', help='시작 기준 날짜 (YYYY-MM-DD)')
    p_exp.add_argument('--to', dest='to_date', help='종료 기준 날짜 (YYYY-MM-DD)')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    # 초기화 및 종속성 주입
    repo = DataRepository(args.data_dir)
    service = BudgetService(repo)

    # 명령 분기 처리
    if args.command == 'add':
        service.interactive_add()
    elif args.command == 'list':
        service.list_transactions(args.limit)
    elif args.command == 'search':
        service.search_transactions(args.from_date, args.to_date, args.category, args.type, args.query, args.tag)
    elif args.command == 'summary':
        service.show_summary(args.month, args.top)
    elif args.command == 'budget':
        if args.subcommand == 'set':
            service.set_budget(args.month, args.amount)
        else:
            print("사용법: python -m budget_app budget set --month YYYY-MM --amount 금액")
    elif args.command == 'category':
        service.manage_category(args.action, args.name)
    elif args.command == 'update':
        service.interactive_update(args.id)
    elif args.command == 'delete':
        service.delete_transaction(args.id)
    elif args.command == 'import':
        service.import_csv(args.from_path)
    elif args.command == 'export':
        if not args.month and not (args.from_date or args.to_date):
            print("[오류] export 명령은 --month 또는 --from/--to 기간 중 하나 이상이 필수입니다.")
            sys.exit(1)
        service.export_csv(args.out, args.month, args.from_date, args.to_date)

if __name__ == '__main__':
    main()