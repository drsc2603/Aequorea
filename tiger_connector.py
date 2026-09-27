import os
from datetime import datetime, timezone

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

# ==============================================================================
# LOCAL IN-MEMORY TELEMETRY BUFFER (FAULT-TOLERANT FALLBACK)
# Initialized with realistic sample records tagged explicitly with sample status
# ==============================================================================
_LOCAL_TELEMETRY_BUFFER = [
    {
        "timestamp": "2026-09-26 17:38:29+00:00",
        "port_key": "PA_PHILLY",
        "station_id": "8545240",
        "water_level_mhhw_ft": 1.03,
        "nws_stage": "Normal Operations (USACE Channel Clear)",
        "terminal_disruption_pct": 0.0,
        "daily_direct_loss_usd": 0.0,
        "total_client_loss_usd": 0.0,
        "client_profile": "[SAMPLE CLIENT] Tier-1 Regional E-Commerce Hub"
    }
]


def get_db_connection():
    """
    Establishes connection to Tiger Data PostgreSQL / Timescale instance
    using a strict 2-second timeout to prevent application hanging.
    """
    if not PSYCOPG2_AVAILABLE:
        return None
    db_url = os.getenv("TIMESCALE_SERVICE_URL") or os.getenv("DATABASE_URL")
    if not db_url:
        return None
    try:
        return psycopg2.connect(db_url, connect_timeout=2)
    except Exception:
        return None


def init_telemetry_hypertable():
    """
    Ensures the target table exists and initializes Timescale hypertable
    partitioning if running on a live Tiger Data / Timescale database instance.
    """
    conn = get_db_connection()
    if not conn:
        return False
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS port_telemetry (
                    timestamp TIMESTAMPTZ NOT NULL,
                    port_key VARCHAR(32) NOT NULL,
                    station_id VARCHAR(16) NOT NULL,
                    water_level_mhhw_ft DOUBLE PRECISION NOT NULL,
                    nws_stage VARCHAR(64) NOT NULL,
                    terminal_disruption_pct DOUBLE PRECISION NOT NULL,
                    daily_direct_loss_usd DOUBLE PRECISION NOT NULL,
                    total_client_loss_usd DOUBLE PRECISION DEFAULT 0.0,
                    client_profile VARCHAR(128) DEFAULT '[SAMPLE CLIENT]'
                );
            """)
            # Convert to hypertable if Timescale extension is available
            try:
                cur.execute("SELECT create_hypertable('port_telemetry', 'timestamp', if_not_exists => TRUE);")
            except Exception:
                pass
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()


def log_telemetry_event(port_payload):
    """
    Persists real-time hydrodynamic and client impact telemetry.
    Supports both client-custom and sample benchmark profiles.
    """
    impact = port_payload.get("impact_assessment", {})
    client_name = impact.get("client_profile_applied", "[SAMPLE CLIENT] Benchmark E-Commerce Hub")
    
    record = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S+00:00"),
        "port_key": port_payload.get("port_key", "PA_PHILLY"),
        "station_id": port_payload.get("station_id", "8545240"),
        "water_level_mhhw_ft": float(port_payload.get("water_level_mhhw_ft", 1.03)),
        "nws_stage": impact.get("nws_flood_stage", "Normal Operations"),
        "terminal_disruption_pct": float(impact.get("terminal_capacity_loss_pct", 0.0)),
        "daily_direct_loss_usd": float(impact.get("estimated_daily_direct_loss_usd", 0.0)),
        "total_client_loss_usd": float(impact.get("total_client_financial_risk_usd", 0.0)),
        "client_profile": client_name
    }

    _LOCAL_TELEMETRY_BUFFER.insert(0, record)

    conn = get_db_connection()
    if conn:
        try:
            init_telemetry_hypertable()
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO port_telemetry (
                        timestamp, port_key, station_id, water_level_mhhw_ft,
                        nws_stage, terminal_disruption_pct, daily_direct_loss_usd,
                        total_client_loss_usd, client_profile
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    record["timestamp"], record["port_key"], record["station_id"],
                    record["water_level_mhhw_ft"], record["nws_stage"],
                    record["terminal_disruption_pct"], record["daily_direct_loss_usd"],
                    record["total_client_loss_usd"], record["client_profile"]
                ))
            conn.commit()
        except Exception:
            # Fall back to legacy schema insert if existing table lacks newer columns
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO port_telemetry (
                            timestamp, port_key, station_id, water_level_mhhw_ft,
                            nws_stage, terminal_disruption_pct, daily_direct_loss_usd
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (
                        record["timestamp"], record["port_key"], record["station_id"],
                        record["water_level_mhhw_ft"], record["nws_stage"],
                        record["terminal_disruption_pct"], record["daily_direct_loss_usd"]
                    ))
                conn.commit()
            except Exception:
                pass
        finally:
            conn.close()
    return True


def fetch_recent_telemetry(port_key="PA_PHILLY", limit=10):
    """
    Retrieves the most recent telemetry rows for the specified port node.
    Falls back seamlessly to local buffered records when database is unreachable.
    """
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT *
                    FROM port_telemetry
                    WHERE port_key = %s
                    ORDER BY timestamp DESC
                    LIMIT %s
                """, (port_key, limit))
                rows = cur.fetchall()
                if rows:
                    return [dict(r) for r in rows]
        except Exception:
            pass
        finally:
            conn.close()

    filtered = [r for r in _LOCAL_TELEMETRY_BUFFER if r["port_key"] == port_key]
    return filtered[:limit] if filtered else _LOCAL_TELEMETRY_BUFFER[:limit]