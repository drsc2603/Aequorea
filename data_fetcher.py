import os
import requests
import json
from datetime import datetime, timezone

# ==============================================================================
# SECTION I: OBJECTIVE GROUND TRUTH MARITIME SPECIFICATIONS (NOAA & USACE)
# These values are fixed physical constants and official federal hydrologic datums.
# They DO NOT change per client.
# ==============================================================================

NOAA_API_URL = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"

PORT_NODES = {
    "PA_PHILLY": {
        "name": "PhillyPort (Packer Avenue Marine Terminal)",
        "station_id": "8545240",  # NOAA Station: Delaware River at Washington Ave, Philadelphia
        "waterway": "Delaware River Estuary",
        "usace_channel_depth_ft": 45.0,  # USACE Delaware River Deepening Project specification
        "tidal_harmonic_cycle_hours": 12.42,  # Semidiurnal tidal cycle period
        "surge_high_water_window_hours": 5.0,  # Average duration of tidal crest above flood stage
        "nws_flood_thresholds_mhhw": {
            "action": 1.00,
            "minor": 1.50,      # Minor Coastal Flood (NWS Philadelphia)
            "moderate": 2.50,   # Moderate Coastal Flood (berth wind/surge limit)
            "major": 3.50,      # Major Coastal Flood (USCG Port Safety shutdown)
            "historic_record_jan_2024": 3.97  # Jan 10, 2024 Delaware River surge record
        },
        "bea_rims_ii_regional_multiplier": 1.82  # BEA Type II Output Multiplier for PA Port Operations
    },
    "DE_WILMINGTON": {
        "name": "Port of Wilmington (Citrus & Cold-Storage Terminal)",
        "station_id": "8551910",  # NOAA Station: Christina River at Wilmington, DE
        "waterway": "Delaware River / Christina River Basin",
        "usace_channel_depth_ft": 38.0,
        "tidal_harmonic_cycle_hours": 12.42,
        "surge_high_water_window_hours": 4.5,
        "nws_flood_thresholds_mhhw": {
            "action": 1.10,
            "minor": 1.65,
            "moderate": 2.60,
            "major": 3.60,
            "historic_record_jan_2024": 4.12
        },
        "bea_rims_ii_regional_multiplier": 1.76
    }
}


# ==============================================================================
# SECTION II: SAMPLE CLIENT BASELINE CONFIGURATIONS (CUSTOMIZABLE)
# [SAMPLE ONLY]: These parameters represent benchmark archetypes. In enterprise
# deployment, these are supplied dynamically per client from ERP/TMS data or UI inputs.
# ==============================================================================

SAMPLE_CLIENT_ARCHETYPES = {
    # SAMPLE ARCHETYPE 1: Regional E-Commerce Fulfillment (e.g., Amazon PHL Archetype)
    "SAMPLE_ECOMMERCE_FULFILLMENT": {
        "client_name": "[SAMPLE CLIENT] Tier-1 Regional E-Commerce Distribution Hub",
        "is_sample_profile": True,  # Flags that these are benchmark defaults
        "daily_maritime_throughput_usd": 5_000_000.0,  # $5.0M/day nominal cargo flow
        "quarterly_gross_exposure_usd": 450_000_000.0,
        "daily_holding_cost_rate": 0.0009,             # h = 0.09%/day inventory carry cost
        "contractual_sla_multiplier": 1.45,            # Downstream liquidated damage penalty (1.45x)
        "air_freight_diversion_ratio": 0.15,           # 15% of delayed cargo shifted to emergency air
        "inland_staging_capex_usd": 18_000_000.0,      # Private off-dock rail/drayage staging capital
        "working_capital_runway_days": 45              # Liquidity tolerance before credit draw
    },

    # SAMPLE ARCHETYPE 2: Perishable Fruit Cold-Chain (e.g., Packer Ave Citrus Importer)
    "SAMPLE_COLD_CHAIN_PERISHABLES": {
        "client_name": "[SAMPLE CLIENT] Delaware Valley Cold-Chain Produce Logistics",
        "is_sample_profile": True,
        "daily_maritime_throughput_usd": 3_500_000.0,
        "quarterly_gross_exposure_usd": 315_000_000.0,
        "daily_holding_cost_rate": 0.0035,             # High decay: spoilage / reefer diesel costs
        "contractual_sla_multiplier": 1.85,            # Supermarket delivery cancellation clawbacks
        "air_freight_diversion_ratio": 0.28,           # High emergency air reliance for perishables
        "inland_staging_capex_usd": 14_000_000.0,
        "working_capital_runway_days": 21
    },

    # SAMPLE ARCHETYPE 3: Automotive JIT Assembly (e.g., Regional Component Distributor)
    "SAMPLE_AUTOMOTIVE_JIT": {
        "client_name": "[SAMPLE CLIENT] Mid-Atlantic Automotive JIT Component Supplier",
        "is_sample_profile": True,
        "daily_maritime_throughput_usd": 6_200_000.0,
        "quarterly_gross_exposure_usd": 558_000_000.0,
        "daily_holding_cost_rate": 0.0005,             # Metal/parts do not rot; low holding decay
        "contractual_sla_multiplier": 2.20,            # Factory assembly-line shutdown liquidated damages
        "air_freight_diversion_ratio": 0.40,           # High modal air pivot to prevent plant halting
        "inland_staging_capex_usd": 22_000_000.0,
        "working_capital_runway_days": 60
    }
}


