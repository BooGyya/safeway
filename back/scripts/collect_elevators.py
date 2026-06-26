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

from infrastructure.models import Elevator
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('PUBLIC_DATA_API_KEY')
BASE_URL = 'https://apis.data.go.kr/B553664/BuldElevatorService/getBuldElvtrList'


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

    return {
        'building_nm': get_text('buldNm'),
        'sido': get_text('areaNm'),
        'sigungu': get_text('sigunguNm'),
        'address': get_text('address1'),
        'lat': None,
        'lng': None,
        'elevator_type': get_text('elvtrDivNm'),
        'is_operating': get_text('elvtrSttsNm') == '운행중',
        'install_place': get_text('installationPlace'),
    }


def collect_all():
    print("승강기 데이터 수집 시작...")

    first = fetch_page(1, 1)
    print(ET.tostring(first, encoding='unicode')) 
    total_el = first.find('.//totalCount')
    total = int(total_el.text) if total_el is not None else 0
    print(f"전체 건수: {total}건")
 
    Elevator.objects.all().delete()
    print("기존 데이터 삭제 완료")

    all_items = []
    page = 1

    while True:
        try:
            root = fetch_page(page)
            items = root.findall('.//item')

            if not items:
                break

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
    objs = [Elevator(**parse_item(item)) for item in all_items]
    Elevator.objects.bulk_create(objs, batch_size=1000)
    print(f"DB 저장 완료! {Elevator.objects.count()}건")


if __name__ == '__main__':
    collect_all()