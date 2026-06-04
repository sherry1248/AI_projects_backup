# https://github.com/rjb1116/crash_net

import argparse
import pandas as pd
import folium
import osmnx as ox
import geopy.distance
import os
import matplotlib.pyplot as plt
import numpy as np
from folium.plugins import HeatMap
from branca.element import Figure, IFrame

def get_inputs():
    parser = argparse.ArgumentParser()
    parser.add_argument('--accidents_csv', default='C:\\sqlite\\mysql\\code\\AI\\Mid_project\\data\\file\\merged_dataframe.csv')
    parser.add_argument('-a', '--A_IDs', default=None)
    parser.add_argument('-d', '--distance', default=250)
    parser.add_argument('-g', '--grid_size', default=6)
    args = parser.parse_args()

    df_accidents = pd.read_csv(args.accidents_csv)
    A_IDs = [args.A_IDs] if args.A_IDs else df_accidents['시군구'].unique()
    distance = int(args.distance)
    grid_size = int(args.grid_size)

    return df_accidents, A_IDs, distance, grid_size, args

def make_mini_bboxes(bbox, grid_size):
    del_lat = (bbox['북쪽'] - bbox['남쪽']) / grid_size
    del_lng = (bbox['동쪽'] - bbox['서쪽']) / grid_size

    mini_bboxes = []

    for i in range(0, grid_size):
        for j in range(0, grid_size):
            mini_bbox = {}
            mini_bbox['북쪽'] = bbox['북쪽'] - del_lat * i
            mini_bbox['남쪽'] = mini_bbox['북쪽'] - del_lat
            mini_bbox['서쪽'] = bbox['서쪽'] + del_lng * j
            mini_bbox['동쪽'] = mini_bbox['서쪽'] + del_lng

            mini_bboxes.append(mini_bbox)

    return mini_bboxes

def get_accidents(bbox, df_accidents):
    df_bbox = df_accidents[(df_accidents['위도'] >= bbox['남쪽']) & (df_accidents['경도'] >= bbox['서쪽']) & (df_accidents['위도'] <= bbox['북쪽']) & (df_accidents['경도'] <= bbox['동쪽'])]
    return df_bbox

def get_danger_coeff(df_mini_bbox, num_zip_accidents):
    danger_coeff = len(df_mini_bbox) / num_zip_accidents
    return danger_coeff


# def get_inputs():
#     parser = argparse.ArgumentParser()
#     parser.add_argument('--accidents_csv', default='C:\\sqlite\\mysql\\code\\AI\\Mid_project\\data\\file\\merged_dataframe.csv')
#     parser.add_argument('-a', '--A_IDs', default=None)
#     parser.add_argument('-d', '--distance', default=250)
#     parser.add_argument('-g', '--grid_size', default=6)
#     args = parser.parse_args()

#     # 데이터 로드
#     df_accidents = pd.read_csv(args.accidents_csv)
#     A_IDs = [args.A_IDs] if args.A_IDs else df_accidents['시군구'].unique()
#     distance = int(args.distance)
#     grid_size = int(args.grid_size)

#     return df_accidents, A_IDs, distance, grid_size, args

def add_grid(fig, ax, grid_size, bbox, df_bbox, num_zip_accidents):
    mini_bboxes = make_mini_bboxes(bbox, grid_size)

    grid = []

    for mini_bbox in mini_bboxes:
        df_mini_bbox = get_accidents(mini_bbox, df_bbox)
        danger_coeff = get_danger_coeff(df_mini_bbox, num_zip_accidents)
        grid.append(danger_coeff)

        xs = [mini_bbox['서쪽'], mini_bbox['서쪽'], mini_bbox['동쪽'], mini_bbox['동쪽']]
        ys = [mini_bbox['북쪽'], mini_bbox['남쪽'], mini_bbox['남쪽'], mini_bbox['북쪽']]

        alpha = danger_coeff * 5
        if alpha > 0.5:
            alpha = 0.5

        ax.fill(xs, ys, "r", alpha=alpha)

    grid = np.array(grid).reshape((grid_size, grid_size))

    return grid, ax

def make_graph(lat, lng, distance):
    lat = df_accidents['위도'].median()
    lng = df_accidents['경도'].median()
    try:
        G = ox.graph_from_point((lat, lng), dist=distance, dist_type='bbox', network_type='drive', retain_all=True, simplify=False)
    except ox._errors.InsufficientResponseError:
        return None, None, None, None
    except ValueError as error:
        if "Found no graph nodes within the requested polygon" in str(error):
            print(f"Warning: No graph nodes found for coordinates ({lat}, {lng})")
            return None, None, None, None
        else:
            raise error
    fig, ax = ox.plot_graph(G, node_size=0, edge_color='black', show=False)
    nw = geopy.distance.great_circle(kilometers=distance).destination(point=(lat, lng), bearing=315).format_decimal()
    se = geopy.distance.great_circle(kilometers=distance).destination(point=(lat, lng), bearing=135).format_decimal()

    north, west = map(float, nw.split(","))
    south, east = map(float, se.split(","))

    bbox = {'남쪽': south, '북쪽': north, '서쪽': west, '동쪽': east}

    return fig, ax, G, bbox

