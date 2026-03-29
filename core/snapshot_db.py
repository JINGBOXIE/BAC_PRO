# core/snapshot_db.py
from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Tuple, Any, List, Optional

import pymysql


def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


@dataclass
class DBConfig:
    host: str = "localhost"
    user: str = "root"
    password: str = ""
    database: str = "BAC_PRO"
    port: int = 3306
    charset: str = "utf8mb4"


class SnapshotDBWriter:
    """
    Batch UPSERT:
      - premax_snapshot_state: cnt/sum_hist_hb/sum_hist_hp accumulated
      - premax_snapshot_run: progress checkpoint
    """
    def __init__(self, cfg: DBConfig, *, autocommit: bool = False):
        self.cfg = cfg
        self.conn = pymysql.connect(
            host=cfg.host,
            user=cfg.user,
            password=cfg.password,
            database=cfg.database,
            port=cfg.port,
            charset=cfg.charset,
            autocommit=autocommit,
        )
        self.buffer: Dict[str, Tuple[str, int, str, str, int, int, int]] = {}
        # buffer[state_hash] = (cur_side, cur_len, hist_b_json, hist_p_json, cnt, sum_hb, sum_hp)

    def close(self):
        try:
            self.conn.close()
        except Exception:
            pass

    def add_state(self, state_key, cur_side, cur_len, hist_b_json, hist_p_json, hist_hb, hist_hp):
        # 生成唯一哈希（如果传入的 state_key 还没有哈希化）
        import hashlib
        state_hash = hashlib.sha256(state_key.encode()).hexdigest()
        
        # 严格按照 SQL 顺序构建元组：6个字段
        # 对应：state_hash, cur_side, cur_len, cnt (初始化为1), sum_hist_hb, sum_hist_hp
        if state_hash in self.buffer:
            # 如果缓冲区已存在，累加数值
            prev = self.buffer[state_hash]
            self.buffer[state_hash] = (
                state_hash,    # 0: state_hash
                cur_side,      # 1: cur_side
                cur_len,       # 2: cur_len
                prev[3] + 1,   # 3: cnt + 1
                prev[4] + hist_hb, # 4: sum_hist_hb
                prev[5] + hist_hp  # 5: sum_hist_hp
            )
        else:
            # 新增
            self.buffer[state_hash] = (
                state_hash, cur_side, cur_len, 1, hist_hb, hist_hp
            )

    def flush_states(self):
        if not self.buffer:
            return
        
        # 确保 SQL 占位符正好是 6 个
        sql = """
        INSERT INTO premax_snapshot_state (state_hash, cur_side, cur_len, cnt, sum_hist_hb, sum_hist_hp)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE 
            cnt = cnt + VALUES(cnt),
            sum_hist_hb = sum_hist_hb + VALUES(sum_hist_hb),
            sum_hist_hp = sum_hist_hp + VALUES(sum_hist_hp)
        """
        
        rows = list(self.buffer.values())
        
        try:
            with self.conn.cursor() as cur:
                # executemany 会自动处理 rows 列表中的每个元组
                cur.executemany(sql, rows)
            self.conn.commit()
            self.buffer.clear()
        except Exception as e:
            self.conn.rollback()
            print(f"[DB ERROR] Flush failed: {e}")
            # 如果是死锁，可以在这里加入上一轮讨论的重试逻辑

    def upsert_run_checkpoint(
        self,
        *,
        run_id: str,
        mode: str,
        master_seed: int,
        params: dict,
        shoes_target: int,
        shoes_done: int,
        snapshots_done: int,
        states_touched: int,
        finished: bool = False,
    ):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        params_json = json.dumps(params, separators=(",", ":"), sort_keys=True)

        sql = """
        INSERT INTO premax_snapshot_run
          (run_id, mode, master_seed, params_json, shoes_target, shoes_done, snapshots_done, states_touched, started_at, updated_at, finished_at)
        VALUES
          (%s, %s, %s, CAST(%s AS JSON), %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
          shoes_done = VALUES(shoes_done),
          snapshots_done = VALUES(snapshots_done),
          states_touched = VALUES(states_touched),
          updated_at = VALUES(updated_at),
          finished_at = VALUES(finished_at);
        """

        finished_at = now if finished else None
        with self.conn.cursor() as cur:
            cur.execute(
                sql,
                (
                    run_id, mode, master_seed, params_json,
                    shoes_target, shoes_done, snapshots_done, states_touched,
                    now, now, finished_at
                ),
            )
        self.conn.commit()

    def load_run_for_resume(self, run_id: str):
        """
        Load run info for auto-resume.
        Returns: (master_seed, shoes_done, shoes_target, params_dict)
        """
        sql = """
        SELECT master_seed, shoes_done, shoes_target, params_json
        FROM premax_snapshot_run
        WHERE run_id = %s
        """
        with self.conn.cursor() as cur:
            cur.execute(sql, (run_id,))
            row = cur.fetchone()
            if row is None:
                raise RuntimeError(f"run_id not found: {run_id}")

        master_seed, shoes_done, shoes_target, params_json = row
        return int(master_seed), int(shoes_done), int(shoes_target), json.loads(params_json)