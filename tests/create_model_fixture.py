"""Create an explicitly synthetic fitted artifact for cross-service tests only."""
import json
import os
from pathlib import Path
import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

root = Path(os.environ['MODEL_ARTIFACTS_ROOT'])
version = 'synthetic-software-fixture-v1'
out = root / version
out.mkdir(parents=True, exist_ok=True)
metrics = ['smart_5_raw', 'smart_187_raw', 'smart_188_raw', 'smart_197_raw', 'smart_198_raw', 'smart_199_raw', 'smart_241_raw', 'smart_242_raw', 'temperature']
columns = ['capacity_bytes', 'age_days'] + [f'{m}_{suffix}' for m in metrics for suffix in ['mean_7d','mean_30d','std_30d','delta_vs_7d','is_increasing']]
x = np.array([[1_000_000_000_000., float(i*10)] + [float(i)]*(len(columns)-2) for i in range(8)])
scaler = StandardScaler().fit(x)
model = LogisticRegression(random_state=42).fit(scaler.transform(x), [0,0,0,0,1,1,1,1])
joblib.dump({'model':model,'scaler':scaler,'model_type':'LogisticRegression','feature_columns':columns,'fill_values':{c:0. for c in columns},'horizon_days':30},out/'model.joblib')
for name,payload in {
 'feature_schema.json':{'ordered_features':[{'name':c} for c in columns]},
 'version.json':{'model_version':version,'horizon_days':30,'data_source':'SYNTHETIC SOFTWARE FIXTURE; NOT A FLEET MODEL'},
 'metrics.json':{'evaluation_scope':'synthetic integration fixture; no performance claim'},
}.items(): (out/name).write_text(json.dumps(payload))
print(f'Synthetic software fixture created: {out}')
