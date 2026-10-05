import platform
from datetime import datetime

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from btc_common.features import FEATURE_NAMES, MIN_HISTORY, training_set
from btc_common.series import drop_incomplete_day

TEST_FRACTION = 0.2
VALIDATION_FRACTION = 0.2
MIN_SAMPLES = 300


def candidates() -> dict:
    return {
        "ridge": make_pipeline(StandardScaler(), Ridge(alpha=10.0)),
        "hist_gradient_boosting": HistGradientBoostingRegressor(
            max_depth=3, learning_rate=0.05, max_iter=200, random_state=42
        ),
    }


def to_price(close: pd.Series, log_return) -> np.ndarray:
    return close.to_numpy() * np.exp(np.asarray(log_return))


def price_errors(close: pd.Series, y_true, y_pred) -> dict:
    error = to_price(close, y_pred) - to_price(close, y_true)
    return {
        "mae": float(np.mean(np.abs(error))),
        "rmse": float(np.sqrt(np.mean(error**2))),
    }


def directional_accuracy(y_true, y_pred) -> float:
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    return float(np.mean(np.sign(y_true) == np.sign(y_pred)))


def improvement(model_value: float, baseline_value: float) -> float:
    return float((baseline_value - model_value) / baseline_value * 100)


def span(index: pd.Index) -> dict:
    return {
        "start": index[0].strftime("%Y-%m-%d"),
        "end": index[-1].strftime("%Y-%m-%d"),
        "n": int(len(index)),
    }


def train_model(
    frame: pd.DataFrame, source: str, model_id: str, created_at: datetime
) -> tuple[dict, dict, dict]:
    complete = drop_incomplete_day(frame)
    dropped_incomplete = len(complete) < len(frame)
    X, y = training_set(complete)
    if len(X) < MIN_SAMPLES:
        raise ValueError(
            f"dados insuficientes: {len(X)} amostras utilizáveis, mínimo de {MIN_SAMPLES}"
        )

    close = complete["close"].loc[X.index]
    cut = int(len(X) * (1 - TEST_FRACTION))
    X_train, y_train, close_train = X.iloc[:cut], y.iloc[:cut], close.iloc[:cut]
    X_test, y_test, close_test = X.iloc[cut:], y.iloc[cut:], close.iloc[cut:]

    vcut = int(len(X_train) * (1 - VALIDATION_FRACTION))
    validation = {}
    for name, estimator in candidates().items():
        estimator.fit(X_train.iloc[:vcut], y_train.iloc[:vcut])
        pred = estimator.predict(X_train.iloc[vcut:])
        validation[name] = price_errors(close_train.iloc[vcut:], y_train.iloc[vcut:], pred)
    chosen = min(validation, key=lambda n: validation[n]["mae"])

    model = candidates()[chosen]
    model.fit(X_train, y_train)
    pred_test = model.predict(X_test)

    model_scores = price_errors(close_test, y_test, pred_test)
    baseline_scores = price_errors(close_test, y_test, np.zeros(len(y_test)))

    metrics = {
        "model_id": model_id,
        "model_type": chosen,
        "unit": "USD",
        "test": {
            **model_scores,
            "directional_accuracy": directional_accuracy(y_test, pred_test),
            "n": int(len(y_test)),
        },
        "baseline": baseline_scores,
        "improvement_over_baseline_pct": {
            "mae": improvement(model_scores["mae"], baseline_scores["mae"]),
            "rmse": improvement(model_scores["rmse"], baseline_scores["rmse"]),
        },
        "validation": validation,
    }

    manifest = {
        "model_id": model_id,
        "created_at": created_at.isoformat(),
        "model_type": chosen,
        "artifact": "model.joblib",
        "target": "log_return_next_day",
        "prediction": "close_t * exp(predicted_log_return)",
        "features": FEATURE_NAMES,
        "min_history": MIN_HISTORY,
        "data": {
            "source": source,
            "n_rows_received": int(len(frame)),
            "incomplete_day_dropped": dropped_incomplete,
            **span(complete.index),
        },
        "split": {
            "train": span(X_train.index),
            "test": span(X_test.index),
        },
        "libraries": {
            "python": platform.python_version(),
            "scikit_learn": sklearn.__version__,
            "pandas": pd.__version__,
            "numpy": np.__version__,
            "joblib": joblib.__version__,
        },
    }

    bundle = {
        "model": model,
        "model_type": chosen,
        "features": FEATURE_NAMES,
        "min_history": MIN_HISTORY,
    }
    return bundle, metrics, manifest
