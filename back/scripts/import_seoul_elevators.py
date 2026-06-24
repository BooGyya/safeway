"""
서울시 지하철역 엘리베이터 위치정보 import 스크립트

사용법:
    python manage.py shell < scripts/import_seoul_elevators.py
또는:
    python scripts/import_seoul_elevators.py

CSV 파일 경로를 아래 CSV_PATH에 맞게 수정하세요.
"""

import os
import sys
import django
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

import csv
from infrastructure.models import Elevator

# CSV 파일 경로 (실제 경로로 수정)
CSV_PATH = r'C:\Users\user\OneDrive\바탕 화면\safewayaa\서울시 지하철역 엘리베이터 위치정보.csv'

def parse_wkt_point(wkt):
    """'POINT(경도 위도)' 형식에서 위경도 추출"""
    match = re.match(r'POINT\(([0-9.]+)\s+([0-9.]+)\)', wkt.strip())
    if match:
        lng = float(match.group(1))
        lat = float(match.group(2))
        return lat, lng
    return None, None

def run():
    created_count = 0
    skipped_count = 0

    with open(CSV_PATH, encoding='cp949') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # 좌표 파싱
            lat, lng = parse_wkt_point(row['노드 WKT'])
            if not lat or not lng:
                print(f"  좌표 오류 스킵: {row}")
                skipped_count += 1
                continue

            station_name = row['지하철역명']
            sigungu = row['시군구명']
            node_id = row['노드 ID']

            # 중복 방지: 노드 ID로 체크
            exists = Elevator.objects.filter(
                building_nm=station_name,
                address=node_id,
            ).exists()

            if exists:
                skipped_count += 1
                continue

            Elevator.objects.create(
                building_nm=station_name,       # 지하철역명
                sido='서울',
                sigungu=sigungu,                # 시군구명
                address=node_id,                # 노드 ID (중복 방지용)
                lat=lat,
                lng=lng,
                elevator_type='지하철역',
                install_place=row['읍면동명'],   # 읍면동명
                is_operating=True,
            )
            created_count += 1
            print(f"  ✅ {station_name} ({sigungu}) 삽입")

    print(f"\n완료: {created_count}개 삽입, {skipped_count}개 스킵")

if __name__ == '__main__':
    run()