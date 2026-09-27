import os
import json
from datetime import datetime, timezone
from engine import run_merton_simulation, SECTOR_PROFILES

# ==============================================================================
# GEMINI CLIENT INITIALIZATION (FAULT-TOLERANT WITH AUTO-FALLBACK)
# ==============================================================================
try:
    from google import genai
    from google.genai import types
    GENAI_SDK_AVAILABLE = True
except ImportError:
    GENAI_SDK_AVAILABLE = False


def _get_gemini_client(api_key_override=None):
    """
    Attempts to initialize Google GenAI Client using provided key or environment variable.
    """
    if not GENAI_SDK_AVAILABLE:
        return None
    api_key = api_key_override or os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    try:
        return genai.Client(api_key=api_key)
    except Exception:
        return None


# ==============================================================================
# SECTION I: C-SUITE EXECUTIVE DIRECTIVE GENERATOR
# Translates complex stochastic SDE outputs into plain-English, high-impact
# executive takeaways suitable for C-suite executives and board presentations.
# ==============================================================================

def generate_cfo_advisory(
    port_key="PA_PHILLY",
    sector_key="ECOMMERCE_HUB",
    daily_throughput_override=None,
    simulated_surge_override=None,
    buffer_ratio=0.50,
    parametric_hedge=True,
    capex_investment_usd=None,
    custom_client_overrides=None,
    api_key_override=None
):
    """
    Generates a formal, McKinsey-style C-Suite Advisory Directive.
    Uses Gemini 2.5/3.8 Flash when configured, or a deterministic actuarial
    template when running offline. All dense quant concepts are translated
    into plain-English executive impact metrics.
    """
    # 1. Run Quantitative Engine
    sim = run_merton_simulation(
        port_key=port_key,
        sector_key=sector_key,
        daily_throughput_override=daily_throughput_override,
        horizon_days=90,
        buffer_ratio=buffer_ratio,
        parametric_hedge=parametric_hedge,
        capex_investment_usd=capex_investment_usd,
        simulated_surge_override=simulated_surge_override,
        custom_client_overrides=custom_client_overrides
    )

    port = sim["port_metadata"]
    impact = port["impact_assessment"]
    sec = sim["sector_metadata"]
    qm = sim["cfo_quarterly_metrics"]
    lt = sim["long_term_5yr_metrics"]

    # 2. Extract Plain-English Operational Figures
    water_ft = port["water_level_mhhw_ft"]
    flood_stage = impact["nws_flood_stage"]
    client_name = sec["name"]
    is_sample = sec.get("is_sample_profile", False)

    daily_rev_m = sim["time_series_data"]["S0"] / 1e6
    worst_case_unmit_loss_m = qm["unmitigated_cfar_95_usd"] / 1e6
    worst_case_mit_loss_m = qm["mitigated_cfar_95_usd"] / 1e6
    cash_saved_m = qm["tail_risk_reduction_usd"] / 1e6
    pct_risk_suppressed = qm["tail_risk_reduction_pct"]
    co2_saved = qm["scope3_co2_tons_avoided"]

    capex_m = lt["capex_investment_usd"] / 1e6
    npv_5yr_m = lt["npv_5yr_usd"] / 1e6
    bcr = lt["benefit_cost_ratio"]
    payback_yrs = lt["payback_period_years"]
    irr_pct = lt["irr_pct"]

    # 3. Construct Plain-English Strategy Memo via Gemini if Available
    client = _get_gemini_client(api_key_override)
    if client:
        try:
            prompt = f"""
You are the Chief Risk Officer and Senior Strategy Partner advising the Board of Directors.
Translate this mathematical risk assessment into a crisp, authoritative, user-friendly Executive Directive.

CRITICAL TONE & USER-EXPERIENCE INSTRUCTIONS:
- Avoid dense academic jargon or unexplained math symbols.
- Translate every technical term into immediate business reality:
  * Instead of "95% CFaR", say "Worst-Case Quarterly Revenue at Risk (95th percentile downside)".
  * Instead of "Poisson jump shock", say "Sudden storm surge terminal shutdown".
  * Instead of "mean-reversion speed kappa", say "Backlog clearance speed (how quickly gates clear queued cargo)".
  * Instead of "Brownian motion", say "Baseline day-to-day demand and shipping cost fluctuations".
- Emphasize the bottom line: Dollar savings, payback period, and operational execution steps.

DATA CONTEXT:
- Client Profile: {client_name} (Sample Profile: {is_sample})
- Location: {port['port_name']} (Delaware River, Station {port['station_id']})
- Current Hydrologic Alert: {water_ft:.2f} ft MHHW ({flood_stage})
- Daily Cargo Exposure: ${daily_rev_m:.1f}M / day
- 90-Day Unmitigated Worst-Case Loss (Do Nothing): ${worst_case_unmit_loss_m:.1f}M
- 90-Day Protected Loss with Aequorea: ${worst_case_mit_loss_m:.1f}M
- Net Quarterly Cash Preserved: ${cash_saved_m:.1f}M ({pct_risk_suppressed}\% Downside Risk Eliminated) - 5-Year Private Staging & Railhead CapEx:${capex_m:.1f}M
- 5-Year Net Present Value (NPV): ${npv_5yr_m:.1f}M (Benefit-Cost Ratio: {bcr}x, Payback: {payback_yrs} years, IRR: {irr_pct}%)
- Avoided Scope 3 Carbon Emissions: {co2_saved:,.0f} Metric Tons CO2 (by preventing panic emergency air-charters)
- Pre-Surge Inventory Buffer: {buffer_ratio*100:.0f}%
- Parametric Liquidity Insurance: {"ACTIVE (24-hr automatic payout)" if parametric_hedge else "INACTIVE"}

FORMAT AS:
### 1. Executive Situation & Threat Summary (2-3 crisp sentences)
### 2. The Bottom Line: Cost of Inaction vs. Aequorea Strategy (bulleted comparison)
### 3. Immediate Operational Directives (48-Hour Action Plan)
### 4. Strategic Financial & Capital Allocation (5-Year ROI & Payback)
"""
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            return {
                "advisory_markdown": response.text,
                "engine_source": "Gemini 2.5 Flash Autonomous Agent",
                "sim_data": sim
            }
        except Exception:
            pass  # Fall through to deterministic template if API call fails

    # 4. Deterministic Plain-English Executive Directive Template
    memo = f"""### 📋 Strategic Risk Directive: {client_name}
**Terminal Location:** {port['port_name']} | **Gauge Reading:** `{water_ft:.2f} ft MHHW` (`{flood_stage}`)  
**Operational Status:** {"⚠️ CRITICAL FLOOD THREAT: Action Protocol Initiated" if water_ft >= 2.50 else "🟢 NORMAL OPERATIONS: Continuous Hazard Monitoring Active"}

---

#### 1. Executive Situation Summary
A severe coastal storm surge in the Delaware River Estuary threatens terminal access roads and crane operations at Packer Avenue. Without preventive measures, terminal gate closures will halt **${daily_rev_m:.1f}M in daily cargo flow**, triggering compounding downstream delivery penalties, customer cancellations, and expensive emergency freight substitutions.

#### 2. The Bottom Line: Cost of Inaction vs. Aequorea Protection
* **Cost of Doing Nothing (Status Quo):** In a severe 90-day storm scenario, your unmitigated worst-case downside loss reaches **${worst_case_unmit_loss_m:.1f}M** in disrupted orders, lost client contracts, and SLA penalties.
* **With Aequorea Protocol Applied:** Pre-buffering inventory and activating parametric insurance limits your worst-case quarterly loss to **${worst_case_mit_loss_m:.1f}M**.
* **Net Cash Flow Preserved:** **${cash_saved_m:.1f}M** in cash retained on your balance sheet (**{pct_risk_suppressed:.1f}% downside risk eliminated**).
* **Sustainability Dividend:** Avoids **{co2_saved:,.0f} metric tons of Scope 3 CO₂** emissions by preventing last-minute panic air-cargo diversions.

#### 3. Immediate Operational Directives (Next 48 Hours)
1. **Execute 48-Hour Pre-Surge Drayage Pull:** Mobilize contracted drayage carriers to pre-pull **{buffer_ratio*100:.0f}% of scheduled container volume** to inland staging hubs in the Lehigh Valley before the storm crests.
2. **Authorize Parametric Liquidity Draw:** {"Confirmed active. Automatic NOAA gauge verification triggers instant 24-hour insurance payout to finance inland trucking." if parametric_hedge else "Notice: Parametric liquidity hedge is currently inactive; emergency freight must be funded via internal cash reserves."}
3. **Notify Tier-1 Retail & Manufacturing Partners:** Issue proactive revised delivery notices leveraging buffered stock to avoid contractual late-delivery penalties.

#### 4. 5-Year Capital Allocation & ROI
* **Private Staging & Railhead Investment:** **${capex_m:.1f}M**
* **5-Year Net Present Value (NPV):** **+${npv_5yr_m:.1f}M** after fully accounting for capital costs
* **Benefit-to-Cost Ratio:** **{bcr:.2f}x** (for every $1.00 invested in resilience, you protect ${bcr:.2f} in value)
* **Capital Payback Period:** **{payback_yrs:.1f} Years** (Internal Rate of Return: **{irr_pct:.1f}%**)

> *Note: This analysis utilizes pre-calibrated sample parameters. Individual corporate figures can be customized via the sidebar controls.*
"""
    return {
        "advisory_markdown": memo,
        "engine_source": "Dynamic Actuarial Rules Engine",
        "sim_data": sim
    }


