import pandas as pd
from collections import defaultdict

def load_and_pivot_data(csv_path="output/camera_data.csv") :

    df = pd.read_csv(csv_path)

    df["attributes"] = df.apply(lambda row: (
        (row['pos_x'], row['pos_y'], row['pos_z']),  
        (row['rot_x'], row['rot_y'], row['rot_z']), 
        row['focal']                                
    ), axis=1)

    pivot_df = df.pivot(
        index = "filename",
        columns = "frame",
        values = "attributes"
    )
    return pivot_df


def get_frame_clusters_tuple(column_data) :
    groups = defaultdict(list)

    for camera_name, attr_tuple in column_data.dropna().items() :
        groups[attr_tuple].append(camera_name)

    sorted_groups = sorted(groups.items(), key=lambda item: len(item[1]), reverse=True)

    cluster_results = {}
    for group_id, (attr_tuple, cameras) in enumerate(sorted_groups) :
        for camera in cameras :
            cluster_results[camera] = {
                "group_id" : group_id,
                "attributes" : attr_tuple
            }
    return cluster_results


def count_frame_statuses(df) :
    identical_frames_counts = 0
    mismatched_frames_counts = 0
    mismatched_frames_list = []

    for frame in df.columns :
        frame_clusters = get_frame_clusters_tuple(df[frame])

        unique_groups = set(info["group_id"] for info in frame_clusters.values())

        if len(unique_groups) == 1 :
            identical_frames_counts += 1
        else :
            mismatched_frames_counts += 1
            mismatched_frames_list.append(frame)

    return identical_frames_counts, mismatched_frames_counts, mismatched_frames_list


def create_mismatched_dataframe(df, mismatched_frames_list) :
    mismatched_df = df[mismatched_frames_list].copy()
    return mismatched_df