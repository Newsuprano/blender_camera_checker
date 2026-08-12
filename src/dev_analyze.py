from logic import (
    load_and_pivot_data, 
    count_frame_statuses, 
    create_mismatched_dataframe
)

df = load_and_pivot_data()

identical, mismatched, bad_frames = count_frame_statuses(df)

print(f"Identical frames : {identical}")
print(f"Mismatched frames : {mismatched}")

mismatched_df = create_mismatched_dataframe(df, bad_frames)

print(f"Mismatched DataFrame shape : {mismatched_df.shape}")