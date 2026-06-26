import os
import sys
import django
import requests
import time
import xml.etree.ElementTree as ET
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from infrastructure.models import Facility
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('PUBLIC_DATA_API_KEY')
BASE_URL = 'http://apis.data.go.kr/B554287/DisabledPersonConvenientFacility/getDisConvFaclList'


def fetch_page(page_no, num_of_rows=1000):
    params = {
        'serviceKey': API_KEY,
        'pageNo': page_no,
        'numOfRows': num_of_rows,
    }
    for attempt in range(3):
        try:
            response = requests.get(
                BASE_URL,
                params=params,
                timeout=30,
                verify=False
            )
            return ET.fromstring(response.content)
        except Exception as e:
            print(f"  재시도 {attempt + 1}/3: {e}")
            time.sleep(2)
    raise Exception(f"{page_no}페이지 3번 모두 실패")


def parse_item(item):
    def get_text(tag):
        el = item.find(tag)
        return el.text.strip() if el is not None and el.text else ''

    lat = get_text('faclLat')
    lng = get_text('faclLng')

    return {
        'name': get_text('faclNm'),
        'facility_type': 'other',
        'sido': '',
        'sigungu': '',
        'address': get_text('lcMnad'),
        'lat': float(lat) if lat else None,
        'lng': float(lng) if lng else None,
        'is_available': get_text('salStaDivCd') == 'Y',
        'ref_date': '',
    }


def collect_all():
    print("장애인 편의시설 데이터 수집 시작 (100페이지부터)...")

    # 전체 건수 파악
    first = fetch_page(1, 1)
    total_el = first.find('.//totalCount')
    total = int(total_el.text) if total_el is not None else 0
    print(f"전체 건수: {total}건")

    # 기존 데이터 삭제 안 함 (이어서 수집)
    # Facility.objects.all().delete()

    all_items = []
    page = 100  # 100페이지부터 시작

    while True:
        try:
            root = fetch_page(page)
            items = root.findall('.//servList')

            if not items:
                break

            all_items.extend(items)
            print(f"{page}페이지 완료 ({99000 + len(all_items)}/{total}건)")

            if 99000 + len(all_items) >= total:
                break

            page += 1
            time.sleep(0.1)

        except Exception as e:
            print(f"{page}페이지 오류: {e}")
            break

    print(f"\n추가 수집 완료! {len(all_items)}건")

    print("DB 저장 중...")
    objs = [Facility(**parse_item(item)) for item in all_items]
    Facility.objects.bulk_create(objs, batch_size=1000)
    print(f"DB 총 저장: {Facility.objects.count()}건")


if __name__ == '__main__':
    collect_all()