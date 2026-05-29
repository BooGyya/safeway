import os
import sys
import django
import requests
import time

# Django 설정
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from infrastructure.models import TrafficLight
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('PUBLIC_DATA_API_KEY')
BASE_URL = 'https://api.data.go.kr/openapi/tn_pubr_public_traffic_light_api'


def fetch_page(page_no, num_of_rows=1000):
    params = {
        'serviceKey': API_KEY,
        'pageNo': page_no,
        'numOfRows': num_of_rows,
        'type': 'json',
    }
    # 3번 재시도
    for attempt in range(3):
        try:
            response = requests.get(
                BASE_URL,
                params=params,
                timeout=30,  # 30초로 증가
                verify=False
            )
            return response.json()
        except Exception as e:
            print(f"  재시도 {attempt + 1}/3: {e}")
            time.sleep(2)
    raise Exception(f"{page_no}페이지 3번 모두 실패")


def parse_item(item):
    """API 응답 파싱"""
    return {
        'sido': item.get('ctprvnNm', ''),
        'sigungu': item.get('signguNm', ''),
        'road_nm': item.get('roadRouteNm', ''),
        'lat': float(item.get('latitude', 0)),
        'lng': float(item.get('longitude', 0)),
        'sgn_asp_ordr': item.get('sgnaspOrdr', ''),
        'sgn_asp_time': item.get('sgnaspTime', ''),
        'has_audio': item.get('sondSgngnrYn', 'N') == 'Y',
        'has_remndr': item.get('remndrIdctYn', 'N') == 'Y',
        'is_operating': item.get('opratnYn', 'Y') == 'Y',
        'manage_no': item.get('tfclghtManageNo', ''),
        'ref_date': item.get('referenceDate', ''),
    }


def collect_all():
    print("전국 신호등 데이터 수집 시작...")

    # 전체 건수 파악
    first = fetch_page(1, 1)
    total = int(first['response']['body']['totalCount'])
    print(f"전체 건수: {total}건")

    # 기존 데이터 삭제
    TrafficLight.objects.all().delete()
    print("기존 데이터 삭제 완료")

    all_items = []
    page = 1

    while True:
        try:
            data = fetch_page(page)
            items = data['response']['body']['items']

            if not items:
                break

            # 1건일 때 dict로 오는 경우 처리
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

    # DB 저장
    print("DB 저장 중...")
    objs = [TrafficLight(**parse_item(item)) for item in all_items]
    TrafficLight.objects.bulk_create(objs, batch_size=1000)
    print(f"DB 저장 완료! {TrafficLight.objects.count()}건")


if __name__ == '__main__':
    collect_all()