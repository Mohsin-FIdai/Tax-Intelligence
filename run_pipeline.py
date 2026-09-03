import sys
import time
import io
import os
from pathlib import Path
import pandas as pd
import numpy as np


def _atomic_csv_write(df: pd.DataFrame, target_path: Path):
    """Write a DataFrame to CSV atomically: write to .tmp first, then os.replace().
    If the process is killed mid-write, the original file is never corrupted."""
    tmp_path = target_path.with_suffix(".csv.tmp")
    df.to_csv(tmp_path, index=False)
    os.replace(str(tmp_path), str(target_path))

# Force UTF-8 for Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from config.settings import RAW_UPLOADS_DIR, PROCESSED_DIR, MODELS_DIR
from core.pipeline.profiler import PipelineProfiler
from core.pipeline.pipeline_state import PipelineState
from core.pipeline.cache_manager import CacheManager

state = PipelineState()
cache = CacheManager()
profiler = PipelineProfiler()

def run_full_pipeline(source_dir: Path | str = RAW_UPLOADS_DIR, progress_callback=None):
    start = time.time()
    print("=" * 70)
    print("  GRAPH AI TAX INTELLIGENCE — HIGH PERFORMANCE PIPELINE")
    print("=" * 70)

    source_dir = Path(source_dir)
    data_files = list(source_dir.glob("*.csv")) + list(source_dir.glob("*.xlsx"))
    if not data_files:
        print("\n❌ No datasets available for analysis.")
        return

    # 1. ETL Pipeline
    profiler.start_stage('ETL')
    if progress_callback: progress_callback(15, "Running ETL data ingestion...")
    print("\n[1/6] Running ETL pipeline (with Caching)...")
    
    # Try Cache
    cached_etl = cache.get_stage_cache('ETL', data_files)
    if cached_etl is not None:
        print("  ✓ [CACHE HIT] Loaded cleaned datasets from cache.")
        for label, df in cached_etl.items():
            state.set_df(label, df)
    else:
        from core.data_ingestion.etl_pipeline import ETLPipeline
        pipeline = ETLPipeline(output_dir=PROCESSED_DIR)
        pipeline.add_sources_from_dir(source_dir, extensions=(".csv", ".xlsx"))
        results = pipeline.run()
        
        # Load processed into state
        cleaned_dfs = {}
        for csv_file in PROCESSED_DIR.glob("*_clean.csv"):
            label = csv_file.stem.replace("_clean", "")
            if not label.startswith("_"):
                df = pd.read_csv(csv_file, low_memory=False)
                state.set_df(label, df)
                cleaned_dfs[label] = df
        cache.set_stage_cache('ETL', data_files, cleaned_dfs)
    
    profiler.end_stage()

    # 2. Entity Resolution
    profiler.start_stage('ENTITY_RESOLUTION')
    if progress_callback: progress_callback(30, "Running entity resolution...")
    print("\n[2/6] Running entity resolution...")
    
    er_inputs = data_files # Cache depends on source files
    cached_er = cache.get_stage_cache('ENTITY_RESOLUTION', er_inputs)
    
    if cached_er is not None:
        print("  ✓ [CACHE HIT] Loaded resolved entities from cache.")
        citizens_df = cached_er['citizens_df']
    else:
        from core.entity_resolution.entity_resolver import EntityResolver
        resolver = EntityResolver()
        datasets = {k: state.get_df(k) for k in state._dataframes.keys()}
        citizens_df = resolver.resolve(datasets)
        cache.set_stage_cache('ENTITY_RESOLUTION', er_inputs, {'citizens_df': citizens_df})
    
    state.set_df('citizens_df', citizens_df)
    print(f"  ✓ Resolved → {len(citizens_df):,} unique citizens")
    profiler.end_stage(len(citizens_df))

    # 3. Feature Engineering
    profiler.start_stage('FEATURE_ENGINEERING')
    if progress_callback: progress_callback(50, "Extracting features...")
    print("\n[3/6] Running Feature Engineering...")
    
    cached_fe = cache.get_stage_cache('FEATURE_ENGINEERING', er_inputs)
    if cached_fe is not None:
        print("  ✓ [CACHE HIT] Loaded features from cache.")
        features_df = cached_fe['features_df']
    else:
        from core.ml.feature_engineering import FeatureEngineer
        # Map CNIC to citizen_id logic
        if "cnic" in citizens_df.columns:
            cnic_to_cid = dict(zip(citizens_df["cnic"].astype(str), citizens_df["citizen_id"]))
        else:
            cnic_to_cid = {}

        def _add_citizen_id(df: pd.DataFrame | None) -> pd.DataFrame | None:
            if df is None or df.empty: return df
            df = df.copy()
            if "citizen_id" in df.columns: return df
            
            from core.entity_resolution.entity_resolver import normalize_cnic
            
            if "cnic" in df.columns:
                df["citizen_id"] = df["cnic"].astype(str).apply(normalize_cnic).map(cnic_to_cid)
            else:
                for col in df.columns:
                    if "cnic" in col.lower():
                        df["citizen_id"] = df[col].astype(str).apply(normalize_cnic).map(cnic_to_cid)
                        break
            if "citizen_id" not in df.columns:
                df["citizen_id"] = "UNKNOWN"
            # Some mappings might fail and become NaN, replace with UNKNOWN
            df["citizen_id"] = df["citizen_id"].fillna("UNKNOWN")
            return df
            
        vehicles = _add_citizen_id(state.get_df('vehicle_records'))
        properties = _add_citizen_id(state.get_df('property_records'))
        utilities = _add_citizen_id(state.get_df('utility_bills'))
        travel = _add_citizen_id(state.get_df('travel_records'))
        business = _add_citizen_id(state.get_df('business_records'))
        banking = _add_citizen_id(state.get_df('banking_indicators'))

        if vehicles is not None and "market_value" in vehicles.columns and "vehicle_value" not in vehicles.columns:
            vehicles["vehicle_value"] = vehicles["market_value"]
        if properties is not None and "property_value" not in properties.columns:
            for col in properties.columns:
                if "value" in col.lower():
                    properties["property_value"] = properties[col]
                    break

        fe = FeatureEngineer()
        features_df = fe.extract_features(citizens_df, vehicles, properties, utilities, travel, business, banking)
        _atomic_csv_write(features_df, PROCESSED_DIR / "feature_vectors.csv")
        cache.set_stage_cache('FEATURE_ENGINEERING', er_inputs, {'features_df': features_df})

    state.set_df('features_df', features_df)
    print(f"  ✓ Feature vectors: {features_df.shape}")
    profiler.end_stage(len(features_df))
    
    # 4. ML Models
    profiler.start_stage('ML_MODELS')
    if progress_callback: progress_callback(60, "Running ML Models...")
    print("\n[4/6] Running ML Models...")
    
    numeric_cols = [c for c in features_df.columns if c != "citizen_id" and features_df[c].dtype in ["float64", "int64", "float32", "int32"]]
    X = features_df[numeric_cols].fillna(0)

    from core.ml.anomaly_detector import AnomalyDetector
    from core.ml.risk_classifier import RiskClassifier
    
    print(f"X variance:\n{X.var().head(10)}")
    print(f"X sample:\n{X.head(2)}")

    ad = AnomalyDetector()
    ad.fit(X)
    suspicion = ad.get_suspicion_percentage(X)
    citizens_df["suspicion_pct"] = suspicion[:len(citizens_df)]
    print(f"  ✓ Anomaly detection complete. Mean suspicion: {suspicion.mean():.1f}%")

    rc = RiskClassifier()
    labels = rc.generate_labels(features_df)
    if labels is not None and len(labels) > 0 and labels.nunique() >= 2:
        try:
            metrics = rc.train(X, labels)
            print(f"  ✓ Risk classifier trained. CV Accuracy: {metrics.get('cv_accuracy_mean', 0):.3f}")
            importance_df = rc.get_feature_importance()
            importance_df = importance_df.rename(columns={"avg_importance": "importance"})
            _atomic_csv_write(importance_df, PROCESSED_DIR / "feature_importance.csv")
        except Exception as e:
            pass
    profiler.end_stage(len(X))

    # 5. Risk Scoring
    profiler.start_stage('RISK_SCORING')
    if progress_callback: progress_callback(70, "Computing multi-dimensional risk scores...")
    print("\n[5/6] Computing risk scores...")
    
    from core.risk_scoring.net_worth_estimator import NetWorthEstimator
    from core.risk_scoring.deviation_scorer import DeviationScorer
    from core.risk_scoring.risk_categorizer import RiskCategorizer

    nwe = NetWorthEstimator()
    ds = DeviationScorer()
    rc2 = RiskCategorizer()

    # Merge features into citizens for vectorized scoring
    merged_scoring = citizens_df.copy()
    for col in features_df.columns:
        if col != "citizen_id" and col not in merged_scoring.columns:
            if len(features_df[col]) >= len(merged_scoring):
                merged_scoring[col] = features_df[col].values[:len(merged_scoring)]
    
    suspicion_list = suspicion.tolist() if hasattr(suspicion, 'tolist') else list(suspicion)
    merged_scoring["anomaly_suspicion"] = [float(suspicion_list[i]) if i < len(suspicion_list) else 0 for i in range(len(merged_scoring))]

    # Vectorized scoring using apply (much faster than dict conversion loop)
    score_dicts = merged_scoring.to_dict(orient="records")
    
    net_worths = []
    dev_scores = []
    risk_cats = []
    for citizen_data in score_dicts:
        nw_result = nwe.estimate(citizen_data)
        est_nw = nw_result.get("estimated_net_worth", 0)
        net_worths.append(est_nw)

        citizen_data["estimated_net_worth"] = est_nw
        dev_result = ds.score(citizen_data)
        dev_score = dev_result.get("deviation_score", 0)
        dev_scores.append(dev_score)

        cat_result = rc2.categorize(dev_score)
        risk_cats.append(cat_result.get("category", "C"))

    citizens_df["estimated_net_worth"] = net_worths
    citizens_df["deviation_score"] = dev_scores
    citizens_df["risk_category"] = risk_cats

    from core.risk_scoring.tax_gap_estimator import TaxGapEstimator
    tge = TaxGapEstimator()
    citizens_df = tge.process_dataframe(citizens_df)

    feature_cols_to_merge = [
        "total_vehicle_value", "total_property_value", "foreign_travel_count",
        "business_count", "business_class_trips", "avg_monthly_electricity",
        "avg_monthly_gas", "vehicle_count", "property_count",
        "total_utility_spend", "directorship_count", "avg_bank_balance",
    ]
    for col in feature_cols_to_merge:
        if col in features_df.columns:
            vals = features_df[col].values
            citizens_df[col] = vals[:len(citizens_df)] if len(vals) >= len(citizens_df) else np.pad(vals, (0, len(citizens_df) - len(vals)), constant_values=0)

    _atomic_csv_write(citizens_df, PROCESSED_DIR / "master_citizens.csv")
    profiler.end_stage(len(citizens_df))

    # 6. Knowledge Graph
    profiler.start_stage('KNOWLEDGE_GRAPH')
    if progress_callback: progress_callback(85, "Building knowledge graph...")
    print("\n[6/6] Building knowledge graph...")
    
    from core.knowledge_graph.graph_builder import KnowledgeGraphBuilder
    gb = KnowledgeGraphBuilder()
    G = gb.build_graph(
        citizens_df=citizens_df,
        vehicles_df=state.get_df('vehicle_records'),
        properties_df=state.get_df('property_records'),
        utilities_df=state.get_df('utility_bills'),
        travel_df=state.get_df('travel_records'),
        business_df=state.get_df('business_records'),
        mobile_df=state.get_df('mobile_records'),
        banking_df=state.get_df('banking_indicators'),
    )
    gb.save_graph()

    # Community Detection for Hidden Network Detection
    from networkx.algorithms.community import louvain_communities
    try:
        communities = louvain_communities(G.to_undirected(), resolution=1.0, seed=42)
    except Exception:
        from networkx.algorithms.community import greedy_modularity_communities
        communities = list(greedy_modularity_communities(G.to_undirected()))

    comm_records = []
    for i, comm in enumerate(communities):
        for node in comm:
            if str(node).startswith('CZ-') or G.nodes.get(node, {}).get('node_type') == 'Person':
                comm_records.append({'citizen_id': str(node), 'community_id': i})

    comm_df = pd.DataFrame(comm_records)
    _atomic_csv_write(comm_df, PROCESSED_DIR / "communities.csv")
    print(f"  ✓ Communities: {comm_df['community_id'].nunique():,} clusters detected and saved to communities.csv")
    profiler.end_stage(G.number_of_nodes())

    elapsed = time.time() - start
    high_risk = len(citizens_df[citizens_df["risk_category"].isin(["D", "E"])])

    print("\n" + "=" * 70)
    print(f"  ✅ PIPELINE COMPLETE in {elapsed:.1f} seconds")
    print(f"  📊 Citizens: {len(citizens_df):,}")
    print(f"  🕸️  Graph: {G.number_of_nodes():,} nodes, {G.number_of_edges():,} edges")
    print(f"  ⚠️  High-risk (Cat D+E): {high_risk:,}")
    print("=" * 70)
    
if __name__ == '__main__':
    run_full_pipeline()
