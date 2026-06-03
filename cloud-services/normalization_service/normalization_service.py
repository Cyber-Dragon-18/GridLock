import io
import pandas as pd
import numpy as np
import openstack
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

RAW_SUFFIX = "raw"
CLEAN_SUFFIX = "clean"

def get_connection():
    return openstack.connect()

def _load_csv_from_swift(username, container_name, object_name):
    conn = get_connection()
    full_container = f"{username}-{container_name}"
    data = conn.object_store.download_object(object_name, container=full_container)
    return pd.read_csv(io.BytesIO(data))

def _normalize(df):
    changes = {}
    df_clean = df.copy()

    # 1. Standardize column names
    original_cols = list(df_clean.columns)
    df_clean.columns = [c.strip().lower().replace(" ", "_") for c in df_clean.columns]
    renamed = {o: n for o, n in zip(original_cols, df_clean.columns) if o != n}
    if renamed:
        changes["renamed_columns"] = renamed

    # 2. Handle null values
    null_counts = df_clean.isnull().sum()
    null_cols = null_counts[null_counts > 0].to_dict()
    if null_cols:
        for col in df_clean.columns:
            if df_clean[col].isnull().any():
                if df_clean[col].dtype in [np.float64, np.int64]:
                    median_val = df_clean[col].median()
                    df_clean[col] = df_clean[col].fillna(median_val)
                else:
                    mode_val = df_clean[col].mode()[0]
                    df_clean[col] = df_clean[col].fillna(mode_val)
        changes["nulls_filled"] = {col: int(count) for col, count in null_cols.items()}

    # 3. Encode categorical columns
    obj_cols = df_clean.select_dtypes(include="object").columns.tolist()
    encoded = {}
    for col in obj_cols:
        unique_vals = df_clean[col].unique().tolist()
        df_clean[col], _ = pd.factorize(df_clean[col])
        encoded[col] = {str(v): int(i) for i, v in enumerate(unique_vals)}
    if encoded:
        changes["encoded_columns"] = encoded

    # 4. Standardize target column
    target_candidates = ["class", "label", "target", "output"]
    found_target = None
    for col in df_clean.columns:
        if col.lower() in target_candidates:
            found_target = col
            break
    if found_target is None:
        found_target = df_clean.columns[-1]
    if found_target != "CLASS":
        df_clean = df_clean.rename(columns={found_target: "CLASS"})
        changes["target_column_renamed"] = {"from": found_target, "to": "CLASS"}

    return df_clean, changes


# --- Flask Endpoints ---

@app.route('/normalize/preview', methods=['POST'])
def preview_endpoint():
    data = request.get_json()
    username = data.get('username')
    object_name = data.get('object_name')
    container_name = data.get('container_name', RAW_SUFFIX)
    n_rows = data.get('n_rows', 5)

    try:
        df_raw = _load_csv_from_swift(username, container_name, object_name)
        df_clean, changes = _normalize(df_raw)

        return jsonify({
            "object_name": object_name,
            "source_container": f"{username}-{container_name}",
            "shape": {"rows": len(df_raw), "columns": len(df_raw.columns)},
            "changes": changes,
            "original_sample": df_raw.head(n_rows).to_dict(orient="records"),
            "cleaned_sample": df_clean.head(n_rows).to_dict(orient="records")
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/normalize/confirm', methods=['POST'])
def confirm_endpoint():
    data = request.get_json()
    username = data.get('username')
    object_name = data.get('object_name')
    container_name = data.get('container_name', RAW_SUFFIX)

    try:
        df_raw = _load_csv_from_swift(username, container_name, object_name)
        df_clean, changes = _normalize(df_raw)

        conn = get_connection()
        full_clean_container = f"{username}-{CLEAN_SUFFIX}"

        # Ensure clean container exists
        try:
            conn.object_store.create_container(full_clean_container)
        except Exception:
            pass

        csv_bytes = df_clean.to_csv(index=False).encode("utf-8")
        clean_name = object_name.replace(".csv", "_clean.csv")

        conn.object_store.upload_object(
            container=full_clean_container,
            name=clean_name,
            data=csv_bytes
        )

        return jsonify({
            "status": "saved",
            "clean_file": clean_name,
            "container": full_clean_container,
            "changes_applied": changes
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(port=5003, debug=True)
