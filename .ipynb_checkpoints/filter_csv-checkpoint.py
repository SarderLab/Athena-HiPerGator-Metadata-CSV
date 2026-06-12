import pandas as pd

df = pd.read_csv("/home/iansari/kpmp3/Batch_6/output_batch6.csv", keep_default_na=False)

qc_cols = [
    "gloms_qc",
    "muscular_vessels_qc",
    "tubules_qc",
    "ptc_qc",
    "ifta_qc"
]

# Keep rows where at least one QC field is not N/A
df = df[~df[qc_cols].eq("N/A").all(axis=1)]

df.to_csv("/home/iansari/kpmp3/Batch_6/output_batch6_filtered.csv", index=False)