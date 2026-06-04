import pandas as pd
import geopandas as gpd
import folium
from shapely.geometry import Point
from folium.plugins import MarkerCluster
from shapely.geometry import Point
from shapely.ops import unary_union
from branca.element import Template, MacroElement
import numpy as np
from folium import Element

df = pd.read_excel('C:\\sqlite\\mysql\\code\\AI\\Mid_project\\data\\file\\all_test - 복사본.xlsx')

# 지도 설명 HTML
template = """
{% macro html(this, kwargs) %}
<div style="
    position: fixed; 
    top: 5px;
    right: 5px;
    width: 270px;
    height: 220px;
    z-index:9999;
    font-size:14px;
    background: #f0f0f0;
    opacity: 0.9;
    padding: 5px;
    border-radius: 10px;
    ">
    <p><a style="color:#00ff00;font-size:150%;">&block;</a>&nbsp;: 위험도 낮음 (녹색)</p>
    <p><a style="color:#ff7f00;font-size:150%;">&block;</a>&nbsp;: 위험도 높음 (주황색)</p>
    <p><a style="color:#ff0000;font-size:150%;">&block;</a>&nbsp;: 위험도 매우 높음 (빨강색)</p>
    <p><img src='https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-red.png' width='25' height='41'/>&nbsp;: 마커 (사고 발생 지역)</p>
    <p><a style="color:#0000ff;font-size:150%;">&#9679;</a>&nbsp;: 파랑색 구역 (어린이 보호 지역)</p>
</div>
<div style="
    position: fixed; 
    bottom: 5px;
    left: 5px;
    width: 250px;
    height: 40px;
    z-index:9999;
    font-size:14px;
    background: #f0f0f0;
    opacity: 0.9;
    padding: 5px;
    border-radius: 10px;
    ">
    <p><b>위험도: </b>위험도를 계산하여 색상으로 표시</p>
    <p><a style="color:#ffff00;font-size:150%;">&cir;</a>&nbsp;: 노란색 원 (보호 필요 지역)</p>
</div>
{% endmacro %}
"""
# 커스텀 색상
custom_css = """
<style>
.leaflet-marker-icon, .leaflet-marker-icon div {
    background-color: rgba(255, 127, 0, 0.7) !important;
    color: white !important;
}
</style>
"""
# 데이터 정리
grouped_df = df.groupby(['시군구', '피해운전자 상해정도']).size().reset_index(name='상해정도 갯수')

grouped_df['피해운전자 상해정도'] = grouped_df['피해운전자 상해정도'].astype(str)
grouped_df['상해정도 갯수'] = grouped_df['상해정도 갯수'].astype(str)
grouped_df['상해정도 정보'] = grouped_df[['피해운전자 상해정도', '상해정도 갯수']].apply(lambda x: ': '.join(x), axis=1)

grouped_df_agg = grouped_df.groupby('시군구')['상해정도 정보'].apply(lambda x: '<br>'.join(x)).reset_index()

df_all = pd.read_excel('C:\\sqlite\\mysql\\code\\AI\\total좌표.xlsx')
columns = ["시군구", "경도", "위도"]
df_all.columns = columns
first_all = df_all.groupby('시군구').first().reset_index()

first_all_merged = first_all.merge(grouped_df_agg, on='시군구', how='left')

geometry = [Point(lon, lat) for lat, lon in zip(first_all_merged['위도'], first_all_merged['경도'])]
gdf_coordinates = gpd.GeoDataFrame(first_all_merged, geometry=geometry, crs='EPSG:4326')
gdf_coordinates = gdf_coordinates[~gdf_coordinates['geometry'].is_empty]

mymap = folium.Map(location=(37.53,127), zoom_start=10, control_scale=True)
marker_cluster = MarkerCluster(
    options={
        'showCoverageOnHover': False,
        'zoomToBoundsOnClick': True,}
        ).add_to(mymap)

def calculate_danger_coeff(df, sg):
    accident_weights = {
        "경상": 0.5, 
        "중상": 1,  
        "부상신고": 0.25, 
        "사망": 2.5 
    }

    accidents_in_location = df[df['시군구'] == sg]
    danger_coeff = 0
    for index, row in accidents_in_location.iterrows():
        accident_info = row['상해정도 정보'].split('<br>')
        for info in accident_info:
            accident_type, num_accidents_of_type = info.split(': ')
            num_accidents_of_type = int(num_accidents_of_type)
            if accident_type in accident_weights:
                danger_coeff += num_accidents_of_type * accident_weights[accident_type]
        # if danger_coeff >= 29:  # 위험도가 20 이상인 경우
            # print(f"시군구: {sg}, 위험도: {danger_coeff}")
    return danger_coeff

#위험도 기준치
def get_color(danger_coeff):
    if danger_coeff < 10:
        return 'green'
    # elif danger_coeff < 0.01:
    #     return 'yellow'
    elif danger_coeff < 00: 
        return 'orange'
    else:
        return 'red'

