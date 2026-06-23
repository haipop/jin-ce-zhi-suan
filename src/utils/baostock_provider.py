# src/utils/baostock_provider.py
import baostock as bs
import pandas as pd
from datetime import datetime, timedelta
import os
from src.utils.config_loader import ConfigLoader


class BaostockProvider:
    """
    Baostock Data Provider (Open Source, Free)
    数据来源：证券宝 (baostock.com)，完全免费，无需 Token
    注意：不支持 1 分钟 K 线，最小周期为 5 分钟；不支持实时行情
    """

    # Baostock 不支持 1min，用 5min 作为最小周期回退
    _MINUTE_FALLBACK_FREQ = "5"

    def __init__(self):
        cfg = ConfigLoader.reload()
        self.last_error = ""
        self._cache_enabled = bool(cfg.get("data_provider.local_cache_enabled", True))
        cache_dir = str(cfg.get("data_provider.local_cache_dir", "data/history/cache") or "data/history/cache")
        base_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(base_dir))
        self._cache_dir = cache_dir if os.path.isabs(cache_dir) else os.path.join(project_root, cache_dir)
        os.makedirs(self._cache_dir, exist_ok=True)

    # ------------------------------------------------------------------ #
    #  代码转换
    # ------------------------------------------------------------------ #
    @staticmethod
    def _to_baostock_code(code: str) -> str:
        """600036.SH -> sh.600036, 000001.SZ -> sz.000001"""
        code = str(code).upper().strip()
        if code.startswith("SH.") or code.startswith("SZ."):
            raw = code.split(".")[1]
            prefix = code[:2].lower()
            return f"{prefix}.{raw}"
        if "." in code:
            parts = code.split(".")
            suffix = parts[1].upper()
            prefix = "sh" if suffix == "SH" else "sz"
            return f"{prefix}.{parts[0]}"
        # 纯 6 位数字，根据首位判断市场
        if code.startswith(("6", "9")):
            return f"sh.{code}"
        return f"sz.{code}"

    # ------------------------------------------------------------------ #
    #  缓存（与其他 Provider 保持一致的模式）
    # ------------------------------------------------------------------ #
    def _cache_file_path(self, code, interval="5min"):
        safe_code = str(code).upper().replace(".", "_")
        return os.path.join(self._cache_dir, f"baostock_{safe_code}_{interval}.csv")

    def _normalize_minutes_df(self, df):
        if df is None or df.empty:
            return pd.DataFrame()
        work = df.copy()
        required_cols = ["code", "open", "high", "low", "close", "vol", "amount", "dt"]
        for c in required_cols:
            if c not in work.columns:
                return pd.DataFrame()
        work["dt"] = pd.to_datetime(work["dt"])
        for c in ["open", "high", "low", "close", "vol", "amount"]:
            work[c] = pd.to_numeric(work[c], errors="coerce")
        work = work.dropna(subset=["dt", "open", "high", "low", "close"])
        work = work.drop_duplicates(subset=["dt"]).sort_values("dt").reset_index(drop=True)
        return work[["code", "dt", "open", "high", "low", "close", "vol", "amount"]]

    def _load_cached_minute_data(self, code, start_time, end_time):
        if not self._cache_enabled:
            return pd.DataFrame(), False
        path = self._cache_file_path(code, "5min")
        if not os.path.exists(path):
            return pd.DataFrame(), False
        try:
            df = pd.read_csv(path)
            if "dt" in df.columns:
                df["dt"] = pd.to_datetime(df["dt"])
            df = self._normalize_minutes_df(df)
            if df.empty:
                return pd.DataFrame(), False
            full_coverage = df["dt"].min() <= start_time and df["dt"].max() >= end_time
            df_range = df[(df["dt"] >= start_time) & (df["dt"] <= end_time)].copy()
            return df_range, bool(full_coverage and not df_range.empty)
        except Exception:
            return pd.DataFrame(), False

    def _save_minute_cache(self, code, df):
        if not self._cache_enabled or df is None or df.empty:
            return
        path = self._cache_file_path(code, "5min")
        try:
            df_save = self._normalize_minutes_df(df)
            if df_save.empty:
                return
            if os.path.exists(path):
                old_df = pd.read_csv(path)
                if "dt" in old_df.columns:
                    old_df["dt"] = pd.to_datetime(old_df["dt"])
                old_df = self._normalize_minutes_df(old_df)
                if not old_df.empty:
                    df_save = pd.concat([old_df, df_save], ignore_index=True)
                    df_save = self._normalize_minutes_df(df_save)
            df_save.to_csv(path, index=False, encoding="utf-8")
        except Exception:
            return

    # ------------------------------------------------------------------ #
    #  核心接口
    # ------------------------------------------------------------------ #
    def fetch_minute_data(self, code, start_time, end_time):
        """
        获取历史分钟级 K 线数据
        Baostock 最小周期为 5 分钟，1 分钟请求会自动回退到 5 分钟
        """
        cached_df, cache_hit = self._load_cached_minute_data(code, start_time, end_time)
        if cache_hit:
            return cached_df

        fetch_start = start_time
        if not cached_df.empty:
            fetch_start = cached_df["dt"].max() + timedelta(minutes=5)
            if fetch_start > end_time:
                return cached_df

        ba_code = self._to_baostock_code(code)
        start_str = fetch_start.strftime("%Y-%m-%d %H:%M:%S")
        end_str = end_time.strftime("%Y-%m-%d %H:%M:%S")

        try:
            lg = bs.login()
            if lg.error_code != "0":
                self.last_error = f"baostock_login_failed code={ba_code} err={lg.error_msg}"
                return cached_df if not cached_df.empty else pd.DataFrame()

            try:
                rs = bs.query_history_k_data_plus(
                    ba_code,
                    "date,time,code,open,high,low,close,volume,amount",
                    start_date=start_str,
                    end_date=end_str,
                    frequency=self._MINUTE_FALLBACK_FREQ,
                    adjustflag="2"  # 前复权
                )
            finally:
                bs.logout()

            if rs.error_code != "0":
                self.last_error = f"query_failed code={ba_code} err={rs.error_msg}"
                return cached_df if not cached_df.empty else pd.DataFrame()

            # 转 DataFrame
            rows = []
            while (rs.error_code == "0") and rs.next():
                rows.append(rs.get_row_data())
            if not rows:
                self.last_error = f"no_data code={ba_code} range={start_str}->{end_str}"
                return cached_df if not cached_df.empty else pd.DataFrame()

            df = pd.DataFrame(rows, columns=rs.fields)
            # 拼接 date + time -> dt
            df["dt"] = pd.to_datetime(df["date"] + " " + df["time"], errors="coerce")
            df = df.rename(columns={"volume": "vol"})
            df["code"] = code
            df = df.dropna(subset=["dt"])
            df = df[(df["dt"] >= start_time) & (df["dt"] <= end_time)]

            df = self._normalize_minutes_df(df[["code", "dt", "open", "high", "low", "close", "vol", "amount"]])
            if not cached_df.empty:
                df = pd.concat([cached_df, df], ignore_index=True)
                df = self._normalize_minutes_df(df)

            self._save_minute_cache(code, df)
            self.last_error = ""
            return df

        except Exception as e:
            self.last_error = f"fetch_minute_data_failed code={ba_code} range={start_str}->{end_str} err={e}"
            print(f"Error fetching Baostock history: {e}")
            return cached_df if not cached_df.empty else pd.DataFrame()

    def get_latest_bar(self, code):
        """
        获取最新行情
        Baostock 不提供实时行情，返回最近一个交易日的最后一根 5 分钟 K 线
        """
        today = datetime.now().strftime("%Y-%m-%d")
        # 请求今天及昨天的数据，以防非交易时段
        ba_code = self._to_baostock_code(code)
        start_str = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S")
        end_str = today + " 15:30:00"

        try:
            lg = bs.login()
            if lg.error_code != "0":
                self.last_error = f"baostock_login_failed code={ba_code} err={lg.error_msg}"
                return None

            try:
                rs = bs.query_history_k_data_plus(
                    ba_code,
                    "date,time,code,open,high,low,close,volume,amount",
                    start_date=start_str,
                    end_date=end_str,
                    frequency=self._MINUTE_FALLBACK_FREQ,
                    adjustflag="2"
                )
            finally:
                bs.logout()

            if rs.error_code != "0":
                self.last_error = f"query_failed code={ba_code} err={rs.error_msg}"
                return None

            rows = []
            while (rs.error_code == "0") and rs.next():
                rows.append(rs.get_row_data())
            if not rows:
                self.last_error = f"no_data code={ba_code}"
                return None

            df = pd.DataFrame(rows, columns=rs.fields)
            df["dt"] = pd.to_datetime(df["date"] + " " + df["time"], errors="coerce")
            df = df.rename(columns={"volume": "vol"})
            df = df.dropna(subset=["dt"]).sort_values("dt")

            row = df.iloc[-1]
            dt = row["dt"]
            return {
                "code": code,
                "dt": dt,
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "vol": float(row["vol"]),
                "amount": float(row["amount"])
            }

        except Exception as e:
            self.last_error = f"get_latest_bar_failed code={ba_code} err={e}"
            print(f"Error fetching Baostock latest bar: {e}")
            return None

    def check_connectivity(self, code="sh.600000"):
        """连通性检查"""
        try:
            lg = bs.login()
            if lg.error_code != "0":
                return False, lg.error_msg
            bs.logout()
            self.last_error = ""
            return True, "ok"
        except Exception as e:
            return False, str(e)
