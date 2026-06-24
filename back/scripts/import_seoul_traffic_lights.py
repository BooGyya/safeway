import os
import sys
import django
import csv
import shapefile
from pyproj import Transformer

# Django 설정
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from infrastructure.models import TrafficLight

transformer = Transformer.from_crs("EPSG:5186", "EPSG:4326", always_xy=True)

# ===== 경로 설정 (본인 환경에 맞게 수정) =====
SIGNAL_CSV = r'C:\Users\SSAFY\Desktop\safesafe\DATA\신호등(부착대).csv'
AUDIO_SHP = r'C:\Users\SSAFY\Desktop\safesafe\DATA\A073_P_음향신호기_현황\A073_P 음향신호기.shp'
REMNDR_SHP = r'C:\Users\SSAFY\Desktop\safesafe\DATA\A074_P_잔여시간표시기\A074_P.shp'
# =============================================

# 음향신호기 좌표 수집
print("음향신호기 로딩...")
audio_coords = set()
sf = shapefile.Reader(AUDIO_SHP, encoding='euc-kr')
for r in sf.records():
    try:
        x, y = float(r['XCE']), float(r['YCE'])
        lng, lat = transformer.transform(x, y)
        if 37.4 <= lat <= 37.7 and 126.7 <= lng <= 127.2:
            audio_coords.add((round(lat, 4), round(lng, 4)))
    except:
        pass
print(f"음향신호기: {len(audio_coords)}개")

# 잔여시간표시기 좌표 수집
print("잔여시간표시기 로딩...")
remndr_coords = set()
sf2 = shapefile.Reader(REMNDR_SHP, encoding='euc-kr')
for r in sf2.records():
    try:
        x, y = float(r['XCE']), float(r['YCE'])
        lng, lat = transformer.transform(x, y)
        if 37.4 <= lat <= 37.7 and 126.7 <= lng <= 127.2:
            remndr_coords.add((round(lat, 4), round(lng, 4)))
    except:
        pass
print(f"잔여시간표시기: {len(remndr_coords)}개")

def is_near(lat, lng, coord_set):
    rlat, rlng = round(lat, 4), round(lng, 4)
    for dlat in [-0.001, 0, 0.001]:
        for dlng in [-0.001, 0, 0.001]:
            if (round(rlat + dlat, 4), round(rlng + dlng, 4)) in coord_set:
                return True
    return False

# 신호등 CSV 처리
print("신호등 CSV 처리 중...")
lights = []
with open(SIGNAL_CSV, encoding='euc-kr') as f:
    reader = csv.reader(f)
    header = next(reader)
    x_idx = header.index('X좌표')
    y_idx = header.index('Y좌표')
    for i, row in enumerate(reader):
        try:
            x, y = float(row[x_idx]), float(row[y_idx])
            lng, lat = transformer.transform(x, y)
            if 37.4 <= lat <= 37.7 and 126.7 <= lng <= 127.2:
                lights.append(TrafficLight(
                    lat=round(lat, 7),
                    lng=round(lng, 7),
                    road_nm='서울',
                    has_audio=is_near(lat, lng, audio_coords),
                    has_remndr=is_near(lat, lng, remndr_coords),
                ))
        except:
            pass
        if i % 5000 == 0:
            print(f"  {i}행 처리 중...")

print(f"서울 신호등 {len(lights)}개 변환 완료")

# 기존 서울 데이터 삭제 후 삽입
print("기존 서울 신호등 삭제 중...")
TrafficLight.objects.filter(
    lat__range=(37.4, 37.7),
    lng__range=(126.7, 127.2)
).delete()

print("DB 삽입 중...")
TrafficLight.objects.bulk_create(lights, batch_size=1000)
print(f"완료! 총 {len(lights)}개")
print(f"음향신호기 있음: {sum(1 for l in lights if l.has_audio)}개")
print(f"잔여시간표시기 있음: {sum(1 for l in lights if l.has_remndr)}개")