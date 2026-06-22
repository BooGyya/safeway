import os
import sys
import django
import requests
import time
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from infrastructure.models import SupportCenter
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('PUBLIC_DATA_API_KEY')
BASE_URL = 'https://api.data.go.kr/openapi/tn_pubr_public_tfcwker_mvmn_cnter_api'


def fetch_page(page_no, num_of_rows=1000):
    params = {
        'serviceKey': API_KEY,
        'pageNo': page_no,
        'numOfRows': num_of_rows,
        'type': 'json',
    }
    for attempt in range(3):
        try:
            response = requests.get(
                BASE_URL,
                params=params,
                timeout=30,
                verify=False
            )
            return response.json()
        except Exception as e:
            print(f"  재시도 {attempt + 1}/3: {e}")
            time.sleep(2)
    raise Exception(f"{page_no}페이지 3번 모두 실패")


def parse_item(item):
    return {
        'name': item.get('tfcwkerMvmnCnterNm', '') or item.get('institutionNm', ''),
        'sido': item.get('insttNm', ''),
        'sigungu': '',
        'address': item.get('rdnmadr', '') or item.get('lnmadr', ''),
        'lat': float(item.get('latitude', 0) or 0),
        'lng': float(item.get('longitude', 0) or 0),
        'phone': item.get('phoneNumber', '') or item.get('rceptPhoneNumber', ''),
        'is_operating': True,
    }

def collect_all():
    print("교통약자 이동지원센터 데이터 수집 시작...")

    first = fetch_page(1, 1)
    total = int(first['response']['body']['totalCount'])
    print(f"전체 건수: {total}건")

    SupportCenter.objects.all().delete()
    print("기존 데이터 삭제 완료")

    all_items = []
    page = 1

    while True:
        try:
            data = fetch_page(page)
            items = data['response']['body']['items']

            if not items:
                break

            if isinstance(items, dict):
                items = [items]

            all_items.extend(items)
            print(f"{page}페이지 완료 ({len(all_items)}/{total}건)")

            if len(all_items) >= total:
                break

            page += 1
            time.sleep(0.1)

        except Exception as e:
            print(f"{page}페이지 오류: {e}")
            break

    print(f"\n수집 완료! 총 {len(all_items)}건")

    print("DB 저장 중...")
    objs = [SupportCenter(**parse_item(item)) for item in all_items]
    SupportCenter.objects.bulk_create(objs, batch_size=1000)
    print(f"DB 저장 완료! {SupportCenter.objects.count()}건")


if __name__ == '__main__':
    collect_all()