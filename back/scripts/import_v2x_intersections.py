"""
서울 V2X 신호제어기 설치 교차로(itstId + 위경도) import 스크립트
실시간 신호 잔여시간 조회 시 좌표 -> itstId 매핑에 사용한다.

사용법:
    python scripts/import_v2x_intersections.py
"""

import os
import sys
import django

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

import requests
from dotenv import load_dotenv
from infrastructure.models import V2XIntersection

load_dotenv(dotenv_path=os.path.join(BASE_DIR, '.env'), override=True)

API_KEY = os.getenv('SEOUL_TDATA_API_KEY')
BASE_URL = 'http://t-data.seoul.go.kr/apig/apiman-gateway/tapi/v2xCrossroadMapInformation/1.0'


def fetch_page(page_no, num_of_rows=1000):
    params = {'apikey': API_KEY, 'type': 'json', 'numOfRows': num_of_rows, 'pageNo': page_no}
    response = requests.get(BASE_URL, params=params, timeout=20)
    response.raise_for_status()
    return response.json()


def run():
    created_count = 0
    updated_count = 0
    page_no = 1

    while True:
        items = fetch_page(page_no)
        if not items:
            break

        for item in items:
            itst_id = item.get('itstId')
            lat = item.get('mapCtptIntLat')
            lng = item.get('mapCtptIntLot')
            if not itst_id or lat is None or lng is None:
                continue

            obj, created = V2XIntersection.objects.update_or_create(
                itst_id=itst_id,
                defaults={'name': item.get('itstNm') or '', 'lat': lat, 'lng': lng},
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        print(f'페이지 {page_no}: {len(items)}건 처리')
        if len(items) < 1000:
            break
        page_no += 1

    print(f'완료: {created_count}건 생성, {updated_count}건 갱신')


if __name__ == '__main__':
    run()