# ==============================================================================
# SECTION II: INTERACTIVE C-SUITE STRATEGY CHAT AGENT
# Handles natural language follow-up inquiries from executives and demo viewers.
# ==============================================================================

def query_cfo_agent_chat(user_query, sim_results, api_key_override=None):
    """
    Answers executive follow-up questions in plain English, citing specific
    model figures (cash saved, CapEx, payback, storm levels) from the simulation.
    """
    client = _get_gemini_client(api_key_override)
    qm = sim_results["cfo_quarterly_metrics"]
    lt = sim_results["long_term_5yr_metrics"]
    port = sim_results["port_metadata"]
    sec = sim_results["sector_metadata"]

    context_summary = f"""
CLIENT: {sec['name']}
STATION: {port['port_name']} ({port['water_level_mhhw_ft']:.2f} ft MHHW, {port['impact_assessment']['nws_flood_stage']})
90-DAY WORST-CASE LOSS (STATUS QUO): ${qm['unmitigated_cfar_95_usd']/1e6:.1f}M
90-DAY PROTECTED LOSS (AEQUOREA): ${qm['mitigated_cfar_95_usd']/1e6:.1f}M
CASH FLOW PRESERVED: ${qm['tail_risk_reduction_usd']/1e6:.1f}M ({qm['tail_risk_reduction_pct']}\%) 5-YEAR CAPEX BUDGET:${lt['capex_investment_usd']/1e6:.1f}M
5-YEAR NET PRESENT VALUE: ${lt['npv_5yr_usd']/1e6:.1f}M (BCR: {lt['benefit_cost_ratio']}x, Payback: {lt['payback_period_years']} years)
AVOIDED CO2: {qm['scope3_co2_tons_avoided']:,.0f} Metric Tons
"""

    if client:
        try:
            chat_prompt = f"""
You are the Strategic Risk Advisor answering an executive's question during a high-stakes board presentation.
Respond in 2 to 3 concise, highly readable, polished paragraphs.
Use plain English: explain any quantitative or logistics terms simply and clearly.
Directly cite the exact figures from the provided financial context.

FINANCIAL MODEL CONTEXT:
{context_summary}

EXECUTIVE QUERY:
"{user_query}"
"""
            resp = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=chat_prompt
            )
            return resp.text
        except Exception:
            pass

    # Deterministic conversational fallback
    query_lower = user_query.lower()
    if "capex" in query_lower or "budget" in query_lower or "cost" in query_lower:
        return (
            f"Our recommended resilience CapEx is **${lt['capex_investment_usd']/1e6:.1f}M**, dedicated to establishing "
            f"private off-dock railhead staging and elevated warehousing away from coastal flood zones. "
            f"This investment generates a **${lt['npv_5yr_usd']/1e6:.1f}M Net Present Value (NPV)** over 5 years, "
            f"achieving full capital payback in just **{lt['payback_period_years']:.1f} years** with a **{lt['benefit_cost_ratio']}x Benefit-Cost Ratio**."
        )
    elif "ignore" in query_lower or "nothing" in query_lower or "status quo" in query_lower:
        return (
            f"If management elects to take no action, your unmitigated worst-case downside risk over the next 90 days "
            f"stands at **${qm['unmitigated_cfar_95_usd']/1e6:.1f}M**. When severe river flooding halts port gates, stranded cargo "
            f"triggers heavy late-delivery penalties and forces emergency air-freight chartering. By implementing the Aequorea protocol, "
            f"you immediately preserve **${qm['tail_risk_reduction_usd']/1e6:.1f}M** in balance-sheet liquidity."
        )
    elif "carbon" in query_lower or "esg" in query_lower or "environment" in query_lower:
        return (
            f"By executing pre-surge inventory buffering, we prevent panic air-cargo substitutions when maritime berths freeze. "
            f"Air freight generates roughly 50 times more carbon emissions than container shipping. Over 90 days, this operational "
            f"time-shifting eliminates **{qm['scope3_co2_tons_avoided']:,.0f} Metric Tons of Scope 3 CO₂** emissions, delivering direct ESG and regulatory compliance benefits."
        )
    else:
        return (
            f"Based on current NOAA gauge telemetry of **{port['water_level_mhhw_ft']:.2f} ft MHHW** at {port['port_name']}, "
            f"the Aequorea platform recommends maintaining a **50% pre-surge inventory buffer** paired with active parametric insurance. "
            f"This operational strategy eliminates **{qm['tail_risk_reduction_pct']}% of severe downside risk**, preserving **${qm['tail_risk_reduction_usd']/1e6:.1f}M** "
            f"in cash flow while securing a **{lt['benefit_cost_ratio']}x return** on resilience capital investments."
        )


if __name__ == "__main__":
    print("=" * 70)
    print("AEQUOREA STRATEGY MONITOR | C-SUITE ADVISORY AUDIT")
    print("=" * 70)
    advisory = generate_cfo_advisory("PA_PHILLY", simulated_surge_override=3.97)
    print(f"Engine: {advisory['engine_source']}")
    print(advisory["advisory_markdown"][:600] + "...\n[Truncated for console]")
    print("-" * 70)
    test_reply = query_cfo_agent_chat("What happens if we ignore this plan?", advisory["sim_data"])
    print(f"Chat Response Test:\n{test_reply}")
    print("=" * 70)