def add_accidents(fig, ax, bbox, df_accidents):
    # Assuming df_accidents has columns '위도' and '경도'
    accidents = df_accidents[(df_accidents['위도'] >= bbox['남쪽']) & (df_accidents['위도'] <= bbox['북쪽']) &
                             (df_accidents['경도'] >= bbox['서쪽']) & (df_accidents['경도'] <= bbox['동쪽'])]

    for _, accident in accidents.iterrows():
        # Assuming you want to plot accidents as red dots
        ax.plot(accident['경도'], accident['위도'], 'ro', markersize=5)

    return fig, ax, accidents

def generate_single_accident(df_accidents, A_ID, distance, grid_size, failures_counter, failures_IDs, m):
    lat = df_accidents[df_accidents['시군구'] == A_ID]['위도'].values[0]
    lng = df_accidents[df_accidents['시군구'] == A_ID]['경도'].values[0]

    num_sigungu_accidents = df_accidents[df_accidents['시군구'] == A_ID]['상해정도 갯수_x'].values[0]

    fig, ax, G, bbox = make_graph(lat, lng, distance)

    if bbox is None:
        print(f"Failed to generate graph for A_ID {A_ID}")
        failures_counter += 1
        failures_IDs.append(A_ID)
        return None, failures_counter, failures_IDs

    fig, ax, df_bbox = add_accidents(fig, ax, bbox, df_accidents)

    grid, ax = add_grid(fig, ax, grid_size, bbox, df_bbox, num_sigungu_accidents)

    # calculate danger coefficient using the new function
    danger_coeff = calculate_danger_coeff(df_accidents, lat, lng)

    if danger_coeff > 0.7:
        color = 'red'
    elif danger_coeff > 0.5:
        color = 'orange'
    else:
        color = 'green'

    folium.CircleMarker(
        location=[lat, lng],
        radius=5,
        color=color,
        fill=True,
        fill_color=color
    ).add_to(m)

    plt.close()  # Close the figure to avoid the warning
    return grid, failures_counter, failures_IDs

def calculate_danger_coeff(df_accidents, lat, lng):
    # 사고의 심각성에 따른 가중치 설정
    accident_weights = {
        "경상": 1,
        "중상": 2,
        "부상신고": 0.5,
        "사망": 5
    }
    
    # 해당 지역에서 발생한 사고 데이터 추출
    accidents_in_location = df_accidents[(df_accidents['위도'] == lat) & (df_accidents['경도'] == lng)]
    
    # 위험도 계산
    danger_coeff = 0
    for accident_type, weight in accident_weights.items():
        num_accidents_of_type = accidents_in_location[accident_type].sum()
        danger_coeff += num_accidents_of_type * weight
    
    # 전체 사고 수로 나누어 정규화
    total_accidents = df_accidents.shape[0]
    danger_coeff /= total_accidents

    # 위험도 출력
    print("위험도:", danger_coeff)

    return danger_coeff

def main(df_accidents, A_IDs, distance, grid_size):
    failures_counter = 0
    failures_IDs = []

    danger_levels = pd.DataFrame(columns=['위도', '경도', '위험도'])

    # Create a map centered at the mean latitude and longitude values
    m = folium.Map(location=[df_accidents['위도'].mean(), df_accidents['경도'].mean()], zoom_start=7)

    for i, A_ID in enumerate(A_IDs):
        grid, failures_counter, failures_IDs = generate_single_accident(df_accidents, A_ID, distance, grid_size, failures_counter, failures_IDs, m)

        # print progress
        print(f"Processing {i+1}/{len(A_IDs)}: {A_ID}")

        if grid is not None:
            lat = df_accidents[df_accidents['시군구'] == A_ID]['위도'].values[0]
            lng = df_accidents[df_accidents['시군구'] == A_ID]['경도'].values[0]
            danger_level = grid.mean()
            new_data = pd.DataFrame([{'위도': lat, '경도': lng, '위험도': danger_level}])  # keep the values as numbers
            danger_levels = pd.concat([danger_levels, new_data], ignore_index=True)

    print(f"Number of failures: {failures_counter}")
    print(f"Failed IDs: {failures_IDs}")

    HeatMap(data=danger_levels, radius=15).add_to(m)
    m.save('C:\\sqlite\\mysql\\code\\AI\\Mid_project\\crash_net-main\\all_maps_test.html')




if __name__ == '__main__':
    df_accidents, A_IDs, distance, grid_size, args = get_inputs()
    main(df_accidents, A_IDs, distance, grid_size)