for index, row in gdf_coordinates.iterrows():
    if not row['geometry'].is_empty:
        # 위험도 계산
        danger_coeff = calculate_danger_coeff(first_all_merged, row['시군구'])

        # 위험도에 따른 색상 결정
        color = get_color(danger_coeff)

        # 위험도 소수점 
        danger_coeff = round(danger_coeff, 6)

        # 위험도 색상을 한글로 바꾸기
        # color_kr = {'green': '녹색', 'yellow': '노랑색', 'orange': '주황색', 'red': '빨강색'}[color]
        color_kr = {'green': '녹색', 'orange': '주황색', 'red': '빨강색'}[color]


        latitude = row['geometry'].y
        longitude = row['geometry'].x
        # icon = folium.Icon(color=color,icon='info-sign')
        icon = folium.Icon(color=color,icon='person-falling-burst', prefix='fa')
        popup_text = f"시군구: {row['시군구']}<br>{row['상해정도 정보']}<br>위험도: {danger_coeff}<br>위험도 색상: {color_kr}"
        folium.Marker(location=[latitude, longitude], icon=icon, popup=folium.Popup(popup_text, max_width=250)).add_to(marker_cluster)


first_all_merged['상해정도 갯수'] = grouped_df['상해정도 갯수']

first_all_merged['상해정도 갯수'] = first_all_merged['상해정도 갯수'].astype(int)

# 데이터 정리
grouped_df = first_all_merged.groupby('시군구')['상해정도 갯수'].sum().reset_index()
first_all_merged = pd.merge(first_all_merged, grouped_df, on='시군구', how='left')
    
first_all_merged['danger_coeff'] = first_all_merged['시군구'].apply(lambda sg: calculate_danger_coeff(first_all_merged, sg))

danger_coeff_data = first_all_merged.groupby('시군구')['danger_coeff'].sum().reset_index()
danger_coeff_data.columns = ['SIG_KOR_NM', 'danger_coeff']

# 마커 설정
for index, row in first_all_merged.iterrows():
    latitude = row['위도']
    longitude = row['경도']
    total_injury_count = row['상해정도 갯수_y']
    # radius = total_injury_count 
    radius = np.log(total_injury_count + 1)

    # 위험도 계산
    danger_coeff = row['danger_coeff']

    # 위험도 출력
    # print(f"Danger coefficient for index {index}: {danger_coeff}")

    # 위험도에 따른 색상 가져오기
    color = get_color(danger_coeff)

    folium.CircleMarker(
        location=[latitude, longitude],
        radius=radius,
        color=color,
        fill=True,
        fill_color=color,
        fill_opacity=0.5
    ).add_to(mymap)


# 도로 출력
gdf_road = gpd.read_file('C:\\sqlite\\mysql\\code\\AI\\Mid_project\\data\\sig.shp')
gdf_road = gdf_road.set_crs(epsg=5179)
gdf_road['region_code'] = gdf_road['SIG_CD'].str[:2]
gdf_road = gdf_road[gdf_road['region_code'].isin(['11', '41'])]

accident_data = first_all_merged.groupby('시군구')['상해정도 갯수_x'].sum().reset_index()
accident_data.columns = ['EMD_KOR_NM', 'total_accidents']
accident_data['EMD_KOR_NM'] = accident_data['EMD_KOR_NM'].apply(lambda x: ' '.join(x.split()[:2]))
accident_data = accident_data.groupby('EMD_KOR_NM')['total_accidents'].sum().reset_index()

geo_data = gdf_road.__geo_interface__

# 도로 설정
folium.GeoJson(
    gdf_road,
    style_function=lambda feature: {
        'fillColor': '#000000',  # 도로 색상을 검은색으로 설정
        'color': '#000000',  # 도로 테두리 색상을 검은색으로 설정
        'weight': 0.5,  # 도로 테두리 두께를 1로 설정
        'fillOpacity': 0,  # 도로 채우기 불투명도를 1.0으로 설정
    }
).add_to(mymap)

marker_cluster = MarkerCluster().add_to(mymap)

element = Element(custom_css)
mymap.get_root().html.add_child(element)

# 어린이 보호구역 출력
gdf_protect = gpd.read_file('C:\\sqlite\\mysql\\code\\AI\\gyeonggi_protect_polygons_test.geojson')

def polygon_to_circle(polygon):
    center = polygon.centroid
    distance = center.distance(unary_union(polygon.boundary))
    return center.buffer(distance)

gdf_protect['geometry'] = gdf_protect['geometry'].apply(polygon_to_circle)

# 어린이 보호구역 설정
folium.GeoJson(
    gdf_protect,
    style_function=lambda feature: {
        'fillColor': '#0000ff',
        # 'color': '#0000ff',
        'color': 'transparent',  # 테두리 색상을 투명하게 설정
        'weight': 0.5,  # 테두리 두께를 0으로 설정
        'fillOpacity': 0.2,
    }
).add_to(mymap)

macro = MacroElement()
macro._template = Template(template)

mymap.get_root().add_child(macro)

mymap.save('C:\\sqlite\\mysql\\code\\AI\\Mid_project\\data\\file\\cartoon_map_with_injury_counts_test_1_1안.html')