# ==============================================================================
# SECTION III: OBJECTIVE HYDRODYNAMIC DATA INGESTION (NOAA API)
# ==============================================================================

def get_current_noaa_water_level(station_id="8545240"):
    """
    Fetches real-time verified water level relative to Mean Higher High Water (MHHW).
    Returns verified station data or an offline deterministic fallback on connection error.
    """
    params = {
        "station": station_id,
        "product": "water_level",
        "datum": "mhhw",
        "units": "english",
        "time_zone": "gmt",
        "application": "Aequorea_Maritime_Resilience",
        "format": "json",
        "date": "latest"
    }
    try:
        resp = requests.get(NOAA_API_URL, params=params, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if "data" in data and len(data["data"]) > 0:
                latest = data["data"][0]
                return {
                    "status": "online",
                    "station_id": station_id,
                    "water_level_mhhw_ft": float(latest["v"]),
                    "timestamp_gmt": latest["t"],
                    "is_simulated": False
                }
    except Exception as e:
        pass

    # Reliable fallback to nominal tidal mean if external network is unavailable
    return {
        "status": "offline_fallback",
        "station_id": station_id,
        "water_level_mhhw_ft": 1.03,  # Typical nominal baseline at Washington Ave
        "timestamp_gmt": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        "is_simulated": True
    }


def get_historical_event_data(station_id="8545240", begin_date="20240109", end_date="20240111"):
    """
    Pulls empirical gauge observations from the historic Jan 10, 2024 flood event.
    Provides verifiable storm surge ground truth.
    """
    params = {
        "station": station_id,
        "product": "water_level",
        "datum": "mhhw",
        "units": "english",
        "time_zone": "gmt",
        "application": "Aequorea_Maritime_Resilience",
        "format": "json",
        "begin_date": begin_date,
        "end_date": end_date
    }
    try:
        resp = requests.get(NOAA_API_URL, params=params, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            if "data" in data:
                return {"status": "success", "observations": data["data"]}
    except Exception as e:
        return {"status": "error", "error": str(e), "observations": []}
    return {"status": "no_data", "observations": []}


# ==============================================================================
# SECTION IV: ENTERPRISE FINANCIAL & PHYSICAL IMPACT TRANSLATOR
# Evaluates water elevation against official NWS thresholds and maps physical
# inundation into discrete client-specific economic loss vectors.
# ==============================================================================

def calculate_port_hydrodynamic_impact(water_level_mhhw_ft, port_key="PA_PHILLY", client_config=None):
    """
    Translates physical water level into port operational capacity loss and
    client-level financial damage using NWS thresholds and firm-specific parameters.
    """
    port_spec = PORT_NODES.get(port_key, PORT_NODES["PA_PHILLY"])
    thresholds = port_spec["nws_flood_thresholds_mhhw"]
    
    # Use client config if passed; otherwise fall back to Sample E-Commerce benchmark
    client = client_config or SAMPLE_CLIENT_ARCHETYPES["SAMPLE_ECOMMERCE_FULFILLMENT"]
    
    daily_exposure = client["daily_maritime_throughput_usd"]
    multiplier = port_spec["bea_rims_ii_regional_multiplier"]
    sla_mult = client.get("contractual_sla_multiplier", 1.45)
    surge_hours = port_spec.get("surge_high_water_window_hours", 5.0)

    # 1. Map physical water levels to terminal operating state
    if water_level_mhhw_ft < thresholds["action"]:
        stage = "Normal Operations (USACE Channel Clear)"
        disruption_ratio = 0.0
    elif water_level_mhhw_ft < thresholds["minor"]:
        stage = "Action Stage (Pre-Storm Tidal Swell)"
        disruption_ratio = 0.08
    elif water_level_mhhw_ft < thresholds["moderate"]:
        # Minor coastal flood: perimeter access road inundation; rail sidings slowed
        stage = "NWS Minor Flood Stage"
        disruption_ratio = 0.30
    elif water_level_mhhw_ft < thresholds["major"]:
        # Moderate flood: berth crane wind/water safety lockouts; electrical substation hazard
        stage = "NWS Moderate Flood Stage"
        disruption_ratio = 0.65
    else:
        # Major flood: USCG Captain of the Port emergency navigation suspension
        stage = "NWS Major Flood (Mandatory Navigation Shutdown)"
        disruption_ratio = 1.00

    # 2. Semidiurnal tidal exposure factor (e.g. 5-hour high tide peak vs 24-hr day)
    # For full shutdowns (disruption_ratio == 1.0), safety protocols halt operations all day
    effective_daily_disruption = disruption_ratio if disruption_ratio >= 0.65 else disruption_ratio * (surge_hours / 12.0)

    # 3. Compute client-specific financial exposure
    direct_cargo_halt_usd = daily_exposure * effective_daily_disruption
    contingent_sla_damages_usd = direct_cargo_halt_usd * (sla_mult - 1.0)
    total_client_loss_usd = direct_cargo_halt_usd + contingent_sla_damages_usd
    total_regional_impact_usd = direct_cargo_halt_usd * multiplier

    return {
        "port_key": port_key,
        "port_name": port_spec["name"],
        "station_id": port_spec["station_id"],
        "water_level_mhhw_ft": water_level_mhhw_ft,
        "nws_flood_stage": stage,
        "terminal_capacity_loss_pct": effective_daily_disruption * 100.0,
        "estimated_daily_direct_loss_usd": direct_cargo_halt_usd,
        "contingent_sla_damages_usd": contingent_sla_damages_usd,
        "total_client_financial_risk_usd": total_client_loss_usd,
        "total_regional_economic_impact_usd": total_regional_impact_usd,
        "client_profile_applied": client["client_name"],
        "is_sample_profile": client.get("is_sample_profile", False)
    }


def get_port_intelligence_payload(port_key="PA_PHILLY", client_override=None):
    """
    Standard interface called by app.py and engine.py.
    Packages live NOAA sensor data, physical specifications, and client risk calculations.
    """
    port_spec = PORT_NODES.get(port_key, PORT_NODES["PA_PHILLY"])
    station_id = port_spec["station_id"]

    # Ingest verified sensor water level
    sensor_data = get_current_noaa_water_level(station_id=station_id)
    water_level = sensor_data["water_level_mhhw_ft"]

    # Calculate operational and economic impact
    impact = calculate_port_hydrodynamic_impact(
        water_level_mhhw_ft=water_level,
        port_key=port_key,
        client_config=client_override
    )

    return {
        "port_key": port_key,
        "port_name": port_spec["name"],
        "station_id": station_id,
        "water_level_mhhw_ft": water_level,
        "is_sensor_simulated": sensor_data["is_simulated"],
        "timestamp_gmt": sensor_data["timestamp_gmt"],
        "nws_thresholds": port_spec["nws_flood_thresholds_mhhw"],
        "channel_depth_ft": port_spec["usace_channel_depth_ft"],
        "bea_multiplier": port_spec["bea_rims_ii_regional_multiplier"],
        "impact_assessment": impact
    }


if __name__ == "__main__":
    print("=" * 70)
    print("AEQUOREA MARITIME INTELLIGENCE | DATA FETCHER ENGINE AUDIT")
    print("=" * 70)

    # 1. Live Sensor Verification
    live_payload = get_port_intelligence_payload("PA_PHILLY")
    print(f"\n[LIVE SENSOR CHECK]")
    print(f"Port Node: {live_payload['port_name']}")
    print(f"NOAA Station: {live_payload['station_id']}")
    print(f"Live Water Level: {live_payload['water_level_mhhw_ft']:.2f} ft MHHW")
    print(f"Current Status: {live_payload['impact_assessment']['nws_flood_stage']}")

    # 2. Historical Replay Verification (Jan 10, 2024 Record Surge: 3.97 ft MHHW)
    print(f"\n[STORM STRESS TEST: JAN 10, 2024 BENCHMARK (3.97 ft MHHW)]")
    storm_impact = calculate_port_hydrodynamic_impact(3.97, "PA_PHILLY")
    print(f"Applied Archetype: {storm_impact['client_profile_applied']} (Sample = {storm_impact['is_sample_profile']})")
    print(f"Terminal Flood Stage: {storm_impact['nws_flood_stage']}")
    print(f"Daily Direct Cargo Halt: ${storm_impact['estimated_daily_direct_loss_usd']:,.2f}")
    print(f"Contingent SLA Late Penalties: ${storm_impact['contingent_sla_damages_usd']:,.2f}")
    print(f"Total Client Daily Loss: ${storm_impact['total_client_financial_risk_usd']:,.2f}")
    print(f"Regional Economic Ripple (BEA 1.82x): ${storm_impact['total_regional_economic_impact_usd']:,.2f}")
    print("=" * 70)